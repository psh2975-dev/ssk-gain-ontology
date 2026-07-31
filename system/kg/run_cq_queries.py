# -*- coding: utf-8 -*-
"""역량질문 SPARQL 질의 실행 (2026-07-09).

실체화된 파일럿 KG(pilot_kg_demo.ttl)에 CQ4·CQ2·CQ7을 실제 SPARQL로 실행하고
결과를 저장한다. 「질의하였다」는 본 스크립트의 SPARQL 실행을 뜻한다.

CQ7의 HHI는 사전계산값 조회가 아니라 SPARQL 집계(SUM(점유율²))로 그래프에서
직접 산출하며, 카탈로그에 저장된 값(원자료 전량 기준)과 대조한다. 집계지역
(nes 등) 제외분만큼 미세 차이가 나며 그 차이를 함께 보고한다.

산출: out/cq_query_results.json
실행: .venv python (rdflib)
"""
from __future__ import annotations

# 콘솔 인코딩 방어. 윈도 기본 콘솔(cp949 등)에서는 비ASCII 문자를 출력할 때
# UnicodeEncodeError 로 죽는다. 표준 출력만 UTF-8 로 재설정한다.
import sys as _sys
if hasattr(_sys.stdout, "reconfigure"):
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import json
from pathlib import Path
from rdflib import Graph

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
demo_path = OUT / "pilot_kg_demo.ttl"
if not demo_path.exists():
    print("""시연 그래프(out/pilot_kg_demo.ttl) 없음: UN Comtrade 라이선스로 배포본에서
제외되어 있다. materialize_pilot_kg.py 로 원자료에서 재구축하면 본 질의가 재현된다.
산출 결과는 out/cq_query_results.json 에 동봉.""")
    raise SystemExit(2)
g = Graph().parse(str(demo_path), format="turtle")

PREF = """
PREFIX core:   <https://w3id.org/ssk-gain/ontology/core#>
PREFIX intl:   <https://w3id.org/ssk-gain/ontology/intl#>
PREFIX gvc:    <https://w3id.org/ssk-gain/ontology/gvc#>
PREFIX bridge: <https://w3id.org/ssk-gain/ontology/bridge#>
PREFIX rdf:    <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs:   <http://www.w3.org/2000/01/rdf-schema#>
PREFIX xsd:    <http://www.w3.org/2001/XMLSchema#>
"""

# 실행일을 산출물에 넣으면 같은 입력·코드가 날마다 다른 파일을 낸다.
results = {"graph": "pilot_kg_demo.ttl", "triples": len(g), "queries": {}}

# CQ4: 어떤 품목이 어떤 수출통제로 제한되는가
q4 = PREF + """
SELECT ?control ?scope ?hs ?plabel WHERE {
  ?control a intl:ExportControl ; bridge:restricts ?p .
  OPTIONAL { ?control intl:controlScope ?scope }
  ?p core:hsCode ?hs ; rdfs:label ?plabel .
} ORDER BY ?hs"""
rows4 = [{"control": str(r.control), "scope": str(r.scope), "hsCode": str(r.hs), "product": str(r.plabel)}
         for r in g.query(q4)]
results["queries"]["CQ4_restricts"] = {"sparql": "ExportControl -restricts-> Product",
                                       "rows": rows4, "n": len(rows4), "expected_n": 3,
                                       "pass": len(rows4) == 3}

