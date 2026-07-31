# -*- coding: utf-8 -*-
"""어휘 -> 역량질문(CQ)/설계요건(REQ) 추적 행렬 + 고아 감사 (2026-07-08).

목적: 온톨로지의 모든 명명 어휘(클래스·속성)가 16개 CQ 또는 명시적 설계요건으로
추적됨을 검증. CQ 미대응(고아) 항목을 식별해 정당화 또는 v0.2.0 이월 판정.
LOT/Gruninger-Fox 원칙: 어휘는 CQ가 요구하는 만큼만, 그 이상은 정당화 필요.

매핑 근거: 설계 단계에서 확정한 역량질문의 응답 어휘 + 설계요건.
REQ 범주: UPPER(상위 골격) / PROV(출처·계보) / FAIR(정준식별자) / SDIN(SD 접합 입력) /
          SCOPE(도메인 개입수단 완전성) / REIF(관계 사물화).
판정: CQ=직접 대응 / REQ=요건 대응 / ORPHAN=CQ·REQ 모두 약함(이월·가지치기 후보).
"""
from __future__ import annotations

# 콘솔 인코딩 방어. 윈도 기본 콘솔(cp949 등)에서는 비ASCII 문자를 출력할 때
# UnicodeEncodeError 로 죽는다. 표준 출력만 UTF-8 로 재설정한다.
import sys as _sys
if hasattr(_sys.stdout, "reconfigure"):
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from rdflib import Graph, RDF, RDFS, OWL

