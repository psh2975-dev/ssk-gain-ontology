# -*- coding: utf-8 -*-
"""파일럿 카탈로그 RDF 실체화 + 실 인스턴스 SHACL 검증 (2026-07-09).

curated JSON 카탈로그(시연 2종 + 개방 기탁본)를 온톨로지 준거 RDF로 변환하고,
실 인스턴스에 대해 SHACL을 실행한다(합성 표본 검증 validate.py와 구별).

원산 해소: Comtrade M49 → ISO 3166-1 alpha-3 (pycountry + Comtrade 관용코드).
미해소 집계지역(nes 등)은 국가로 사칭하지 않고 제외하며 제외 수를 보고한다.
엣지 속성(magnitude·lag·scope)은 표준 RDF reification으로 부착한다.

산출: out/pilot_kg_demo.ttl, out/pilot_kg_deposit.ttl,
      out/shacl_demo.txt, out/shacl_deposit.txt, out/materialize_report.json
실행: .venv python (pyshacl·rdflib·pycountry)
"""
from __future__ import annotations

# 콘솔 인코딩 방어. 윈도 기본 콘솔(cp949 등)에서는 비ASCII 문자를 출력할 때
# UnicodeEncodeError 로 죽는다. 표준 출력만 UTF-8 로 재설정한다.
import sys as _sys
if hasattr(_sys.stdout, "reconfigure"):
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import json, re, sys
from pathlib import Path
from urllib.parse import quote
from rdflib import Graph, Namespace, URIRef, Literal, RDF, RDFS, XSD
import pycountry
from pyshacl import validate as shacl_validate

ROOT = Path(__file__).resolve().parents[1]          # system/
DATA = ROOT / "data" / "curated"
ONT = ROOT / "ontology"
OUT = Path(__file__).resolve().parent / "out"
OUT.mkdir(exist_ok=True)

NS = {p: Namespace(f"https://w3id.org/ssk-gain/ontology/{p}#") for p in ("core", "intl", "gvc", "bridge")}
KG = Namespace("https://w3id.org/ssk-gain/kg/")

# 릴리스 날짜는 고정한다. 실행일을 쓰면 산출물이 날마다 달라진다.
RELEASE_DATE = "2026-08-01"

# 등재 발령 기관. 조직 노드로 두어야 listAuthority 의 치역 제약을 만족한다.
AUTHORITY_OFAC = URIRef("https://w3id.org/ssk-gain/kg/agent%3Aofac")
CORE, INTL, GVC, BR = NS["core"], NS["intl"], NS["gvc"], NS["bridge"]

# Comtrade 관용 파트너코드 → ISO3 (표준 M49와 다르거나 ISO 비대응 집계인 것)
QUIRKS = {842: "USA", 490: "TWN", 251: "FRA", 381: "ITA", 699: "IND",
          757: "CHE", 579: "NOR", 58: "BEL", 736: "SDN"}
SKIP_AGG = {0, 899, 837, 838, 839, 568, 473, 577, 636, 290, 837}   # nes·벙커·자유지대 등 집계

def m49_to_iso3(code: int) -> str | None:
    if code in SKIP_AGG:
        return None
    if code in QUIRKS:
        return QUIRKS[code]
    c = pycountry.countries.get(numeric=f"{code:03d}")
    return c.alpha_3 if c else None

def term(pref_local: str) -> URIRef:
    p, l = pref_local.split(":", 1)
    return NS[p][l]

def nuri(node_id: str) -> URIRef:
    return KG[quote(str(node_id), safe="")]

LEI_RE = re.compile(r"^[A-Z0-9]{18}[0-9]{2}$")
ISO3_RE = re.compile(r"^[A-Z]{3}$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}")

# JSON 필드 → (온톨로지 술어, 변환)
def lit_date(v): return Literal(str(v)[:10], datatype=XSD.date)
FIELDS = {
    "canonicalId": (CORE.canonicalId, lambda v: Literal(str(v))),
    "label":       (CORE.label,       lambda v: Literal(str(v))),
    "hsCode":      (CORE.hsCode,      lambda v: Literal(str(v))),
    "eccn":        (CORE.eccn,        lambda v: Literal(str(v))),
    "source":      (CORE.source,      lambda v: Literal(str(v))),
    "tier":        (CORE.tier,        lambda v: Literal(str(v))),
    "evidenceType":(CORE.evidenceType,lambda v: Literal(str(v))),
    "confidence":  (CORE.confidence,  lambda v: Literal(f"{float(v)}", datatype=XSD.decimal)),
    "tradeValueUSD":(GVC.tradeValueUSD,lambda v: Literal(f"{float(v)}", datatype=XSD.decimal)),
    "hhi":         (GVC.hhi,          lambda v: Literal(f"{float(v)}", datatype=XSD.decimal)),
    "controlScope":(INTL.controlScope,lambda v: Literal(str(v))),
    "eventDate":   (INTL.eventDate,   lit_date),
    "sanctionDate":(INTL.sanctionDate,lit_date),
    "validFrom":   (CORE.validFrom,   lit_date),
    "collectedDate":(CORE.collectedDate,lit_date),
    "year":        (CORE.startYear,   lambda v: Literal(str(v), datatype=XSD.gYear)),
    # 원산 점유율(전체 수입 대비 %), 수입시장 점유로서 marketShare 로 표현
    "importShare": (GVC.marketShare,  lambda v: Literal(f"{float(v)*100:.4f}", datatype=XSD.decimal)),
}
EDGE_ATTRS = {"magnitude": (BR.magnitude, XSD.decimal), "lag": (BR.lag, XSD.integer),
              "scope": (BR.scope, XSD.string), "hops": (BR.hops, XSD.integer),
              "suspicion": (BR.suspicion, XSD.decimal), "riskScore": (BR.riskScore, XSD.decimal)}