# CQ2: 정책 이벤트 전후 품목 무역흐름 변화 (reified magnitude + 전후 실측값)
q2 = PREF + """
SELECT ?ev ?hs ?mag ?v2018 ?v2020 WHERE {
  ?st rdf:predicate bridge:disrupts ; rdf:subject ?ev ; rdf:object ?f20 ; bridge:magnitude ?mag .
  ?ev bridge:disrupts ?f20 .
  ?f20 a gvc:TradeFlow ; core:startYear "2020"^^xsd:gYear ; gvc:tradeValueUSD ?v2020 ;
       gvc:flowProduct ?p .
  ?p core:hsCode ?hs .
  ?f18 a gvc:TradeFlow ; core:startYear "2018"^^xsd:gYear ; gvc:tradeValueUSD ?v2018 ;
       gvc:flowProduct ?p ; gvc:flowOrigin ?o .
  ?f20 gvc:flowOrigin ?o .
} ORDER BY ?hs"""
rows2 = []
for r in g.query(q2):
    v18, v20, mag = float(r.v2018), float(r.v2020), float(r.mag)
    rows2.append({"event": str(r.ev), "hsCode": str(r.hs), "magnitude_stored": mag,
                  "value_2018_usd": v18, "value_2020_usd": v20,
                  "change_recomputed": round((v20 - v18) / v18, 4),
                  "consistent": abs(mag - round((v20 - v18) / v18, 4)) < 1e-9})
results["queries"]["CQ2_disrupts"] = {"sparql": "Event -disrupts(reified magnitude)-> TradeFlow, compared against 2018",
                                      "rows": rows2, "n": len(rows2), "expected_n": 3,
                                      "pass": len(rows2) == 3 and all(x["consistent"] for x in rows2)}

# CQ7: 국가 N의 품목 수입 집중도, SPARQL 집계로 HHI 직접 산출
q7 = PREF + """
SELECT ?hs ?yr (SUM((?ms/100)*(?ms/100)) AS ?hhi_sparql) (COUNT(?f) AS ?n_origins) WHERE {
  ?f a gvc:TradeFlow ; gvc:flowDestination ?kor ; gvc:flowProduct ?p ;
     core:startYear ?yr ; gvc:marketShare ?ms .
  ?kor core:isoAlpha3 "KOR" .
  ?p core:hsCode ?hs .
  FILTER(?hs IN ("8541","8542"))
} GROUP BY ?hs ?yr ORDER BY ?hs ?yr"""
q7s = PREF + """
SELECT ?hs ?yr ?hhi_stored WHERE {
  ?dep a gvc:Dependency ; gvc:hhi ?hhi_stored ; gvc:dependsOnProduct ?p ; core:startYear ?yr .
  ?p core:hsCode ?hs .
} ORDER BY ?hs ?yr"""
stored = {(str(r.hs), str(r.yr)): float(r.hhi_stored) for r in g.query(q7s)}
rows7 = []
for r in g.query(q7):
    key = (str(r.hs), str(r.yr))
    hs_ = float(r.hhi_sparql)
    st_ = stored.get(key)
    rows7.append({"hsCode": key[0], "year": key[1], "n_origins_in_kg": int(r.n_origins),
                  "hhi_sparql": round(hs_, 4), "hhi_stored_fullraw": st_,
                  "delta": round(abs(hs_ - st_), 4) if st_ is not None else None,
                  "match_at_2dp": (st_ is not None and round(hs_, 2) == round(st_, 2))})
results["queries"]["CQ7_hhi"] = {
    "sparql": "SUM((marketShare/100)^2) GROUP BY product, year; HHI aggregated directly from the graph",
    "note": "hhi_stored_fullraw counts every origin in the source, including aggregate regions; the SPARQL aggregate counts only ISO-resolved origins, so the fourth-decimal difference is the excluded aggregates.",
    "rows": rows7, "n": len(rows7), "expected_n": 4,
    "pass": len(rows7) == 4 and all(x["match_at_2dp"] for x in rows7)}