# term -> (분류, 근거) ; 근거는 CQ 목록 또는 REQ:범주
M = {
    # ---- core classes (13) ----
    "core:Entity": ("REQ", "UPPER (identifier-bearing top class; dual typing for CQ6)"),
    "core:Country": ("CQ", "CQ7,CQ8"),
    "core:Organization": ("CQ", "CQ3,CQ8"),
    "core:Product": ("CQ", "CQ4,CQ7,CQ11"),
    "core:Material": ("CQ", "CQ11 (semiconductor materials: hydrogen fluoride, photoresist, fluorinated polyimide)"),
    "core:Component": ("REQ", "SCOPE (value chain tier: material, component, equipment)"),
    "core:Equipment": ("REQ", "SCOPE (value chain tier)"),
    "core:Event": ("CQ", "CQ2, CQ12, CQ16 (superclass)"),
    "core:Policy": ("CQ", "CQ1, CQ4, CQ14 (superclass)"),
    "core:Location": ("CQ", "CQ5 (spatial nodes and chokepoints)"),
    "core:Identifier": ("REQ", "FAIR (canonical identifier as a value object)"),
    "core:SourceCoverage": ("CQ", "CQ15 (observed absence)"),
    "core:TemporalScope": ("CQ", "CQ14 (period of validity)"),
    # ---- intl classes (10) ----
    "intl:Sanction": ("CQ", "CQ1,CQ15"),
    "intl:SanctionedEntity": ("CQ", "CQ1,CQ3,CQ6,CQ8"),
    "intl:ExportControl": ("CQ", "CQ4,CQ15"),
    "intl:FinancialSanction": ("CQ", "CQ1 (subtype of sanction)"),
    "intl:GeopoliticalEvent": ("CQ", "CQ2,CQ12,CQ16"),
    "intl:OwnershipPath": ("CQ", "CQ3"),
    "intl:TradeMeasure": ("REQ", "SCOPE (umbrella class for trade policy instruments)"),
    "intl:TechTransferBan": ("REQ", "SCOPE (completeness of policy instruments, EUV controls and the like; no CQ maps to it directly)"),
    "intl:InvestmentRestriction": ("REQ", "SCOPE (completeness of policy instruments, investment screening; no CQ maps to it directly)"),
    # intl:Agreement / signs 는 v0.2.0 으로 이월(2026-07-08 제거)
    # ---- gvc classes (8) ----
    "gvc:Company": ("CQ", "CQ7,CQ9,CQ10,CQ11"),
    "gvc:TradeFlow": ("CQ", "CQ2, CQ7 (reified node)"),
    "gvc:Dependency": ("CQ", "CQ5,CQ9,CQ16"),
    "gvc:RiskNode": ("CQ", "CQ5,CQ16"),
    "gvc:SupplyEdge": ("REQ", "Reification (supply relation as an individual; CQ4, CQ11)"),
    "gvc:Input": ("CQ", "CQ9, CQ11 (process input)"),
    # gvc:Tool 은 core:Equipment 로 통합(2026-07-08 제거)
    "gvc:PriceIndex": ("CQ", "CQ17 (price shock; simulation input)"),
    # ---- core object props (3) ----
    "core:associatedWith": ("CQ", "CQ2 (event to policy association)"),
    "core:declaresCoverage": ("CQ", "CQ15"),
    "core:hasTemporalScope": ("CQ", "CQ14"),
    # ---- intl object props (19) ----
    "intl:owns": ("CQ", "CQ3"),
    "intl:ownedBy": ("CQ", "CQ3"),
    "intl:subsidiaryOf": ("CQ", "CQ3"),
    "intl:acquired": ("CQ", "CQ3 (ownership chain through acquisition)"),
    "intl:pathStart": ("CQ", "CQ3"),
    "intl:pathEnd": ("CQ", "CQ3"),
    "intl:listsEntity": ("CQ", "CQ1,CQ8,CQ15"),
    "intl:financiallySanctions": ("CQ", "CQ1"),
    "intl:exportControlledBy": ("CQ", "CQ4"),
    "intl:headquarteredIn": ("CQ", "CQ8"),
    "intl:hasProductionFacility": ("CQ", "CQ5,CQ8 spatial"),
    "intl:imposes": ("REQ", "PROV (imposing authority; lineage for CQ1 and CQ4)"),
    "intl:enactedBy": ("REQ", "PROV (enacting authority)"),
    "intl:incorporatedIn": ("REQ", "CQ3, CQ8 (jurisdiction of incorporation; weak CQ link)"),
    "intl:bansTechTransferTo": ("REQ", "SCOPE (entailed by TechTransferBan; no CQ maps to it directly)"),
    "intl:restrictsInvestmentIn": ("REQ", "SCOPE (entailed by InvestmentRestriction; no CQ maps to it directly)"),
    "intl:jointVentureWith": ("REQ", "Circumvention vector: non-ownership corporate tie, a route for CQ3 and CQ13"),
    "intl:strategicAllianceWith": ("REQ", "Circumvention vector: non-ownership corporate tie, a route for CQ3 and CQ13"),
    # ---- gvc object props (17) ----
    "gvc:supplies": ("CQ", "CQ4, CQ10 (base supply relation)"),
    "gvc:directlySupplies": ("CQ", "CQ4, CQ11 (supply tier)"),
    "gvc:indirectlySupplies": ("CQ", "CQ4 (indirect supply tier)"),
    "gvc:oemSupplies": ("CQ", "CQ4, CQ11 (original equipment manufacturing tier)"),
    "gvc:reroutedSupplies": ("CQ", "CQ13, CQ16 (circumvention)"),
    "gvc:supplier": ("REQ", "Reification (borne by SupplyEdge; CQ4, CQ11)"),
    "gvc:customer": ("CQ", "CQ10 (downstream customer network)"),
    "gvc:suppliesProduct": ("CQ", "CQ4,CQ11 (REIF)"),
    "gvc:producesProduct": ("CQ", "CQ11"),
    "gvc:providesInput": ("CQ", "CQ9,CQ11"),
    "gvc:dependsOnSupplier": ("CQ", "CQ9"),
    "gvc:dependsOnProduct": ("CQ", "CQ9,CQ11"),
    "gvc:dependentActor": ("CQ", "CQ5,CQ9"),
    "gvc:flowOrigin": ("CQ", "CQ7"),
    "gvc:flowDestination": ("CQ", "CQ7"),
    "gvc:flowProduct": ("CQ", "CQ2,CQ7"),
    "gvc:priceOf": ("CQ", "CQ17 (price shock)"),
    # ---- bridge object props (6) ----
    "bridge:disrupts": ("CQ", "CQ2,CQ12,CQ16"),
    "bridge:restricts": ("CQ", "CQ4,CQ15"),
    "bridge:circumvents": ("CQ", "CQ3"),
    "bridge:exposes": ("CQ", "CQ5,CQ16"),
    "bridge:affects": ("CQ", "CQ10,CQ12"),
    "bridge:bridgeRelation": ("REQ", "UPPER (abstract superproperty of the bridge relations)"),
    # ---- core data props (20) ----
    "core:canonicalId": ("REQ", "FAIR (indirect support of every CQ)"),
    "core:label": ("REQ", "FAIR (label)"),
    "core:lei": ("CQ", "CQ6"),
    "core:wikidataQID": ("REQ", "FAIR (canonical identifier)"),
    "core:isoAlpha3": ("CQ", "CQ7,CQ8"),
    "core:hsCode": ("CQ", "CQ4,CQ7,CQ11"),
    "core:eccn": ("CQ", "CQ4 (export control classification number)"),
    "core:source": ("REQ", "PROV"),
    "core:tier": ("REQ", "PROV (four-tier officiality grading)"),
    "core:collectedDate": ("REQ", "PROV"),
    "core:confidence": ("REQ", "PROV (quality)"),
    # OntoClean 분석(2026-08-02) 결과 신설 어휘.
    "intl:SanctionListing": ("CQ", "CQ1, CQ14 (listing as a fact: delisting, period and multiple registers)"),
    "intl:listedOrganization": ("CQ", "CQ1 (denotes the listed organisation)"),
    "intl:underSanction": ("CQ", "CQ1, CQ14 (measure underlying the listing)"),
    "intl:listAuthority": ("CQ", "CQ1 (issuing authority or register jurisdiction)"),
    "intl:OwnershipAssertion": ("CQ", "CQ3 (attributes the share to the owning pair)"),
    "intl:owner": ("CQ", "CQ3 (start of the ownership relation)"),
    "intl:ownedOrganization": ("CQ", "CQ3 (end of the ownership relation)"),
    "core:alternateId": ("REQ", "Preserves the pre-merge source key for traceability; not used to decide identity"),
    "core:identifierStatus": ("REQ", "Warrant of the identity criterion (standard register versus provisional key)"),
    "core:evidenceType": ("REQ", "PROV (observed versus documented evidence)"),
    "core:coverageStart": ("CQ", "CQ15"),
    "core:coverageEnd": ("CQ", "CQ15"),
    "core:observedCount": ("CQ", "CQ15"),
    "core:validFrom": ("CQ", "CQ14"),
    "core:validTo": ("CQ", "CQ14"),
    "core:startYear": ("CQ", "CQ14 (TemporalScope)"),
    "core:endYear": ("CQ", "CQ14"),
    # ---- intl data props (4) ----
    "intl:sanctionDate": ("CQ", "CQ1,CQ14,CQ15"),
    "intl:eventDate": ("CQ", "CQ2,CQ12"),
    "intl:ownershipPct": ("CQ", "CQ3"),
    "intl:controlScope": ("CQ", "CQ4"),
    # ---- gvc data props (6) ----
    "gvc:hhi": ("CQ", "CQ7"),
    "gvc:marketShare": ("CQ", "CQ11"),
    "gvc:tradeValueUSD": ("CQ", "CQ2,CQ7"),
    "gvc:tradeQuantity": ("CQ", "CQ2,CQ7"),
    "gvc:disclosureResolution": ("REQ", "PROV (warrant of entity resolution)"),
    "gvc:indexValue": ("CQ", "CQ17 (price shock)"),
    # ---- bridge data props (8) ----
    "bridge:magnitude": ("CQ", "CQ2,CQ16"),
    "bridge:lag": ("CQ", "CQ2,CQ16"),
    "bridge:hops": ("CQ", "CQ3"),
    "bridge:geoRisk": ("CQ", "CQ5"),
    "bridge:riskScore": ("CQ", "CQ5,CQ16"),
    "bridge:scope": ("CQ", "CQ4"),
    "bridge:suspicion": ("CQ", "CQ13"),
}

