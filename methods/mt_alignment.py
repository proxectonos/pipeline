import argparse
import json
import re
import unicodedata
from collections import Counter
from itertools import zip_longest
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

from tqdm import tqdm


TOKEN_RE = re.compile(r"\w+", re.UNICODE)
NUMBER_RE = re.compile(r"\d+(?:[.,:/-]\d+)*")
URL_RE = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.IGNORECASE)
PUNCT_CHARS = ".,;:!?()[]{}\"'%-"


_EMBEDDING_MODEL = None


def _load_embedding_model(model_name: str, device: str):
    global _EMBEDDING_MODEL
    if _EMBEDDING_MODEL is None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise ImportError(
                "sentence-transformers is required for mt_alignment. Install with: pip install sentence-transformers"
            ) from exc
        _EMBEDDING_MODEL = SentenceTransformer(model_name, device=device)
    return _EMBEDDING_MODEL


def _encode_batch(texts: List[str], model_name: str, device: str, batch_size: int):
    model = _load_embedding_model(model_name, device)
    return model.encode(
        texts,
        batch_size=batch_size,
        normalize_embeddings=True,
        show_progress_bar=True,
    )


def _paired_cosine_similarities(source_embs, target_embs) -> List[float]:
    try:
        import numpy as np
    except ImportError as exc:
        raise ImportError("numpy is required for mt_alignment") from exc
    return np.sum(source_embs * target_embs, axis=1).astype(float).tolist()


def _pair_similarity(source_emb, target_emb) -> float:
    # Embeddings are already L2-normalized.
    return float((source_emb * target_emb).sum())