# CQ8: 국가 N에 본사를 둔 제재 대상 엔티티는 (기탁 KG: 제재 카탈로그)
# 제재일·프로그램은 파일럿 미실체화 → 본사국 + 제재 유형 차원만 시연(정직 범위)
g_dep = Graph().parse(str(OUT / "pilot_kg_deposit.ttl"), format="turtle")
q8 = PREF + """
SELECT ?hqc (COUNT(DISTINCT ?e) AS ?n) WHERE {
  ?e a intl:SanctionedEntity ; intl:headquarteredIn ?hq .
  ?hq core:canonicalId ?hqc .
} GROUP BY ?hqc ORDER BY DESC(?n)"""
rows8 = [{"hq_country": str(r.hqc), "n_sanctioned_entities": int(r.n)} for r in g_dep.query(q8)]
n8_total = sum(x["n_sanctioned_entities"] for x in rows8)
results["queries"]["CQ8_sanctioned_by_hq_country"] = {
    "graph": "pilot_kg_deposit.ttl",
    "sparql": "SanctionedEntity -headquarteredIn-> Country(isoAlpha3), aggregated by country of headquarters",
    "note": "Covers only sanctioned entities whose headquarters resolve. The designation date and programme dimensions are not yet materialised and remain a stated limitation.",
    "rows": rows8, "n": len(rows8), "entities_with_hq": n8_total,
    "pass": len(rows8) > 0}

# CQ1: 어느 조직이 어떤 제재 수단(프로그램)으로 지정되었는가 (기탁 KG)
# programs 필드 실체화(Sanction -listsEntity-> Entity)로 응답. 제재일은 데이터 부재로 미포함(한계).
q1 = PREF + """
SELECT ?prog (COUNT(DISTINCT ?e) AS ?n) WHERE {
  ?s a intl:Sanction ; rdfs:label ?prog ; intl:listsEntity ?e .
  ?e a intl:SanctionedEntity .
} GROUP BY ?prog ORDER BY DESC(?n)"""
rows1 = [{"program": str(r.prog).replace("OFAC program ", ""), "n_entities": int(r.n)} for r in g_dep.query(q1)]
results["queries"]["CQ1_sanction_program"] = {
    "graph": "pilot_kg_deposit.ttl",
    "sparql": "Sanction -listsEntity-> SanctionedEntity, aggregated by programme",
    "note": "Answered by materialising the already collected programme field as Sanction nodes. The designation date is absent from the source and is therefore not included.",
    "rows": rows1, "n": len(rows1),
    "pass": len(rows1) > 0}

# CQ3(소유 순회): 기업이 소유 사슬로 제재 엔티티에 노출되는가 (GLEIF Level-2 실체화)
# 소유 순회는 실데이터로 응답되나, 제재 노드와의 교차 사례가 없어 부분 응답(한계 유지)
# LEI 병합 노드는 라벨이 2개라 GROUP BY ?plabel 이 같은 노드를 이중 집계한다.
# 노드 기준으로 집계하고 대표 라벨을 뽑는다.
q9 = PREF + """
SELECT ?p (SAMPLE(?plabel) AS ?label) (COUNT(DISTINCT ?c) AS ?n) WHERE {
  ?p intl:owns ?c ; rdfs:label ?plabel .
  ?c a core:Organization .
} GROUP BY ?p ORDER BY DESC(?n)"""
rows9 = [{"parent": str(r.label), "n_subsidiaries": int(r.n)} for r in g_dep.query(q9)]
n9_edges = sum(x["n_subsidiaries"] for x in rows9)
results["queries"]["CQ3_ownership_traversal"] = {
    "graph": "pilot_kg_deposit.ttl",
    "sparql": "Organization -owns-> Organization (subsidiary), aggregated by parent",
    "note": "Materialised from GLEIF Level-2 (CC0): the ownership network of five semiconductor firms. The traversal answers, but no ownership chain reaches a sanctioned node, so exposure and circumvention are not demonstrated. Partial answer.",
    "rows": rows9, "n": len(rows9), "ownership_edges": n9_edges,
    "pass": len(rows9) > 0}

ok = all(v["pass"] for v in results["queries"].values())
results["all_pass"] = ok
(OUT / "cq_query_results.json").write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps({k: {"n": v["n"], "pass": v["pass"]} for k, v in results["queries"].items()},
                 ensure_ascii=False, indent=1))
print("CQ7 detail:", json.dumps(results["queries"]["CQ7_hhi"]["rows"], ensure_ascii=False))
print("ALL_PASS:", ok)
raise SystemExit(0 if ok else 1)
