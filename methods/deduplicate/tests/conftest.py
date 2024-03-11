import pytest


@pytest.fixture
def json_sample_docs():
    """
    Returns a string with documents in JSON line format.
    """
    return r"""{"text": "Santa Teresa e o Ano Xubilar Teresiano\nA Nosa Voz"}
{"text": "No trascurso do campionato foi quen de vencer a varios campions nacionais e europeos, e únicamente cedeu na octava rolda ante Iñigo López Mulet que acabou por converterse no campión do torneo. Na derradeira rolda enfrontábase o campión catalán Alexander Ventura."}
{"text": "Santa Teresa e o Ano Xubilar Teresiano\nA Nosa Voz"}"""  # noqa


@pytest.fixture
def newline_sample_docs():
    """
    Returns a string with documents separated by 3 newlines.
    """
    return """Santa Teresa e o Ano Xubilar Teresiano

A Nosa Voz


No trascurso do campionato foi quen de vencer a varios campions nacionais e europeos, e únicamente cedeu na octava rolda ante Iñigo López Mulet que acabou por converterse no campión do torneo. Na derradeira rolda enfrontábase o campión catalán Alexander Ventura.


Santa Teresa e o Ano Xubilar Teresiano
A Nosa Voz"""  # noqa


@pytest.fixture
def json_expected_default():
    """
    Returns a list with documents in JSON line format.
    """
    return ["Santa Teresa e o Ano Xubilar Teresiano\nA Nosa Voz", "No trascurso do campionato foi quen de vencer a varios campions nacionais e europeos, e únicamente cedeu na octava rolda ante Iñigo López Mulet que acabou por converterse no campión do torneo. Na derradeira rolda enfrontábase o campión catalán Alexander Ventura.", "Santa Teresa e o Ano Xubilar Teresiano\nA Nosa Voz"]  # noqa


@pytest.fixture
def newline_expected_default():
    """
    Returns a list with documents
    """
    return ["""Santa Teresa e o Ano Xubilar Teresiano
A Nosa Voz""", """No trascurso do campionato foi quen de vencer a varios campions nacionais e europeos, e únicamente cedeu na octava rolda ante Iñigo López Mulet que acabou por converterse no campión do torneo. Na derradeira rolda enfrontábase o campión catalán Alexander Ventura.""", """Santa Teresa e o Ano Xubilar Teresiano
A Nosa Voz"""]  # noqa


@pytest.fixture
def newline_expected_two_lf_in_one_lf_out():
    """
    Returns a list with documents
    """
    return ["Santa Teresa e o Ano Xubilar Teresiano", "A Nosa Voz", "No trascurso do campionato foi quen de vencer a varios campions nacionais e europeos, e únicamente cedeu na octava rolda ante Iñigo López Mulet que acabou por converterse no campión do torneo. Na derradeira rolda enfrontábase o campión catalán Alexander Ventura.", """Santa Teresa e o Ano Xubilar Teresiano
A Nosa Voz"""]  # noqa


@pytest.fixture
def newline_docs_not_normalized():
    """
    Returns a string with documents separated by 3 newlines.
    """
    return """   Santa Teresa       e o Ano Xubilar Teresiano

A Nosa Voz


---No trascurso do campionato foi quen de vencer a varios campions nacionais e europeos, e únicamente cedeu na octava rolda ante Iñigo López Mulet que acabou por converterse no campión do torneo. Na derradeira rolda enfrontábase o campión catalán Alexander Ventura.


Santa Teresa e o Ano Xubilar Teresiano
A Nosa. . .Voz"""  # noqa


@pytest.fixture
def newline_expected_normalized():
    """
    Returns a list with documents
    """
    return ["""Santa Teresa e o Ano Xubilar Teresiano
A Nosa Voz""", "No trascurso do campionato foi quen de vencer a varios campions nacionais e europeos, e únicamente cedeu na octava rolda ante Iñigo López Mulet que acabou por converterse no campión do torneo. Na derradeira rolda enfrontábase o campión catalán Alexander Ventura.", """Santa Teresa e o Ano Xubilar Teresiano
A Nosa Voz"""]  # noqa