def _strip_accents(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def _fold_text(text: str) -> str:
    return _strip_accents(text).lower()


def _tokenize(text: str) -> List[str]:
    return TOKEN_RE.findall(_fold_text(text))


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


def _optional_anchor_score(source_items: Set[str], target_items: Set[str]) -> Optional[float]:
    if not source_items and not target_items:
        return None
    return _jaccard(source_items, target_items)


def _preview(text: str, limit: int = 120) -> str:
    compact = re.sub(r"\s+", " ", text).strip()
    return compact[:limit] + ("..." if len(compact) > limit else "")


def _compute_pair_features(source_text: str, target_text: str) -> Dict[str, float]:
    features: Dict[str, float] = {
        "length_ratio": _length_ratio(source_text, target_text),
        "punctuation_similarity": _counter_similarity(
            _extract_punctuation_profile(source_text),
            _extract_punctuation_profile(target_text),
        ),
    }
    number_anchor = _optional_anchor_score(set(NUMBER_RE.findall(source_text)), set(NUMBER_RE.findall(target_text)))
    url_anchor = _optional_anchor_score(set(URL_RE.findall(source_text)), set(URL_RE.findall(target_text)))
    email_anchor = _optional_anchor_score(set(EMAIL_RE.findall(source_text)), set(EMAIL_RE.findall(target_text)))
    if number_anchor is not None:
        features["number_anchor"] = number_anchor
    if url_anchor is not None:
        features["url_anchor"] = url_anchor
    if email_anchor is not None:
        features["email_anchor"] = email_anchor
    return features


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
    if features.get("punctuation_similarity", 1.0) < getattr(args, "min_punctuation_similarity", 0.0):
        reasons.append("punctuation_mismatch")
    if features.get("embedding_similarity", 1.0) < args.score_threshold:
        reasons.append("low_embedding_similarity")
    return reasons


def _load_record(raw_line: str, mode: str, field: Optional[str]) -> Tuple[str, Optional[Dict[str, Any]]]:
    if mode == "jsonl":
        parsed = json.loads(raw_line)
        text_field = field or "text"
        return str(parsed.get(text_field, "")), parsed
    return raw_line.rstrip("\n"), None


def _ensure_newline(raw_line: str) -> str:
    return raw_line if raw_line.endswith("\n") else raw_line + "\n"


def _load_all_records(
    source_path: str,
    target_path: str,
    mode: str,
    field: Optional[str],
) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    with open(source_path, "r", encoding="utf-8") as source_file:
        source_lines = sum(1 for _ in source_file)

    with open(source_path, "r", encoding="utf-8") as source_file, open(target_path, "r", encoding="utf-8") as target_file:
        iterator = enumerate(zip_longest(source_file, target_file, fillvalue=None), start=1)
        iterator = tqdm(iterator, total=source_lines, desc="Loading parallel pairs", unit="lines")
        for idx, pair in iterator:
            source_raw, target_raw = pair
            if source_raw is None or target_raw is None:
                raise ValueError(f"Source and target files have different number of lines at pair {idx}")
            source_text, source_data = _load_record(source_raw, mode, field)
            target_text, target_data = _load_record(target_raw, mode, field)
            records.append(
                {
                    "index": idx,
                    "source_raw": _ensure_newline(source_raw),
                    "target_raw": _ensure_newline(target_raw),
                    "source_text": source_text,
                    "target_text": target_text,
                    "source_data": source_data,
                    "target_data": target_data,
                }
            )
    return records


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
    records = _load_all_records(args.source, args.target, args.mode, args.field)
    source_texts = [record["source_text"] for record in records]
    target_texts = [record["target_text"] for record in records]

    print("Encoding source sentences...")
    source_embs = _encode_batch(source_texts, args.model, args.device, args.batch_size)
    print("Encoding target sentences...")
    target_embs = _encode_batch(target_texts, args.model, args.device, args.batch_size)
    pair_scores = _paired_cosine_similarities(source_embs, target_embs)

    total_pairs = len(records)
    kept_pairs = 0
    mismatched_pairs = 0
    neighbor_window = max(args.neighbor_window, 0)

    with open(paths["source_out"], "w", encoding="utf-8") as source_out, \
         open(paths["target_out"], "w", encoding="utf-8") as target_out, \
         open(paths["source_bad"], "w", encoding="utf-8") as source_bad, \
         open(paths["target_bad"], "w", encoding="utf-8") as target_bad, \
         open(paths["report"], "w", encoding="utf-8") as report_file:
        row_iterable = enumerate(records)
        row_iterable = tqdm(row_iterable, total=total_pairs, desc="Scoring and writing", unit="pairs")
        for idx, record in row_iterable:
            score = pair_scores[idx]
            features = _compute_pair_features(record["source_text"], record["target_text"])
            features["embedding_similarity"] = score
            features["alignment_score"] = score
            reasons = _detect_reasons(record["source_text"], record["target_text"], features, args)

            best_neighbor_offset = 0
            best_neighbor_score = score
            for offset in range(1, neighbor_window + 1):
                prev_idx = idx - offset
                next_idx = idx + offset
                if prev_idx >= 0:
                    candidate_score = _pair_similarity(source_embs[idx], target_embs[prev_idx])
                    if candidate_score > best_neighbor_score:
                        best_neighbor_score = candidate_score
                        best_neighbor_offset = -offset
                if next_idx < total_pairs:
                    candidate_score = _pair_similarity(source_embs[idx], target_embs[next_idx])
                    if candidate_score > best_neighbor_score:
                        best_neighbor_score = candidate_score
                        best_neighbor_offset = offset

            suspicious = bool(reasons)
            if best_neighbor_offset != 0 and best_neighbor_score >= score + args.shift_margin:
                suspicious = True
                reasons.append(f"better_match_at_target_offset_{best_neighbor_offset}")

            report_row = {
                "line": record["index"],
                "embedding_similarity": round(score, 4),
                "alignment_score": round(score, 4),
                "best_neighbor_offset": best_neighbor_offset,
                "best_neighbor_score": round(best_neighbor_score, 4),
                "suspicious": suspicious,
                "reasons": reasons,
                "features": {key: round(value, 4) for key, value in features.items()},
                "source_preview": _preview(record["source_text"]),
                "target_preview": _preview(record["target_text"]),
            }
            report_file.write(json.dumps(report_row, ensure_ascii=False) + "\n")

            if suspicious:
                mismatched_pairs += 1
                source_bad.write(record["source_raw"])
                target_bad.write(record["target_raw"])
            else:
                kept_pairs += 1
                source_out.write(record["source_raw"])
                target_out.write(record["target_raw"])

    print(f"Processed {total_pairs} parallel pairs")
    print(f"Aligned output: {paths['source_out']} and {paths['target_out']}")
    print(f"Mismatched output: {paths['source_bad']} and {paths['target_bad']}")
    print(f"Report: {paths['report']}")
    print(f"Kept pairs: {kept_pairs}")
    print(f"Potentially misaligned pairs: {mismatched_pairs}")
