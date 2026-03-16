import argparse
import json
import re
import unicodedata
from collections import Counter, deque
from itertools import zip_longest
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Set, Tuple


TOKEN_RE = re.compile(r"\w+", re.UNICODE)
NUMBER_RE = re.compile(r"\d+(?:[.,:/-]\d+)*")
URL_RE = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.IGNORECASE)
PUNCT_CHARS = ".,;:!?()[]{}\"'%-"


def _strip_accents(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def _fold_text(text: str) -> str:
    return _strip_accents(text).lower()


def _tokenize(text: str) -> List[str]:
    return TOKEN_RE.findall(_fold_text(text))


def _long_tokens(text: str) -> Set[str]:
    return {token for token in _tokenize(text) if len(token) >= 4}


def _char_ngrams(text: str, n: int = 3) -> Set[str]:
    compact = re.sub(r"\s+", " ", _fold_text(text)).strip()
    if len(compact) < n:
        return {compact} if compact else set()
    return {compact[idx:idx + n] for idx in range(len(compact) - n + 1)}


def _jaccard(left: Iterable[str], right: Iterable[str]) -> float:
    left_set = set(left)
    right_set = set(right)
    if not left_set and not right_set:
        return 1.0
    if not left_set or not right_set:
        return 0.0
    return len(left_set & right_set) / len(left_set | right_set)


def _length_ratio(source_text: str, target_text: str) -> float:
    source_len = max(len(_tokenize(source_text)), 1)
    target_len = max(len(_tokenize(target_text)), 1)
    return min(source_len, target_len) / max(source_len, target_len)


def _extract_punctuation_profile(text: str) -> Counter:
    return Counter(ch for ch in text if ch in PUNCT_CHARS)


def _counter_similarity(left: Counter, right: Counter) -> float:
    keys = set(left) | set(right)
    if not keys:
        return 1.0
    shared = sum(min(left[key], right[key]) for key in keys)
    total = sum(max(left[key], right[key]) for key in keys)
    return shared / total if total else 1.0


def _extract_entities(text: str) -> Set[str]:
    entities = set()
    for idx, token in enumerate(re.findall(r"\b[^\s]+\b", text)):
        stripped = token.strip(".,;:!?()[]{}\"'")
        if len(stripped) < 3:
            continue
        if any(ch.isdigit() for ch in stripped):
            entities.add(_fold_text(stripped))
            continue
        if idx == 0 and stripped[:1].isupper() and stripped[1:].islower():
            continue
        if stripped[:1].isupper() and not stripped.isupper():
            entities.add(_fold_text(stripped))
    return entities


def _optional_anchor_score(source_items: Set[str], target_items: Set[str]) -> Optional[float]:
    if not source_items and not target_items:
        return None
    return _jaccard(source_items, target_items)


def _preview(text: str, limit: int = 120) -> str:
    compact = re.sub(r"\s+", " ", text).strip()
    return compact[:limit] + ("..." if len(compact) > limit else "")


def _compute_pair_features(source_text: str, target_text: str) -> Dict[str, float]:
    return {
        "length_ratio": _length_ratio(source_text, target_text),
        "punctuation_similarity": _counter_similarity(
            _extract_punctuation_profile(source_text),
            _extract_punctuation_profile(target_text),
        ),
        "token_overlap": _jaccard(_long_tokens(source_text), _long_tokens(target_text)),
        "char_ngram_similarity": _jaccard(_char_ngrams(source_text), _char_ngrams(target_text)),
    }


def _score_pair(source_text: str, target_text: str) -> Tuple[float, Dict[str, float]]:
    features = _compute_pair_features(source_text, target_text)
    weighted_total = 0.0
    total_weight = 0.0

    base_weights = {
        "length_ratio": 0.45,
        "punctuation_similarity": 0.20,
        "token_overlap": 0.20,
        "char_ngram_similarity": 0.15,
    }
    for key, weight in base_weights.items():
        weighted_total += features[key] * weight
        total_weight += weight

    optional_features = {
        "number_anchor": _optional_anchor_score(set(NUMBER_RE.findall(source_text)), set(NUMBER_RE.findall(target_text))),
        "url_anchor": _optional_anchor_score(set(URL_RE.findall(source_text)), set(URL_RE.findall(target_text))),
        "email_anchor": _optional_anchor_score(set(EMAIL_RE.findall(source_text)), set(EMAIL_RE.findall(target_text))),
        "entity_anchor": _optional_anchor_score(_extract_entities(source_text), _extract_entities(target_text)),
    }
    optional_weights = {
        "number_anchor": 0.25,
        "url_anchor": 0.20,
        "email_anchor": 0.15,
        "entity_anchor": 0.20,
    }
    for key, value in optional_features.items():
        if value is None:
            continue
        features[key] = value
        weighted_total += value * optional_weights[key]
        total_weight += optional_weights[key]

    score = weighted_total / total_weight if total_weight else 0.0
    features["alignment_score"] = score
    return score, features


def _detect_reasons(source_text: str, target_text: str, features: Dict[str, float], args: argparse.Namespace) -> List[str]:
    reasons: List[str] = []
    source_has_text = bool(source_text.strip())
    target_has_text = bool(target_text.strip())
    if source_has_text != target_has_text:
        reasons.append("blank_side_mismatch")
    if features.get("length_ratio", 1.0) < args.min_length_ratio:
        reasons.append("large_length_mismatch")
    if features.get("number_anchor") is not None and features["number_anchor"] == 0.0:
        reasons.append("number_mismatch")
    if features.get("url_anchor") is not None and features["url_anchor"] == 0.0:
        reasons.append("url_mismatch")
    if features.get("email_anchor") is not None and features["email_anchor"] == 0.0:
        reasons.append("email_mismatch")
    if (
        features.get("entity_anchor") is not None
        and features["entity_anchor"] < args.min_entity_anchor_similarity
        and features.get("alignment_score", 1.0) < args.score_threshold
    ):
        reasons.append("named_entity_mismatch")
    if features.get("punctuation_similarity", 1.0) < args.min_punctuation_similarity:
        reasons.append("punctuation_mismatch")
    if features.get("alignment_score", 1.0) < args.score_threshold:
        reasons.append("low_alignment_score")
    return reasons


def _load_record(raw_line: str, mode: str, field: Optional[str]) -> Tuple[str, Optional[Dict[str, Any]]]:
    if mode == "jsonl":
        parsed = json.loads(raw_line)
        text_field = field or "text"
        return str(parsed.get(text_field, "")), parsed
    return raw_line.rstrip("\n"), None


def _ensure_newline(raw_line: str) -> str:
    return raw_line if raw_line.endswith("\n") else raw_line + "\n"


def _iter_parallel_records(source_path: str, target_path: str, mode: str, field: Optional[str]) -> Iterator[Dict[str, Any]]:
    with open(source_path, "r", encoding="utf-8") as source_file, open(target_path, "r", encoding="utf-8") as target_file:
        for idx, pair in enumerate(zip_longest(source_file, target_file, fillvalue=None), start=1):
            source_raw, target_raw = pair
            if source_raw is None or target_raw is None:
                raise ValueError(f"Source and target files have different number of lines at pair {idx}")
            source_text, source_data = _load_record(source_raw, mode, field)
            target_text, target_data = _load_record(target_raw, mode, field)
            yield {
                "index": idx,
                "source_raw": _ensure_newline(source_raw),
                "target_raw": _ensure_newline(target_raw),
                "source_text": source_text,
                "target_text": target_text,
                "source_data": source_data,
                "target_data": target_data,
            }


def _classify_record(
    record: Dict[str, Any],
    previous_target_texts: List[str],
    next_target_texts: List[str],
    args: argparse.Namespace,
) -> Tuple[bool, Dict[str, Any]]:
    score, features = _score_pair(record["source_text"], record["target_text"])
    reasons = _detect_reasons(record["source_text"], record["target_text"], features, args)

    best_neighbor_offset = 0
    best_neighbor_score = score

    for offset, target_text in enumerate(reversed(previous_target_texts), start=1):
        candidate_score, _ = _score_pair(record["source_text"], target_text)
        if candidate_score > best_neighbor_score:
            best_neighbor_score = candidate_score
            best_neighbor_offset = -offset

    for offset, target_text in enumerate(next_target_texts, start=1):
        candidate_score, _ = _score_pair(record["source_text"], target_text)
        if candidate_score > best_neighbor_score:
            best_neighbor_score = candidate_score
            best_neighbor_offset = offset

    suspicious = bool(reasons)
    if best_neighbor_offset != 0 and best_neighbor_score >= score + args.shift_margin:
        suspicious = True
        reasons.append(f"better_match_at_target_offset_{best_neighbor_offset}")

    report_row = {
        "line": record["index"],
        "alignment_score": round(score, 4),
        "best_neighbor_offset": best_neighbor_offset,
        "best_neighbor_score": round(best_neighbor_score, 4),
        "suspicious": suspicious,
        "reasons": reasons,
        "features": {key: round(value, 4) for key, value in features.items()},
        "source_preview": _preview(record["source_text"]),
        "target_preview": _preview(record["target_text"]),
    }
    return suspicious, report_row


def _derive_output_paths(source: str, target: str, output_tag: str, report_path: Optional[str]) -> Dict[str, Path]:
    source_path = Path(source)
    target_path = Path(target)
    source_out = source_path.parent / f"{source_path.stem}{output_tag}{source_path.suffix}"
    target_out = target_path.parent / f"{target_path.stem}{output_tag}{target_path.suffix}"
    source_bad = source_path.parent / f"{source_path.stem}{output_tag}_mismatched{source_path.suffix}"
    target_bad = target_path.parent / f"{target_path.stem}{output_tag}_mismatched{target_path.suffix}"
    default_report = source_path.parent / f"{source_path.stem}{output_tag}_report.jsonl"
    return {
        "source_out": source_out,
        "target_out": target_out,
        "source_bad": source_bad,
        "target_bad": target_bad,
        "report": Path(report_path) if report_path else default_report,
    }


def run_mt_alignment(args: argparse.Namespace) -> None:
    paths = _derive_output_paths(args.source, args.target, args.output_tag, args.report_path)
    record_iter = _iter_parallel_records(args.source, args.target, args.mode, args.field)
    future_buffer = deque()
    previous_target_texts = deque(maxlen=max(args.neighbor_window, 0))
    target_future_size = max(args.neighbor_window, 0) + 1

    while len(future_buffer) < target_future_size:
        try:
            future_buffer.append(next(record_iter))
        except StopIteration:
            break

    total_pairs = 0
    kept_pairs = 0
    mismatched_pairs = 0

    with open(paths["source_out"], "w", encoding="utf-8") as source_out, \
         open(paths["target_out"], "w", encoding="utf-8") as target_out, \
         open(paths["source_bad"], "w", encoding="utf-8") as source_bad, \
         open(paths["target_bad"], "w", encoding="utf-8") as target_bad, \
         open(paths["report"], "w", encoding="utf-8") as report_file:
        while future_buffer:
            record = future_buffer.popleft()
            total_pairs += 1
            next_target_texts = [item["target_text"] for item in list(future_buffer)[:args.neighbor_window]]
            suspicious, report_row = _classify_record(
                record,
                list(previous_target_texts),
                next_target_texts,
                args,
            )
            report_file.write(json.dumps(report_row, ensure_ascii=False) + "\n")

            if suspicious:
                mismatched_pairs += 1
                source_bad.write(record["source_raw"])
                target_bad.write(record["target_raw"])
            else:
                kept_pairs += 1
                source_out.write(record["source_raw"])
                target_out.write(record["target_raw"])

            previous_target_texts.append(record["target_text"])

            while len(future_buffer) < target_future_size:
                try:
                    future_buffer.append(next(record_iter))
                except StopIteration:
                    break

    print(f"Processed {total_pairs} parallel pairs")
    print(f"Aligned output: {paths['source_out']} and {paths['target_out']}")
    print(f"Mismatched output: {paths['source_bad']} and {paths['target_bad']}")
    print(f"Report: {paths['report']}")
    print(f"Kept pairs: {kept_pairs}")
    print(f"Potentially misaligned pairs: {mismatched_pairs}")
