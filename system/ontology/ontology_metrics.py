# -*- coding: utf-8 -*-
"""온톨로지 구조지표 산출(OntoMetrics 등가, 재현 스크립트).

ontology.ttl에서 스키마 구조 지표를 결정론적으로 계산한다. OOPS!(외부 웹서비스)가
불안정하여, 스키마 품질 근거는 (1) 본 구조지표 + (2) validate.py의 형식검증
(OWL RL 일관성·SHACL 실인스턴스)으로 구성한다.

산출: out/ontology_metrics.json
실행: $env:PYTHONUTF8=1; python ontology_metrics.py
"""
from __future__ import annotations

# 콘솔 인코딩 방어. 윈도 기본 콘솔(cp949 등)에서는 비ASCII 문자를 출력할 때
# UnicodeEncodeError 로 죽는다. 표준 출력만 UTF-8 로 재설정한다.
import sys as _sys
if hasattr(_sys.stdout, "reconfigure"):
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import json
from pathlib import Path
from rdflib import Graph, URIRef, RDF, RDFS, OWL

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
OUT.mkdir(exist_ok=True)

g = Graph().parse(str(HERE / "ontology.ttl"), format="turtle")

cls = set(g.subjects(RDF.type, OWL.Class)) | set(g.subjects(RDF.type, RDFS.Class))
# 명명 클래스만: URIRef이고 ssk 네임스페이스. owl:unionOf 등 익명(BNode) 클래스는 제외.
named = [c for c in cls if isinstance(c, URIRef) and str(c).startswith("https://w3id.org/ssk-gain/ontology")]
obj = set(g.subjects(RDF.type, OWL.ObjectProperty))
dat = set(g.subjects(RDF.type, OWL.DatatypeProperty))
subclass = list(g.triples((None, RDFS.subClassOf, None)))
disj = list(g.triples((None, OWL.disjointWith, None)))
dom = list(g.triples((None, RDFS.domain, None)))
rng = list(g.triples((None, RDFS.range, None)))
labeled = [c for c in named if (c, RDFS.label, None) in g]


def depth(c, seen=None):
    seen = seen or set()
    parents = [o for o in g.objects(c, RDFS.subClassOf) if o in cls and o not in seen]
    return 1 + max([depth(p, seen | {c}) for p in parents], default=0)


n_cls = len(named)
n_prop = len(obj) + len(dat)
metrics = {
    "source": "ontology.ttl",
    "named_classes": n_cls,
    "object_properties": len(obj),
    "datatype_properties": len(dat),
    "subClassOf_axioms": len(subclass),
    "disjointWith_axioms": len(disj),
    "domain_declarations": len(dom),
    "range_declarations": len(rng),
    "label_coverage": round(len(labeled) / n_cls, 3) if n_cls else 0,
    "attribute_richness": round(n_prop / n_cls, 3) if n_cls else 0,
    "inheritance_depth_max": max([depth(c) for c in named], default=1),
    "relationship_richness": round(len(obj) / (len(obj) + len(subclass)), 3) if (len(obj) + len(subclass)) else 0,
    "axiomatization_note": "Domain and range declarations exceed the property count because a union range contributes several declarations. The formal domain and range constraints are checked by SHACL (validate.py).",
}
(OUT / "ontology_metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=1), encoding="utf-8")
for k, v in metrics.items():
    print(f"  {k}: {v}")