# 스크립트 위치 기준 상대 경로. 작업 디렉터리에 의존하면 다른 폴더에서
# 실행할 때 경로가 이중화된다.
from pathlib import Path as _Path
g = Graph(); g.parse(str(_Path(__file__).resolve().parent / "ontology.ttl"), format="turtle")
ns = {p: str(n) for p, n in g.namespaces()}
def modof(u):
    s = str(u)
    for p in ("core", "intl", "gvc", "bridge"):
        if p in ns and s.startswith(ns[p]):
            return p
    return None
def loc(u): return str(u).split("#")[-1]

# 온톨로지 실제 어휘 수집
actual = set()
for s in g.subjects(RDF.type, OWL.Class):
    m = modof(s);  actual.add(f"{m}:{loc(s)}") if m else None
for s in g.subjects(RDF.type, OWL.ObjectProperty):
    m = modof(s);  actual.add(f"{m}:{loc(s)}") if m else None
for s in g.subjects(RDF.type, OWL.DatatypeProperty):
    m = modof(s);  actual.add(f"{m}:{loc(s)}") if m else None

mapped = set(M)
missing = actual - mapped           # 매핑표에 빠진 실제 어휘(감사 누락)
stale   = mapped - actual           # 매핑표에만 있는 유령(온톨로지에 없음)

from collections import Counter
c = Counter(v[0] for k, v in M.items() if k in actual)
print(f"실제 어휘 {len(actual)} / 매핑 {len(mapped)} / 누락 {len(missing)} / 유령 {len(stale)}")
print("분류 분포:", dict(c))
if missing: print("!! 감사 누락:", sorted(missing))
if stale:   print("!! 유령 매핑:", sorted(stale))
print("\n=== ORPHAN (CQ·직접REQ 약함 → 정당화/이월 판정 대상) ===")
for k, (cat, why) in M.items():
    if cat == "ORPHAN" and k in actual:
        print(f"  {k:32} {why}")