@pytest.fixture
def newline_without_duplicates():
    """
    Returns a string with documents separated by 3 newlines.
    """
    return """Jácome e Reigosa mantiveron un encontro esta mañá en dependencias da alcaldía
A vicerreitora do campus de Ourense e o secretario xeral acompañaron a Reigosa na xuntanza con Jácome
De “frutífera” cualificou o alcalde de Ourense, Gonzalo Pérez Jácome, a reunión que esta mañá mantivo en dependencias da alcaldía co reitor da Universidade de Vigo, Manuel Reigosa, e na que ambos avanzaron en diferentes liñas de colaboración entre ambas institucións centradas no reforzo da oferta formativa do campus de Ourense e o desenvolvemento de proxectos de futuro como o Centro de Intelixencia Artificial.
Na xuntanza celebrada este mércores, o reitor trasladoulle ao alcalde a intención da Universidade de implantar no campus ourensán no curso 2020/2021 o Grao en Relacións Internacionais, segundo o acordo acadado a finais do pasado mes de xullo entre a Consellería de Educación, Universidade e Formación Profesional e as universidades galegas. Pola súa banda, o alcalde comprometeuse a que o Concello facilitará espazos axeitados para impartir as clases os primeiros cursos. O reitor agradeceu a “excelente receptividade” do Concello ás necesidades da Universidade no campus de Ourense, ao tempo que expresou a súa satisfacción por contar cunha nova titulación que “engade potencialidade ao campus e vai estar relacionada con titulacións que xa se imparten aquí en Ourense”.
En relación co futuro Centro de Intelixencia Artificial, a xuntanza de hoxe tamén serviu para “afianzar a cooperación clara” da Universidade co proxecto promovido polo Concello e sobre o que proximamente o alcalde manterá un encontro co director da Escola Superior de Enxeñaría Informática. Reigosa cualificou o Centro como“ un proxecto de cidade moi interesante, que pode rexenerar moitas sinerxías coa nosa escola de informática, polo que estamos dispostos a apoiar o proxecto e esperamos que sexa un éxito para a cidade, para a cidadanía e para as dúas institucións”, sinalou o reitor.


Consideran que a lexislación debería ser máis flexible e non distinguir entre tipos de apostas
A lexislación española debería ser máis flexible co sistema impositivo das apostas deportivas e non distinguir entre os diferentes tipos (mutuas, contraportidas, cruzadas...), senón enfocarse unicamente nos beneficios das empresas. Así o defenden un grupo de cinco investigadores e investigadoras do grupo Ecosot, Economía, Sociedade e Territorio, autores do proxecto de investigación Deseño de regras de reparto e medición das desigualdades laborais, financiado polo Ministerio de Economía e Competividade con algo máis de 50.000 euros e no que, entre outras múltiples cuestións, analizaron as principais vantaxes e inconvenientes do actual sistema impositivo que se aplica en España ás apostas deportivas, un mercado que está regulado pola Lei 13/2011, de 27 de maio.
Nos últimos anos moitos países europeos, incluída España, comezaron a regular o seu mercado de apostas e xogos en liña, non obstante, esta regularización non foi uniforme en todos os países. “No noso proxecto o que fixemos foi analizar as vantaxes e inconvenientes dos diversos sistemas de cara a facer achegas que poderían axudar a mellorar”, explica o catedrático Gustavo Bergantiños, investigador principal do proxecto.
As apostas deportivas teñen unha longa tradición en España debido á forte implantación das quinielas, pero a irrupción de Internet trouxo consigo unha forte revolución neste sector coa aparición das casas de aposta en liña que ofrecían unha gran variedade de xogos de azar, incluíndo as apostas deportivas, o póker ou o casino virtual. “A medida que Internet se facía máis popular estas empresas foron incrementando tamén a súa penetración, pasando de 90.000 a 370.000 usuarios e usuarias desde 2006 a 2010”, explica o investigador Juan José Vidal, quen fai fincapé en que naquel intre non existía aínda unha lexislación específica para o xogo en liña e as distintas propostas de lexislación que se barallaban non satisfacían nin aos casinos nin as casas de apostas. “Por facer unha analoxía, a problemática era similar a que se vive na actualidade cos taxistas e as empresas tipo Uber ou Cabify”, explica Vidal.
Segundo explica o equipo responsable deste proxecto, a lei de 2011 é moi similar ás existentes en outros países europeos, “se ben os pequenos detalles poden marcar grandes diferencias”, recalca Vidal, no senso de que quen fai unha aposta deportiva, ou xoga ao póker, non está necesariamente deixando todo ao azar, como acontece na lotaría ou na bonoloto.
As apostas deportivas divídense na actualidade en tres tipos: mutuas, contrapartida e cruzadas. “A quiniela é do primeiro tipo, que esencialmente é o mesmo que unha porra na que a recadación repártese entre todos e todas as que acertaron”, explica o investigador. Pola contra, as casas de apostas en liña ofertan basicamente os outros dous tipos: as apostas de contrapartida, nas que se poñen cotas, e as apostas cruzadas, nas que os xogadores/as negocian nun mercado entre eles e a casa actúa como intermediaria cobrando unha comisión. “Desde un punto de vista legal todo isto é moi importante porque existe unha clara distinción entre ofrecer un servizo, tipo taxis, ou ben actuar como intermediario entre particulares, tipo Blablacar, por seguir o exemplo dos taxis e as plataformas sociais”, recalca o investigador.
En xeral, o tipo impositivo pode ser de dous tipos: sobre o volume das apostas ou sobre os beneficios das empresas. No caso da quiniela dedica a premios o 45% da recadación, polo que é un tipo impositivo do primeiro tipo, pero este sistema é inviable para empregar en apostas de contrapartida ou cruzadas tal e como ofrecen as casas de apostas.


Interpretación, dirección, guión, danza... a arte dramática está na Universidade de Vigo
Para profundar na formación integral do alumnado e dentro da nosa aposta cultural, a Universidade de Vigo conta con instalacións como o teatro da cidade universitaria e iniciativas consolidadas como a Aula de Teatro de Vigo e de Ourense, que son as encargadas de programar a formación teatral ao longo do curso académico e de organizar a MITEU (Mostra Internacional de Teatro Universitario) nos dous campus. No campus de Ourense, a universidade conta cunha aula de danza contemporánea que ofrece formación neste campo a todas persoas interesadas.
A aula de danza do campus de Ourense creouse no curso 2010/2011 e oferta cursos de danza e creación escénica. D-ou-tras é o grupo de danza dirixido por trasPediante que se desenvolve no campus de Ourense e que prepara unha peza ao longo do curso académico e que logo amosa en diversos festivais interuniversitarios de danza.
Cada ano, impártense clases de danza e creación escénica. Trabállase unha peza escénica e móstrase en distintos festivais universitarios ou amateurs.
Foi fundado por Marta Alonso e Begoña Cuquejo no curso 2010/2011, e na actualidade é dirixido por trasPediante (Begoña Cuquejo) e impartido por Nuria Sotelo.


O estudo de Noemí Martínez avalía datos dos últimos oito anos na área sanitaria de Vigo
Noemí Martínez López de Castro, farmacéutica do Complexo Hospitalario Universitario de Vigo, CHUVI, analiza na súa tese de doutoramento o perfil dos pacientes con enfermidades reumatolóxicas sometidos a terapias biolóxicas e faino tanto dende a práctica clínica habitual como a través das redes sociais. O estudo foi desenvolvido no ámbito da área sanitaria de Vigo e inclúe unha análise retrospectiva de oito anos dos pacientes con artropatías inflamatorias crónicas (artrite reumatoide, artrite psoriásica e espondilite anquilosante) en tratamento con terapias biolóxicas. O obxectivo desta tese é, como recoñece a autora, mellorar o coñecemento sobre o perfil dos pacientes con estas enfermidades e sobre distintos aspectos destes tratamentos (adherencia/persistencia, seguridade, custos, etc.) e tamén coñecer mellor a vivencia (inquietudes, necesidades e cuestións) que os pacientes con estas enfermidades teñen sobre a súa enfermidade e os seus tratamentos, tanto na súa vida cotiá como en Google e Twitter.
Martínez López de Castro realizou a súa investigación dentro do programa de doutoramento Metodoloxía e Aplicacións en Ciencias da Vida, baixo a dirección do doutor José María Pego a catedrática da Universidade de Vigo África González. O traballo, que contou co apoio da Unidade de Estatística da EOXI de Vigo, desenvolveuse no contexto do Grupo de Investigación Iridis (Investigation in Rheumatology and Immune-Mediated Diseases) pertencente ao Instituto de Investigación Sanitaria Galicia Sur, formado por un grupo de profesionais, principalmente reumatólogos, farmacéuticos e epidemiólogos, que conxuntamente desenvolven investigación na área das enfermidades autoinmunes."""  # noqa