def build_graph(files: list[Path], report: dict) -> Graph:
    g = Graph()
    for p, ns in NS.items():
        g.bind(p, ns)
    g.bind("kg", KG)
    skipped_countries, skipped_flows, skipped_edges = set(), 0, 0
    dropped_fields = []
    n_listings = 0
    for f in files:
        d = json.loads(f.read_text(encoding="utf-8"))
        nodes = {n["_node_id"]: n for n in d.get("nodes", [])}
        # 1) 국가 ISO 해소 (미해소 국가노드와 그 무역흐름은 제외, 사칭 금지)
        resolved = {}
        for nid, n in nodes.items():
            if "core:Country" not in (n.get("ontology_classes") or []):
                continue
            iso = str(n.get("isoAlpha3") or "")
            if not ISO3_RE.match(iso):
                m = re.match(r"^M49-(\d+)$", iso)
                iso3 = m49_to_iso3(int(m.group(1))) if m else None
                if iso3 is None and re.match(r"^[A-Z]{2}$", iso):      # ISO2 → ISO3
                    c = pycountry.countries.get(alpha_2=iso)
                    iso3 = c.alpha_3 if c else None
                if iso3 is None:                                        # 노드 id 접미(country:XX)
                    m2 = re.match(r"^country:([A-Z]{2})$", str(nid))
                    if m2:
                        c = pycountry.countries.get(alpha_2=m2.group(1))
                        iso3 = c.alpha_3 if c else None
                if iso3 is None:
                    resolved[nid] = None
                    skipped_countries.add(nid)
                    continue
                n["isoAlpha3"] = iso3
                iso = iso3
            # 정준 식별자는 해소된 alpha-3 로 통일한다. 원자료 코드(M49-100,
            # alpha-2)를 두면 같은 국가가 소스마다 다른 정준값을 갖는다.
            n["canonicalId"] = iso
            resolved[nid] = iso
        # 2) 제외 대상 결정: 미해소 국가 + 그를 원산/도착으로 하는 흐름
        bad_nodes = {nid for nid, iso in resolved.items() if iso is None}
        edges = d.get("edges", [])
        for e in edges:
            if e.get("predicate") in ("gvc:flowOrigin", "gvc:flowDestination") and e.get("object") in bad_nodes:
                bad_nodes.add(e.get("subject"))
        # 3) 노드 방출
        for nid, n in nodes.items():
            if nid in bad_nodes:
                skipped_flows += 1 if "gvc:TradeFlow" in (n.get("ontology_classes") or []) else 0
                continue
            u = nuri(nid)
            for cls in (n.get("ontology_classes") or []):
                g.add((u, RDF.type, term(cls)))
            if n.get("label"):
                g.add((u, RDFS.label, Literal(str(n["label"]))))
            lei = str(n.get("lei") or "")
            if LEI_RE.match(lei):
                g.add((u, CORE.lei, Literal(lei)))
            iso = str(n.get("isoAlpha3") or "")
            if ISO3_RE.match(iso):
                g.add((u, CORE.isoAlpha3, Literal(iso)))
            is_flow = "gvc:TradeFlow" in (n.get("ontology_classes") or [])
            for k, (pred, conv) in FIELDS.items():
                if is_flow and k == "hsCode":
                    continue   # hsCode 정의역=Product. 흐름의 품목은 flowProduct 간선으로만 표현
                v = n.get(k)
                if v not in (None, ""):
                    # 변환 실패를 조용히 삼키면 원자료 형식이 바뀌었을 때 트리플이
                    # 말없이 사라진다. 예외 유형을 좁히고 누락을 보고서에 남긴다.
                    try:
                        g.add((u, pred, conv(v)))
                    except (ValueError, TypeError, ArithmeticError) as e:
                        dropped_fields.append(
                            {"node": nid, "field": k, "value": str(v)[:60],
                             "error": type(e).__name__})
        # 3b) 제재 프로그램 실체화: 이미 수집된 programs 필드 → Sanction 노드 + listsEntity
        #     (신규 수집 아님. OFAC 다중프로그램 브래킷 표기 "FTO] [SDGT"를 토큰 분해)
        programs_seen = {}
        for nid, n in nodes.items():
            if nid in bad_nodes:
                continue
            progs = n.get("programs")
            if not progs:
                continue
            for prog in (progs if isinstance(progs, list) else [progs]):
                for token in re.split(r"[\[\]\s]+", str(prog)):
                    token = token.strip()
                    if not token:
                        continue
                    if token not in programs_seen:
                        su = KG[f"sanction:{token}"]
                        g.add((su, RDF.type, term("intl:Sanction")))
                        g.add((su, RDFS.label, Literal(f"OFAC program {token}")))
                        # 프로그램 명칭은 개정·통합되므로 발령 기관을 접두로 붙여
                        # 정준 식별자를 부여한다.
                        g.add((su, CORE.canonicalId, Literal(f"OFAC:PROGRAM:{token}")))
                        g.add((su, CORE.source, Literal("OFAC_CSL")))
                        programs_seen[token] = su
                    g.add((programs_seen[token], term("intl:listsEntity"), nuri(nid)))
                    # 등재 사실을 개체로 분리한다. 등재는 해제 가능한 상태이므로
                    # 조직의 유형이 아니라 진술로 담아야 해제·기간·근거를 표현한다.
                    lu = KG[quote(f"listing:OFAC:{token}:{nid}", safe="")]
                    g.add((lu, RDF.type, term("intl:SanctionListing")))
                    g.add((lu, CORE.canonicalId, Literal(f"OFAC:LISTING:{token}:{nid}")))
                    g.add((lu, term("intl:listedOrganization"), nuri(nid)))
                    g.add((lu, term("intl:underSanction"), programs_seen[token]))
                    g.add((lu, term("intl:listAuthority"), AUTHORITY_OFAC))
                    g.add((lu, CORE.source, Literal("OFAC_CSL")))
                    if n.get("collectedDate"):
                        g.add((lu, CORE.collectedDate, lit_date(n["collectedDate"])))
                    n_listings += 1
        # 4) 엣지 방출 (+속성은 표준 reification)
        for e in edges:
            s, o = e.get("subject"), e.get("object")
            if s in bad_nodes or o in bad_nodes or s not in nodes or o not in nodes:
                skipped_edges += 1
                continue
            pred = term(e["predicate"])
            g.add((nuri(s), pred, nuri(o)))
            attrs = [(k, e[k]) for k in EDGE_ATTRS if e.get(k) is not None]
            if attrs:
                st = KG[quote("stmt:" + str(e.get("_edge_id")), safe="")]
                g.add((st, RDF.type, RDF.Statement))
                g.add((st, RDF.subject, nuri(s)))
                g.add((st, RDF.predicate, pred))
                g.add((st, RDF.object, nuri(o)))
                for k, v in attrs:
                    p2, dt = EDGE_ATTRS[k]
                    g.add((st, p2, Literal(str(v), datatype=dt)))
    report["sanction_listings"] = n_listings
    report["dropped_fields"] = dropped_fields
    report["dropped_field_count"] = len(dropped_fields)
    report["skipped_unresolved_countries"] = sorted(skipped_countries)
    report["skipped_tradeflows"] = skipped_flows
    report["skipped_edges"] = skipped_edges
    return g

