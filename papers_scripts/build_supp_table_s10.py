# -*- coding: utf-8 -*-
"""보충자료 Table S10 생성: 기탁 그래프 인스턴스 통계.

리뷰 M3: 카탈로그 규모가 본문에 분산되어 「연구 질문에 답하기에 충분한가」를
판단할 기반이 없다는 지적. 클래스별 인스턴스 수 · 술어별 트리플 수 · 출처별
레코드 수를 기탁 그래프에서 직접 세어 표로 낸다. 손으로 두면 그래프가 바뀔
때마다 뒤처지므로 생성기로 만든다.

실행: $env:PYTHONUTF8=1; python build_supp_table_s10.py
"""
from __future__ import annotations

import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from collections import Counter
from pathlib import Path

from rdflib import Graph, RDF, URIRef

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
DEP = ROOT / "system" / "kg" / "out" / "pilot_kg_deposit.ttl"
SUPP = HERE.parent / "draft" / "PAP01_supplementary_EN.md"

NS = "https://w3id.org/ssk-gain/ontology/"
PROV = "http://www.w3.org/ns/prov#"


def qn(u) -> str:
    s = str(u)
    if s.startswith(NS):
        mod, _, local = s[len(NS):].partition("#")
        return f"{mod}:{local}"
    if s.startswith(PROV):
        return "prov:" + s[len(PROV):]
    if "rdf-schema#" in s:
        return "rdfs:" + s.rsplit("#", 1)[-1]
    if "22-rdf-syntax-ns#" in s:
        return "rdf:" + s.rsplit("#", 1)[-1]
    return s


def main() -> int:
    g = Graph()
    g.parse(str(DEP), format="turtle")

    # 클래스별 인스턴스 (온톨로지 명명 클래스만)
    cls_cnt = Counter()
    for s, o in g.subject_objects(RDF.type):
        q = qn(o)
        if q.startswith(("core:", "intl:", "gvc:", "bridge:")):
            cls_cnt[q] += 1

    # 술어별 트리플
    pred_cnt = Counter(qn(p) for p in g.predicates())

    # 출처별 노드 (core:source 를 가진 주어 기준; 레코드 개체는 별도 집계)
    SRC = URIRef(NS + "core#source")
    REC = URIRef(NS + "core#Record")
    src_nodes = Counter()
    src_records = Counter()
    for s, o in g.subject_objects(SRC):
        if (s, RDF.type, REC) in g:
            src_records[str(o)] += 1
        else:
            src_nodes[str(o)] += 1

    lines = [
        "## Supplementary Table S10. Instance statistics of the deposited graph",
        "",
        f"Counted from pilot_kg_deposit.ttl ({len(g):,} triples) by "
        "scripts/build_supp_table_s10.py; regenerate after any change to the "
        "deposit. Three tabulations: instances per named class, triples per "
        "predicate, and source-tagged nodes and record individuals per source. "
        "A node typed in several classes counts once per class, which is the "
        "dual typing cross-domain integration relies on.",
        "",
        "### S10.1 Instances per named class",
        "",
        "| Class | Instances |",
        "|------|---:|",
        *[f"| `{k}` | {v:,} |" for k, v in sorted(cls_cnt.items(),
                                                  key=lambda x: (-x[1], x[0]))],
        "",
        "### S10.2 Triples per predicate",
        "",
        "| Predicate | Triples |",
        "|------|---:|",
        *[f"| `{k}` | {v:,} |" for k, v in sorted(pred_cnt.items(),
                                                  key=lambda x: (-x[1], x[0]))],
        "",
        "### S10.3 Source-tagged nodes and record individuals per source",
        "",
        "The catalogue nodes carry core:source as a list-level tag; lineage "
        "attaches to record individuals (Section 3.2). The 22 dependency "
        "products are the semiconductor-related HS6 codes of the BACI "
        "collection filter shipped with the deposit.",
        "",
        "| Source | Catalogue nodes | Record individuals |",
        "|------|---:|---:|",
        *[f"| {k} | {src_nodes.get(k, 0):,} | {src_records.get(k, 0):,} |"
          for k in sorted(set(src_nodes) | set(src_records),
                          key=lambda x: (-src_nodes.get(x, 0)
                                         - src_records.get(x, 0), x))],
    ]

    t = SUPP.read_text(encoding="utf-8")
    start = t.find("## Supplementary Table S10.")
    if start >= 0:
        nxt = t.find("\n## Supplementary ", start + 10)
        end = nxt if nxt > 0 else len(t)
        t = t[:start] + "\n".join(lines) + "\n\n" + t[end:].lstrip("\n")
    else:
        t = t.rstrip() + "\n\n" + "\n".join(lines) + "\n"
    SUPP.write_text(t, encoding="utf-8")
    print(f"S10 재생성 — 클래스 {len(cls_cnt)} · 술어 {len(pred_cnt)} · "
          f"출처 {len(set(src_nodes) | set(src_records))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
