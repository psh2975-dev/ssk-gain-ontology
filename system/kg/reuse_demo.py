# -*- coding: utf-8 -*-
"""재사용/상호운용 시연 (제3자 소비자 관점).

발행된 온톨로지 파일을 빌드 파이프라인과 무관하게 새로 적재하여, 온톨로지가
스키마 계약으로 재사용 가능함을 보인다.

시연 4단계:
  (1) 모듈 문서 발견: 소비자가 어느 모듈 문서를 가져올지 owl:imports 로 판단
  (2) 모듈 단독 적재 + imports 실제 해소: intl.ttl 만 열어 선언된 import 를
      따라가며 필요한 문서만 적재한다(병합본 ontology.ttl 은 열지 않는다)
  (3) 그 부분 그래프를 스키마 계약으로 삼아 제3자 인스턴스 검증 → SHACL 적합
  (4) 정준 식별자 기반 조인 질의가 제3자 데이터에서 성립

시연이 성립하려면 세 조건을 지켜야 한다. 병합본이 아니라 모듈 문서에서
출발해 imports 를 실제로 해소할 것, SHACL 에 온톨로지 전체를 ont_graph 로
넘기는 공허 설정을 피할 것, 소비자 데이터만 검증 대상으로 둘 것.

인스턴스는 재사용 기제 시연용 예시이며 실제 기업이 아니다.
산출: out/reuse_demo_report.json
"""
from __future__ import annotations

# 콘솔 인코딩 방어. 윈도 기본 콘솔(cp949 등)에서는 비ASCII 문자를 출력할 때
# UnicodeEncodeError 로 죽는다. 표준 출력만 UTF-8 로 재설정한다.
import sys as _sys
if hasattr(_sys.stdout, "reconfigure"):
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import json
import sys
from pathlib import Path
from rdflib import Graph, Namespace, Literal, RDF, OWL, URIRef
from pyshacl import validate

HERE = Path(__file__).resolve().parent
ONTO = HERE.parent / "ontology"
OUT = HERE / "out"
sys.path.insert(0, str(ONTO))
from validate import ont_for_shacl          # 비-vacuity 정본 구현 재사용

BASE = "https://w3id.org/ssk-gain/ontology/"
CORE = Namespace(BASE + "core#")
INTL = Namespace(BASE + "intl#")
KG = Namespace("https://w3id.org/ssk-gain/kg/")

report = {"artifact": "module documents (core/intl/gvc/bridge.ttl) + shapes.ttl",
          "steps": {}}


def module_path(iri: str) -> Path:
    """모듈 IRI → 배포 문서 경로. w3id 등록 후에는 이 자리가 HTTP 역참조가 된다."""
    return ONTO / f"{str(iri).rstrip('/').split('/')[-1]}.ttl"


def load_with_imports(start_iri: str) -> tuple[Graph, list[str]]:
    """모듈 문서 하나에서 시작해 owl:imports 를 실제로 따라가며 적재한다."""
    g, seen, queue, order = Graph(), set(), [start_iri], []
    while queue:
        iri = queue.pop(0)
        if iri in seen:
            continue
        seen.add(iri)
        p = module_path(iri)
        if not p.exists():
            raise SystemExit(f"모듈 문서 없음: {p.name} (IRI {iri})")
        g.parse(str(p), format="turtle")
        order.append(p.name)
        for o in g.objects(URIRef(iri), OWL.imports):
            queue.append(str(o))
    return g, order


# (1) 모듈 문서 발견
available = {}
for m in ("core", "intl", "gvc", "bridge"):
    p = ONTO / f"{m}.ttl"
    if p.exists():
        mg = Graph().parse(str(p), format="turtle")
        available[m] = sorted(str(o).split("/")[-1]
                              for o in mg.objects(URIRef(BASE + m), OWL.imports))
report["steps"]["1_module_documents"] = {
    "desc": "The released module documents and the owl:imports each declares",
    "documents": available,
    "found": sorted(available)}

# (2) intl 모듈만 지정해 imports 를 실제로 해소 (병합본 미사용)
schema, loaded = load_with_imports(BASE + "intl")
intl_classes = sorted(str(c).split("#")[-1] for c in schema.subjects(RDF.type, OWL.Class)
                      if str(c).startswith(BASE + "intl#"))
pulled_gvc = any(str(c).startswith(BASE + "gvc#") for c in schema.subjects(RDF.type, OWL.Class))
report["steps"]["2_standalone_module_reuse"] = {
    "desc": "Starting from intl.ttl, load only what its imports declare, as a sanctions-domain consumer would",
    "documents_loaded": loaded,
    "schema_triples": len(schema),
    "intl_named_classes": intl_classes,
    "supply_chain_module_pulled_in": pulled_gvc,
    "reusable": bool(intl_classes) and not pulled_gvc}

# (3) 제3자 인스턴스를 그 부분 스키마로 검증
consumer = Graph()
consumer.bind("core", CORE); consumer.bind("intl", INTL); consumer.bind("kg", KG)
org = KG["org:EXTERNAL-CONSUMER-DEMO"]
consumer.add((org, RDF.type, CORE.Organization))
consumer.add((org, CORE.lei, Literal("DEMOCONSUMER00000012")))   # ISO 17442 형식(20자), 예시
consumer.add((org, CORE.label, Literal("External Consumer Record (demo)")))
country = KG["country:KOR"]
consumer.add((country, RDF.type, CORE.Country))
consumer.add((country, CORE.isoAlpha3, Literal("KOR")))
consumer.add((country, CORE.canonicalId, Literal("KOR")))
consumer.add((org, INTL.headquarteredIn, country))

# 소비자 데이터만 검증 대상으로 두고, 부분 스키마는 ont_graph 로만 준다.
# domain/range 를 제거해 sh:class 검사의 공허를 차단한다(validate.py 와 동일).
conforms, _, rtext = validate(consumer,
                              shacl_graph=str(ONTO / "shapes.ttl"),
                              ont_graph=ont_for_shacl(schema),
                              inference="rdfs", advanced=True)

# (4) 정준 식별자 기반 조인 질의
q = """PREFIX core:<https://w3id.org/ssk-gain/ontology/core#>
PREFIX intl:<https://w3id.org/ssk-gain/ontology/intl#>
SELECT ?lei ?iso WHERE { ?o core:lei ?lei ; intl:headquarteredIn ?c . ?c core:isoAlpha3 ?iso }"""
rows = [{"lei": str(r[0]), "hq_iso": str(r[1])} for r in consumer.query(q)]
report["steps"]["3_external_instance_validation"] = {
    "desc": "Validate third-party instances against the partial schema under a non-vacuous SHACL configuration, then join on the canonical identifier",
    "validated_graph": "consumer instances only (ontology supplied as ont_graph)",
    "shacl_conforms": bool(conforms),
    "violations": rtext.count("Constraint Violation"),
    "query_rows": rows,
    "reuse_ok": bool(conforms) and len(rows) == 1}

report["all_ok"] = (report["steps"]["2_standalone_module_reuse"]["reusable"]
                    and report["steps"]["3_external_instance_validation"]["reuse_ok"])
OUT.mkdir(exist_ok=True)
(OUT / "reuse_demo_report.json").write_text(
    json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(report, ensure_ascii=False, indent=1))
raise SystemExit(0 if report["all_ok"] else 1)