def add_gleif_ownership(g: Graph) -> int:
    """GLEIF Level-2 소유관계(direct-children)를 owns/subsidiaryOf 간선으로 실체화.
    자회사는 신규 Organization 노드(LEI·label·출처 태그). GLEIF=CC0."""
    files = sorted((DATA.parent / "raw" / "gleif").glob("gleif_l2_ownership_*.json"))
    if not files:
        return 0
    d = json.loads(files[-1].read_text(encoding="utf-8"))
    src, tier, cdate = d.get("source", "GLEIF_L2"), d.get("tier", "T1"), d.get("collectedDate", "")
    n = 0
    for o in d.get("ownership", []):
        parent, child = nuri(o["parent_lei"]), nuri(o["child_lei"])
        g.add((child, RDF.type, term("core:Organization")))
        g.add((child, CORE.lei, Literal(o["child_lei"])))
        g.add((child, CORE.label, Literal(o["child_name"])))
        g.add((child, CORE.source, Literal(src)))
        g.add((child, CORE.tier, Literal(tier)))
        if cdate:
            g.add((child, CORE.collectedDate, lit_date(cdate)))
        g.add((parent, term("intl:owns"), child))
        g.add((child, term("intl:subsidiaryOf"), parent))
        # 지분 소유를 관계 개체로 재화한다. 지분율·유효기간·출처는 어느 한 조직이
        # 아니라 이 쌍에 귀속된다. owns 간선은 단순 질의용 파생 관계로 남는다.
        au = KG[quote(f"ownership:{o['parent_lei']}:{o['child_lei']}", safe="")]
        g.add((au, RDF.type, term("intl:OwnershipAssertion")))
        g.add((au, CORE.canonicalId,
               Literal(f"OWN:{o['parent_lei']}:{o['child_lei']}")))
        g.add((au, term("intl:owner"), parent))
        g.add((au, term("intl:ownedOrganization"), child))
        if o.get("ownership_pct") is not None:
            g.add((au, term("intl:ownershipPct"),
                   Literal(str(o["ownership_pct"]), datatype=XSD.decimal)))
        g.add((au, CORE.source, Literal(src)))
        g.add((au, CORE.tier, Literal(tier)))
        if cdate:
            g.add((au, CORE.collectedDate, lit_date(cdate)))
        n += 1
    return n



# PROV-O 출처 계층.
# 자체 속성(source·tier·confidence·evidenceType)은 우리 등급 체계의 세부를 담고,
# PROV-O 는 표준 골격(무엇에서 파생했나·무엇이 생성했나·누구 책임인가)을 담는다.
# 둘은 대체 관계가 아니라 층위가 다르다. 표준 술어가 있어야 제3자 도구가 원자료까지
# 거슬러 올라갈 수 있다.
PROV = Namespace("http://www.w3.org/ns/prov#")

# core:source 문자열 -> (데이터셋 slug, 책임 주체 slug)
SOURCE_MAP = {
    "OFAC_CSL": ("ofac-csl", "ofac"),
    "OFAC SDN / CSL / GDELT / OpenSanctions (intl snapshot)": ("intl-snapshot", "ofac"),
    "GLEIF_LEI": ("gleif-lei", "gleif"),
    "GLEIF_L2": ("gleif-level2", "gleif"),
    "UN Comtrade": ("un-comtrade", "unsd"),
    "UN Comtrade (계산)": ("un-comtrade", "unsd"),
    "BACI (CEPII 공개 배포, HS6, 반도체 필터 2026-07-03 수집)": ("baci", "cepii"),
    "ISO3166": ("iso-3166", "iso"),
    "ISO3166/M49": ("iso-3166", "iso"),
    "WCO HS 2022": ("wco-hs", "wco"),
    "WCO HS": ("wco-hs", "wco"),
    "Wikidata": ("wikidata", "wikidata"),
    "Wikidata maritime nodes": ("wikidata", "wikidata"),
    "GDELT": ("gdelt", "gdelt"),
    "ETO Advanced Semiconductor": ("eto-semiconductor", "eto"),
    "METI/literature": ("meti-notice", "meti"),
    "literature": ("literature", "authors"),
    "expert_curation_public_sources": ("curation", "authors"),
    # SMIC 사례 파일 출처. 미등재면 그 레코드의 계보가 조용히 빠진다(보고서의
    # prov_unmapped_sources 로 드러남).
    "Federal_Register": ("federal-register", "bis"),
    "GLEIF_API": ("gleif-api", "gleif"),
}

