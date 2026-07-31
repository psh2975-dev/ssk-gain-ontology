# -*- coding: utf-8 -*-
"""보충자료 Table S9 생성: 전 속성의 정의역·치역 선언.

원고 3-8절이 「공리 전량을 제시한다」고 말하면서 최대 집단인 정의역·치역을 보충자료로
위임한다. 그 표가 실재해야 그 문장이 참이 된다. 손으로 적으면 어휘가 바뀔 때마다
어긋나므로 ontology.ttl 에서 생성한다.

실행: $env:PYTHONUTF8=1; python build_supp_table_s9.py
"""
from __future__ import annotations

import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from pathlib import Path

from rdflib import Graph, RDF, RDFS, OWL, URIRef
from rdflib.collection import Collection

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
ONT = ROOT / "system" / "ontology" / "ontology.ttl"
OUT = HERE.parent / "draft" / "supp_table_s9.md"
BASE = "https://w3id.org/ssk-gain/ontology/"


def qname(u) -> str:
    s = str(u)
    if s.startswith(BASE) and "#" in s:
        mod, local = s[len(BASE):].split("#", 1)
        return f"{mod}:{local}"
    for pfx, ns in (("owl", "http://www.w3.org/2002/07/owl#"),
                    ("rdfs", "http://www.w3.org/2000/01/rdf-schema#"),
                    ("xsd", "http://www.w3.org/2001/XMLSchema#"),
                    ("prov", "http://www.w3.org/ns/prov#"),
                    ("time", "http://www.w3.org/2006/time#"),
                    ("org", "http://www.w3.org/ns/org#")):
        if s.startswith(ns):
            return pfx + ":" + s[len(ns):]
    return s


def render(g: Graph, node) -> str:
    """union 등 익명 클래스는 구성 요소를 펴서 표기한다."""
    if node is None:
        return "not declared"
    if (node, OWL.unionOf, None) in g:
        members = list(Collection(g, next(g.objects(node, OWL.unionOf))))
        return " OR ".join(qname(x) for x in members)
    return qname(node)


def characteristics(g: Graph, p) -> str:
    marks = []
    for t, lab in ((OWL.FunctionalProperty, "F"), (OWL.InverseFunctionalProperty, "IF"),
                   (OWL.TransitiveProperty, "T"), (OWL.SymmetricProperty, "S"),
                   (OWL.IrreflexiveProperty, "Ir")):
        if (p, RDF.type, t) in g:
            marks.append(lab)
    sup = [qname(o) for o in g.objects(p, RDFS.subPropertyOf)]
    if sup:
        marks.append("sub of " + ", ".join(sup))
    inv = [qname(o) for o in g.objects(p, OWL.inverseOf)]
    if inv:
        marks.append("inverse of " + ", ".join(inv))
    return "; ".join(marks) or "-"


def main() -> int:
    g = Graph().parse(str(ONT), format="turtle")
    rows, n_dom, n_rng = [], 0, 0
    for kind, label in ((OWL.ObjectProperty, "object"), (OWL.DatatypeProperty, "datatype")):
        props = sorted((p for p in g.subjects(RDF.type, kind)
                        if str(p).startswith(BASE)), key=qname)
        for p in props:
            doms = list(g.objects(p, RDFS.domain))
            rngs = list(g.objects(p, RDFS.range))
            n_dom += len(doms)
            n_rng += len(rngs)
            rows.append((qname(p), label,
                         " ; ".join(render(g, d) for d in doms) or "not declared",
                         " ; ".join(render(g, r) for r in rngs) or "not declared",
                         characteristics(g, p)))

    lines = [
        "## Supplementary Table S9. Domain and range declarations of every property",
        "",
        f"Generated from ontology.ttl by `scripts/build_supp_table_s9.py`. "
        f"{len(rows)} properties carry {n_dom} domain and {n_rng} range declarations. "
        "Characteristics: F functional, IF inverse functional, T transitive, S symmetric, "
        "Ir irreflexive. A union range is written with OR.",
        "",
        "| Property | Kind | Domain | Range | Characteristics |",
        "|---|---|---|---|---|",
    ]
    lines += [f"| `{a}` | {b} | `{c}` | `{d}` | {e} |" for a, b, c, d, e in rows]
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"저장 -> {OUT.name}")
    print(f"속성 {len(rows)} · 정의역 {n_dom} · 치역 {n_rng}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