AGENTS = {
    "ofac": "Office of Foreign Assets Control, U.S. Department of the Treasury",
    "gleif": "Global Legal Entity Identifier Foundation",
    "unsd": "United Nations Statistics Division",
    "cepii": "CEPII",
    "iso": "International Organization for Standardization",
    "wco": "World Customs Organization",
    "wikidata": "Wikidata",
    "gdelt": "The GDELT Project",
    "eto": "Emerging Technology Observatory",
    "meti": "Ministry of Economy, Trade and Industry, Japan",
    "authors": "The authors",
    "bis": "Bureau of Industry and Security, U.S. Department of Commerce",
}


def add_provenance(g: Graph, activity_slug: str, report: dict) -> dict:
    """노드의 자체 출처 표기를 PROV-O 표준 술어로 함께 표현한다."""
    g.bind("prov", PROV)
    act = KG[quote("activity:" + activity_slug, safe="")]
    g.add((act, RDF.type, PROV.Activity))
    g.add((act, RDFS.label, Literal(f"Materialisation of the {activity_slug} graph", lang="en")))
    g.add((act, CORE.collectedDate, lit_date(RELEASE_DATE)))


    # 발령 기관은 PROV 주체이자 조직이다. listAuthority 의 치역을 만족시키려면
    # core:Organization 으로도 선언해야 한다.
    g.add((AUTHORITY_OFAC, RDF.type, CORE.Organization))
    g.add((AUTHORITY_OFAC, CORE.canonicalId, Literal("AUTHORITY:OFAC")))
    g.add((AUTHORITY_OFAC, CORE.label,
           Literal("Office of Foreign Assets Control", datatype=XSD.string)))

    datasets, agents, linked = set(), set(), 0
    for s, o in list(g.subject_objects(CORE.source)):
        mapped = SOURCE_MAP.get(str(o))
        if not mapped:
            continue
        ds_slug, ag_slug = mapped
        ds = KG[quote("dataset:" + ds_slug, safe="")]
        ag = KG[quote("agent:" + ag_slug, safe="")]
        if ds_slug not in datasets:
            g.add((ds, RDF.type, PROV.Entity))
            g.add((ds, RDFS.label, Literal(str(o), lang="en")))
            g.add((ds, PROV.wasAttributedTo, ag))
            g.add((act, PROV.used, ds))
            datasets.add(ds_slug)
        if ag_slug not in agents:
            g.add((ag, RDF.type, PROV.Agent))
            g.add((ag, RDFS.label, Literal(AGENTS[ag_slug], lang="en")))
            agents.add(ag_slug)
        # 계보는 대상이 아니라 대상에 관한 레코드에 붙인다. 대상을 prov:Entity 로
        # 두면 국가와 기업이 데이터셋에서 생성된 것으로 읽힌다. core:source 는
        # 「이 목록에서 이 대상을 알게 된 출처」라는 목록 차원의 표기이므로 남긴다.
        rec = KG[quote("record:" + ds_slug + ":" + str(s).rsplit("/", 1)[-1], safe="")]
        g.add((rec, RDF.type, CORE.Record))
        g.add((rec, CORE.recordOf, s))
        g.add((rec, CORE.canonicalId,
               Literal("RECORD:" + ds_slug + ":" + str(s).rsplit("/", 1)[-1],
                       datatype=XSD.string)))
        g.add((rec, CORE.source, Literal(str(o), datatype=XSD.string)))
        g.add((rec, PROV.wasDerivedFrom, ds))
        g.add((rec, PROV.wasGeneratedBy, act))
        linked += 1

    unmapped = sorted({str(o) for _, o in g.subject_objects(CORE.source)
                       if str(o) not in SOURCE_MAP})
    report["prov_records"] = linked
    report["prov_datasets"] = len(datasets)
    report["prov_agents"] = len(agents)
    report["prov_unmapped_sources"] = unmapped
    return report


# 식별자 개체를 주조할 데이터 속성과 그 등록 체계. 값이 아니라 개체가 동일성을
# 나르므로, 같은 (체계, 값)은 반드시 같은 URI 로 가야 한다.
ID_SCHEMES = (
    (CORE.lei, "LEI"),
    (CORE.isoAlpha3, "ISO3166-1-alpha-3"),
    (CORE.hsCode, "HS"),
    (CORE.wikidataQID, "Wikidata"),
)


def reify_identifiers(g: Graph, report: dict) -> dict:
    """표준 식별자를 개체로 세우고 core:hasIdentifier 로 잇는다.

    hasIdentifier 가 역함수적이므로, 두 출처의 노드가 같은 식별자 개체를 가리키면
    OWL 2 DL 안에서 동일 개체로 추론된다. 종전에는 이 추론을 데이터 속성의
    역함수성에 기댔는데, OWL 2 에는 그런 공리가 없어 DL 밖으로 나가 있었다.
    """
    n_id = n_link = 0
    for prop, scheme in ID_SCHEMES:
        for s, o in list(g.subject_objects(prop)):
            v = str(o).strip()
            if not v:
                continue
            u = KG[quote(f"id:{scheme}:{v}", safe="")]
            if (u, RDF.type, CORE.Identifier) not in g:
                g.add((u, RDF.type, CORE.Identifier))
                g.add((u, CORE.identifierScheme, Literal(scheme, datatype=XSD.string)))
                g.add((u, CORE.identifierValue, Literal(v, datatype=XSD.string)))
                g.add((u, CORE.canonicalId, Literal(f"{scheme}:{v}", datatype=XSD.string)))
                g.add((u, CORE.label, Literal(f"{scheme} {v}", datatype=XSD.string)))
                g.add((u, CORE.identifierStatus, Literal("authoritative")))
                n_id += 1
            if (s, CORE.hasIdentifier, u) not in g:
                g.add((s, CORE.hasIdentifier, u))
                n_link += 1
    report["identifier_individuals"] = n_id
    report["identifier_links"] = n_link
    return report


def add_case_smic(g: Graph, report: dict) -> dict:
    """SMIC 종단간 사례: 등재(T1) -> LEI 동일성(실조회) -> 공급간선(공시) -> affects.

    모든 사실이 basis 에 공적 출처를 지닌다. 동일성은 파이프라인 병합이 아니라
    두 노드가 같은 식별자 개체를 가리키는 것으로 표현한다. 역함수 공리가 동일성을
    허가하고, 하네스 [1d] 가 그 추론을 증명한다.
    """
    d = json.loads((DATA / "curated_case_smic_2026-08-03.json").read_text(encoding="utf-8"))
    by_cid = {str(o): s for s, o in g.subject_objects(CORE.canonicalId)}
    by_lei = {str(o): s for s, o in g.subject_objects(CORE.lei)}
    # 제품 노드는 canonicalId 없이 hsCode 만 가진다(BACI 적재 관례).
    by_hs = {str(o): s for s, o in g.subject_objects(CORE.hsCode)}

    # 라이선스·basis 는 KG 트리플이 아니라 큐레이션 JSON 에 남긴다(players 관례).
    # 어휘에 없는 술어를 데이터에 쓰지 않는다.
    def stamp(u, e, keys=("source", "tier", "evidenceType",
                          "collectedDate", "confidence")):
        F = {"source": (CORE.source, lambda v: Literal(str(v))),
             "tier": (CORE.tier, lambda v: Literal(str(v))),
             "evidenceType": (CORE.evidenceType, lambda v: Literal(str(v))),
             "collectedDate": (CORE.collectedDate, lit_date),
             "confidence": (CORE.confidence, lambda v: Literal(f"{float(v)}", datatype=XSD.decimal))}
        for k in keys:
            if k in e and k in dict(F):
                pred, conv = F[k]
                g.add((u, pred, conv(e[k])))

    # 1) LEI 부착 + 식별자 개체(등록 상태 포함). reify 가 같은 URI 를 쓰므로 중복 없음.
    lr = d["lei_record"]
    v = lr["lei"]
    for link in d["identity_links"]:
        g.add((by_cid[link["canonicalId"]], CORE.lei, Literal(v)))
    ident = KG[quote(f"id:LEI:{v}", safe="")]
    g.add((ident, RDF.type, CORE.Identifier))
    g.add((ident, CORE.identifierScheme, Literal("LEI", datatype=XSD.string)))
    g.add((ident, CORE.identifierValue, Literal(v, datatype=XSD.string)))
    g.add((ident, CORE.canonicalId, Literal(f"LEI:{v}", datatype=XSD.string)))
    g.add((ident, CORE.label, Literal(f"LEI {v}", datatype=XSD.string)))
    g.add((ident, CORE.identifierStatus, Literal("authoritative")))
    g.add((ident, CORE.registrationStatus, Literal(lr["registration_status"])))
    stamp(ident, lr)

    # 2) 발령기관 + 수출통제 + 등재사실
    a = d["authority"]
    au = KG[quote(a["canonicalId"], safe="")]
    g.add((au, RDF.type, CORE.Organization))
    g.add((au, CORE.canonicalId, Literal(a["canonicalId"])))
    g.add((au, CORE.label, Literal(a["label"], datatype=XSD.string)))
    stamp(au, a)

    ec_d = d["export_control"]
    ec = KG[quote(ec_d["canonicalId"], safe="")]
    g.add((ec, RDF.type, INTL.ExportControl))
    g.add((ec, CORE.canonicalId, Literal(ec_d["canonicalId"])))
    g.add((ec, CORE.label, Literal(ec_d["label"], datatype=XSD.string)))
    g.add((ec, CORE.validFrom, lit_date(ec_d["validFrom"])))
    g.add((ec, INTL.controlScope, Literal(ec_d["controlScope"], datatype=XSD.string)))
    stamp(ec, ec_d)
    for hs in ec_d["restricts_hs"]:
        g.add((ec, BR.restricts, by_hs[hs]))

    li_d = d["listing"]
    li = KG[quote(li_d["canonicalId"], safe="")]
    g.add((li, RDF.type, INTL.SanctionListing))
    g.add((li, CORE.canonicalId, Literal(li_d["canonicalId"])))
    g.add((li, CORE.label, Literal(li_d["label"], datatype=XSD.string)))
    g.add((li, INTL.listedOrganization,
           by_cid[d["affects_edge"]["subject_canonicalId"]]))
    g.add((li, INTL.underSanction, ec))
    g.add((li, INTL.listAuthority, au))
    stamp(li, li_d)

    # 3) 재화 공급간선 + affects
    se_d = d["supply_edge"]
    se = KG[quote(se_d["canonicalId"], safe="")]
    supplier = by_lei[se_d["supplier_lei"]]
    customer = by_cid[se_d["customer_canonicalId"]]
    g.add((se, RDF.type, GVC.SupplyEdge))
    g.add((se, CORE.canonicalId, Literal(se_d["canonicalId"])))
    g.add((se, CORE.label, Literal(se_d["label"], datatype=XSD.string)))
    g.add((se, GVC.supplier, supplier))
    g.add((se, GVC.customer, customer))
    g.add((se, GVC.suppliesProduct, by_hs[se_d["product_hs"]]))
    # 공급 측이 병합 노드라 gvc:Company 형이 빠져 있을 수 있다. 같은 players
    # 레코드(role: equipment)가 회사임을 입증하므로 형 부여는 그 기록에 근거한다.
    g.add((supplier, RDF.type, GVC.Company))
    g.add((customer, RDF.type, GVC.Company))
    stamp(se, se_d)

    af = d["affects_edge"]
    g.add((by_cid[af["subject_canonicalId"]], BR.affects, se))

    # 등재 사실 총계는 그래프 실물과 같은 의미여야 한다. 사례 등재도 등재다.
    report["sanction_listings"] = report.get("sanction_listings", 0) + 1
    report["case_smic"] = {
        "identity_links": len(d["identity_links"]),
        "listing": 1, "export_control": 1, "supply_edge": 1, "affects": 1,
    }
    return report


def derive_exposes(g: Graph, report: dict) -> dict:
    """exposes 파생: 문서화된 수출통제가 제한하는 품목에 대한 의존관계.

    새 사실을 만들지 않는다. 관측 자료 둘(BACI 의존관계, 문서화된 통제)에
    bridge:exposes 에 선언된 규칙(집중 의존 + 지정학 위험 = 노출)을 그대로
    적용한다. 문턱을 발명하지 않는다: 의존관계 개체는 이미 집중 기준으로
    큐레이션되어 있고, 위험은 실측이 아니라 문서화된 통제의 존재다.
    """
    n = 0
    for dep in set(g.subjects(RDF.type, GVC.Dependency)):
        for prod in g.objects(dep, GVC.dependsOnProduct):
            if (None, BR.restricts, prod) in g:
                g.add((prod, RDF.type, GVC.RiskNode))
                g.add((dep, BR.exposes, prod))
                n += 1
    report["exposes_edges_derived"] = n
    return report


def tag_identifier_status(g: Graph, report: dict) -> dict:
    """정준 식별자가 표준 등록부 근거인지 잠정 큐레이션 키인지 표시한다.

    이름 기반 키는 동일성을 보장하지 못한다(표기 변동·동명이인). 값을 지우면 노드가
    끊기므로, 지우는 대신 근거를 명시해 하류 이용자가 판단할 수 있게 한다.
    """
    import re as _re
    LEI_RE = _re.compile(r"^[A-Z0-9]{18}[0-9]{2}$")
    ISO3_RE2 = _re.compile(r"^[A-Z]{3}$")
    auth = prov = 0
    for s, o in list(g.subject_objects(CORE.canonicalId)):
        if (s, RDF.type, CORE.Identifier) in g:
            continue
        v = str(o)
        standard = bool(LEI_RE.match(v) or ISO3_RE2.match(v) or v.isdigit()
                        or v.startswith(("OFAC:", "OWN:", "COVERAGE:", "AUTHORITY:",
                                         "spatial:", "EC:", "EV:", "DEP:", "GDELT:",
                                         "SE:", "LISTING:", "LEI:")))
        g.add((s, CORE.identifierStatus,
               Literal("authoritative" if standard else "provisional")))
        auth, prov = (auth + 1, prov) if standard else (auth, prov + 1)
    report["identifier_authoritative"] = auth
    report["identifier_provisional"] = prov
    return report


def add_deposit_extras(g: Graph) -> dict:
    """개방 기탁 그래프에 라이선스 적격 gvc·공간·커버리지 계층을 편입한다.

    규제 도메인과 경제 구조가 한 그래프에 함께 실려야 교차도메인 질의가
    성립한다. 큐레이션 자료 중 개방 재배포에 적격인 것만 편입한다.

      players v3   CC-BY-4.0   기업 25 + 공급간선 33
      spatial      CC0-1.0     해상 인프라 22 (Wikidata QID)
      BACI 조망    Etalab 2.0  KOR 수입의존 22품목 (CC-BY 호환)
      coverage     자체 산출    SourceCoverage 4 (관측된 부재 선언)

    Comtrade 유래 흐름(UN 저작권·재배포 불가)과 ETO(CC-BY-NC)는 기탁 제외
    유지, 스키마·재현 절차만 공개(원고 4-1절 정책).

    players 는 검증된 LEI 가 있으면 기존 노드(GLEIF 유래)와 같은 URI 로
    병합한다. DP3(정준 식별자에 의한 중복 없는 해소)의 실동작이다.
    타입은 큐레이션의 core:Organization 에 gvc:Company 를 더한다:
    이 25곳은 role 필드와 공급간선으로 공급사슬 참여가 같은 레코드 안에서
    입증되는 기업이므로, "공급사슬에 참여하는 기업"이라는 클래스 정의를
    자료가 직접 충족한다(임의 재분류 아님).
    """
    rep = {}

    # 0) LEI → 기존 노드 URI (개체 해소용)
    lei_to_uri = {str(o): s for s, o in g.subject_objects(CORE.lei)}

    # 1) players: 기업 + 공급간선
    d = json.loads((DATA / "semiconductor_players_v3.json").read_text(encoding="utf-8"))
    pid_to_uri, merged = {}, 0
    for n in d.get("nodes", []):
        lei = str(n.get("lei") or "")
        if n.get("lei_verified") and LEI_RE.match(lei) and lei in lei_to_uri:
            u = lei_to_uri[lei]
            merged += 1
        else:
            u = nuri(f"player:{n['id']}")
        pid_to_uri[n["id"]] = u
        g.add((u, RDF.type, term("core:Organization")))
        g.add((u, RDF.type, term("gvc:Company")))
        g.add((u, RDFS.label, Literal(str(n["name"]))))
        g.add((u, CORE.label, Literal(str(n["name"]))))
        # 병합된 노드는 LEI 를 정준으로 두고 소스 키는 별칭으로 남긴다. 둘 다
        # 정준으로 두면 "정준"이 성립하지 않고 식별자 근거도 둘로 갈린다.
        _is_merged = lei in lei_to_uri and lei_to_uri.get(lei) is u
        g.add((u, CORE.alternateId if _is_merged else CORE.canonicalId,
               Literal(f"player:{n['id']}")))
        if LEI_RE.match(lei) and n.get("lei_verified"):
            g.add((u, CORE.lei, Literal(lei)))
            lei_to_uri[lei] = u
        for k in ("source", "evidenceType"):
            if n.get(k):
                g.add((u, FIELDS[k][0], Literal(str(n[k]))))
        if n.get("confidence") is not None:
            g.add((u, CORE.confidence, Literal(f"{float(n['confidence'])}", datatype=XSD.decimal)))
        if n.get("collectedDate"):
            g.add((u, CORE.collectedDate, lit_date(n["collectedDate"])))
    # 간선 끝점은 source_node 필드를 쓴다. source 는 출처 태깅이 덮어써
    # provenance 문자열이 되어 있다(repair_players_edges.py 참조).
    n_pedges = 0
    for e in d.get("edges", []):
        s, t = pid_to_uri.get(e.get("source_node")), pid_to_uri.get(e.get("target"))
        if s is None or t is None:
            continue
        g.add((s, term(e["predicate"]), t))
        n_pedges += 1
    rep["players_nodes"] = len(pid_to_uri)
    rep["players_edges"] = n_pedges
    rep["players_lei_merged"] = merged

    # 2) spatial: 해상 인프라 (Wikidata QID)
    d = json.loads((DATA / "curated_spatial_nodes_2026-07-03.json").read_text(encoding="utf-8"))
    n_sp = 0
    for n in d.get("nodes", []):
        u = nuri(n["node_id"])
        g.add((u, RDF.type, term("core:Location")))
        g.add((u, RDFS.label, Literal(str(n.get("matched_label") or n["node_id"]))))
        g.add((u, CORE.canonicalId, Literal(str(n["node_id"]))))
        g.add((u, CORE.wikidataQID, Literal(str(n["wikidata_qid"]))))
        for k in ("source", "tier", "evidenceType"):
            if n.get(k):
                g.add((u, FIELDS[k][0], Literal(str(n[k]))))
        if n.get("collectedDate"):
            g.add((u, CORE.collectedDate, lit_date(n["collectedDate"])))
        n_sp += 1
    rep["spatial_nodes"] = n_sp
    # 좌표(lat·lon)는 온톨로지에 어휘가 없어 원자료 JSON 에만 보존(어휘 확장은
    # v0.2.0 백로그 사안, 공표 어휘 수 29/44/36 을 조용히 바꾸지 않는다).

    # 3) BACI 조망: KOR 수입의존 22품목 → Dependency (+ Product·Country)
    d = json.loads((DATA / "structural_landscape_baci2018.json").read_text(encoding="utf-8"))
    kor = nuri("country:KOR")
    if (kor, RDF.type, term("core:Country")) not in g:
        g.add((kor, RDF.type, term("core:Country")))
        g.add((kor, CORE.isoAlpha3, Literal("KOR")))
        g.add((kor, RDFS.label, Literal("Korea, Republic of")))
    n_dep = 0
    for r in d.get("landscape_2018", []):
        hs = str(r["hs"])
        prod = nuri(f"HS:{hs}")
        g.add((prod, RDF.type, term("core:Product")))
        g.add((prod, CORE.hsCode, Literal(hs)))
        dep = nuri(f"DEP:KOR:{hs}:2018")
        g.add((dep, RDF.type, term("gvc:Dependency")))
        g.add((dep, RDFS.label, Literal(f"KOR import dependency HS {hs} (BACI 2018)")))
        g.add((dep, CORE.canonicalId, Literal(f"DEP:KOR:{hs}:2018")))
        g.add((dep, GVC.hhi, Literal(f"{float(r['hhi'])}", datatype=XSD.decimal)))
        g.add((dep, CORE.startYear, Literal("2018", datatype=XSD.gYear)))
        g.add((dep, CORE.source, Literal(str(d.get("source") or "BACI (CEPII)"))))
        g.add((dep, CORE.tier, Literal("T1")))
        g.add((dep, CORE.evidenceType, Literal("observed")))
        g.add((dep, GVC.dependentActor, kor))
        g.add((dep, GVC.dependsOnProduct, prod))
        n_dep += 1
    rep["baci_dependencies"] = n_dep

    # 3b) 2019 일본 수출통제의 정책 사실 계층 (bridge:restricts 기탁 실증)
    #
    # 일본 2019 사례 파일에서 라이선스 적격(public_domain) 부분만 편입한다:
    # METI 고시가 근거인 통제·이벤트·품목 노드와 restricts·associatedWith 간선.
    # Comtrade 유래(TradeFlow·disrupts·flow*)는 재배포 불가라 기탁 제외 유지,
    # 그 부분은 demo 그래프와 재생성 스크립트로 공개된다.
    # 이로써 기탁 그래프에 bridge 관계 1종(restricts)이 실데이터로 실린다.
    d = json.loads((DATA / "worked_example_japan2019_2026-07-07.json").read_text(encoding="utf-8"))
    ok_nodes = {n["_node_id"]: n for n in d.get("nodes", [])
                if n.get("license") == "public_domain"}
    for nid, n in ok_nodes.items():
        u = nuri(nid)
        for cls in (n.get("ontology_classes") or []):
            g.add((u, RDF.type, term(cls)))
        if n.get("label"):
            g.add((u, RDFS.label, Literal(str(n["label"]))))
        for k, (pred, conv) in FIELDS.items():
            v = n.get(k)
            if v not in (None, ""):
                try:
                    g.add((u, pred, conv(v)))
                except Exception:
                    pass
    n_restricts = 0
    for e in d.get("edges", []):
        if e.get("predicate") not in ("bridge:restricts", "core:associatedWith"):
            continue
        s, o = e.get("subject"), e.get("object")
        if s not in ok_nodes or o not in ok_nodes:
            continue
        pred = term(e["predicate"])
        g.add((nuri(s), pred, nuri(o)))
        attrs = [(k, e[k]) for k in EDGE_ATTRS if e.get(k) is not None]
        if attrs:
            st = KG[quote("stmt:" + str(e.get("_edge_id")), safe="")]
            g.add((st, RDF.type, RDF.Statement))
            g.add((st, RDF.subject, nuri(s)))
            g.add((st, RDF.predicate, pred))
            g.add((st, RDF.object, nuri(o)))
            for k, v in attrs:
                p2, dt = EDGE_ATTRS[k]
                g.add((st, p2, Literal(str(v), datatype=dt)))
        if e.get("predicate") == "bridge:restricts":
            n_restricts += 1
    rep["restricts_edges"] = n_restricts

    # 4) SourceCoverage: DP4(관측된 부재)의 실체화
    d = json.loads((DATA / "coverage_pilot_2026-07-06.json").read_text(encoding="utf-8"))
    n_cov = 0
    for r in d.get("records", []):
        slug = re.sub(r"[^A-Za-z0-9]+", "_", str(r["source"])).strip("_")
        u = nuri(f"coverage:{slug}")
        g.add((u, RDF.type, term("core:SourceCoverage")))
        g.add((u, CORE.canonicalId, Literal(f"COVERAGE:{slug}")))
        g.add((u, RDFS.label, Literal(f"Source coverage: {r['source']}")))
        g.add((u, CORE.source, Literal(str(r["source"]))))
        if r.get("coverageStart") is not None:
            g.add((u, CORE.coverageStart, Literal(str(r["coverageStart"]), datatype=XSD.gYear)))
        if r.get("coverageEnd") is not None:
            g.add((u, CORE.coverageEnd, Literal(str(r["coverageEnd"]), datatype=XSD.gYear)))
        g.add((u, CORE.observedCount, Literal(int(r["observedCount"]), datatype=XSD.integer)))
        n_cov += 1
    rep["coverage_records"] = n_cov
    return rep


def shacl(g: Graph, label: str) -> dict:
    """파일럿 그래프 SHACL 검증.

    ont_graph 에 rdfs:domain/range 를 그대로 넘기면 RDFS range 규칙이 검사 대상
    타입을 사전 공급해 sh:class 제약이 공허하게 통과한다. validate.py 의
    ont_for_shacl 와 같은 서브그래프를 쓴다.
    """
    import sys as _sys
    _sys.path.insert(0, str(ONT))
    from validate import ont_for_shacl  # type: ignore[import-not-found]  # 정본 재사용

    ont = Graph().parse(str(ONT / "ontology.ttl"), format="turtle")
    sh = Graph().parse(str(ONT / "shapes.ttl"), format="turtle")
    conforms, rgraph, rtext = shacl_validate(
        g, shacl_graph=sh, ont_graph=ont_for_shacl(ont),
        inference="rdfs", advanced=True)
    (OUT / f"shacl_{label}.txt").write_text(rtext, encoding="utf-8")
    n_viol = rtext.count("Constraint Violation")
    return {"conforms": bool(conforms), "violations": n_viol}

if __name__ == "__main__":
    # 디렉터리 존재가 아니라 필수 입력 파일로 판정한다. 기탁에는 사례 파일
    # (재배포 적격)만 동봉되므로 디렉터리는 있되 원자료는 없다.
    _need = sorted(DATA.glob("curated_intl_*_deposit.json"))
    if not _need:
        print("""원자료(system/data/curated/) 없음: 이 배포본에는 라이선스상 제외된
원자료(UN Comtrade·ETO 포함 큐레이션 JSON)가 없다. README 의 재현 절 안내대로
원자료를 확보하면 두 그래프가 재구축된다. 산출 결과물은 out/ 에 동봉되어 있다.""")
        raise SystemExit(2)
    report = {"date": RELEASE_DATE, "graphs": {}}
    demo_files = [DATA / "worked_example_japan2019_2026-07-07.json",
                  DATA / "worked_example_cq7_hhi_2026-07-08.json"]
    rep_d = {}
    g_demo = build_graph(demo_files, rep_d)
    reify_identifiers(g_demo, rep_d)
    tag_identifier_status(g_demo, rep_d)
    add_provenance(g_demo, "demo", rep_d)
    g_demo.serialize(str(OUT / "pilot_kg_demo.ttl"), format="turtle")
    rep_d.update(shacl(g_demo, "demo"))
    rep_d["triples"] = len(g_demo)
    report["graphs"]["demo"] = rep_d

    rep_p = {}
    g_dep = build_graph([DATA / "curated_intl_2026-07-04_deposit.json"], rep_p)
    rep_p["gleif_ownership_edges"] = add_gleif_ownership(g_dep)
    rep_p.update(add_deposit_extras(g_dep))
    add_case_smic(g_dep, rep_p)
    derive_exposes(g_dep, rep_p)
    reify_identifiers(g_dep, rep_p)
    tag_identifier_status(g_dep, rep_p)
    add_provenance(g_dep, "deposit", rep_p)
    g_dep.serialize(str(OUT / "pilot_kg_deposit.ttl"), format="turtle")
    rep_p.update(shacl(g_dep, "deposit"))
    rep_p["triples"] = len(g_dep)
    report["graphs"]["deposit"] = rep_p

    (OUT / "materialize_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=1))
    # 두 그래프 모두 적합해야 성공이다. demo 만 보면 논문이 보고하는 기탁 그래프가
    # 비적합인 채로 파이프라인이 통과한다.
    bad = [name for name, r in report["graphs"].items()
           if not r.get("conforms") or r.get("violations")]
    if bad:
        print(f"FAIL: SHACL 비적합 그래프 {bad}")
    sys.exit(1 if bad else 0)
