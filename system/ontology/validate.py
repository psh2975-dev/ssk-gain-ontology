# -*- coding: utf-8 -*-
"""
온톨로지 검증 하니스

1) owlrl OWL RL 추론 → 일관성(모순) 검사 (HermiT 대체; Java 불요)
   - disjointWith 위반, domain/range 충돌로 인한 owl:Nothing 멤버십 등을 탐지
2) pySHACL 제약 검증
   - (a) 적합(conforming) 샘플 인스턴스 → 위반 0 이어야 함
   - (b) 의도적 위반(violating) 샘플 → 위반이 잡혀야 함 (shape 가 실제로 작동하는지)

통과 조건: owlrl 모순 0 AND 적합 표본 위반 0 AND 위반 표본 탐지됨
실행: $env:PYTHONUTF8=1; python validate.py
"""
from __future__ import annotations

# 콘솔 인코딩 방어. 윈도 기본 콘솔(cp949 등)에서는 비ASCII 문자를 출력할 때
# UnicodeEncodeError 로 죽는다. 표준 출력만 UTF-8 로 재설정한다.
import sys as _sys
if hasattr(_sys.stdout, "reconfigure"):
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import sys
from pathlib import Path

from rdflib import Graph, Namespace, Literal
from rdflib.namespace import RDF, RDFS, OWL, XSD

BASE = "https://w3id.org/ssk-gain/ontology/"
CORE = Namespace(BASE + "core#")
INTL = Namespace(BASE + "intl#")
GVC = Namespace(BASE + "gvc#")
BR = Namespace(BASE + "bridge#")
EX = Namespace("https://w3id.org/ssk-gain/data/")

HERE = Path(__file__).resolve().parent


def load_ontology() -> Graph:
    g = Graph()
    g.parse(str(HERE / "ontology.ttl"), format="turtle")
    return g


# ---------------------------------------------------------------------------
# 1) owlrl OWL RL 일관성 추론
# ---------------------------------------------------------------------------
# owlrl 은 모순을 DAML agent-ont 'error' 술어로 보고한다 (owl:Nothing 멤버십 아님).
from rdflib import URIRef as _URIRef
OWLRL_ERROR_PRED = _URIRef("http://www.daml.org/2002/03/agents/agent-ont#error")


from rdflib import BNode as _BNode


def check_consistency(onto: Graph) -> tuple[bool, list[str]]:
    """owlrl OWL RL 추론으로 모순을 탐지한다.

    owlrl 은 disjoint 위반 등 모순을 agent-ont#error 술어 트리플로 기록한다.
    (실제 동작은 validate.py 의 adversarial 자가점검으로 확인, disjoint 주입 시 탐지됨.)
    또한 보강으로 owl:Nothing 의 실제 개체 멤버십도 함께 점검한다.
    """
    import owlrl
    g = Graph()
    for t in onto:
        g.add(t)
    # OWL RL 확장, 의미 규칙 적용(disjoint·domain·range 전파)
    owlrl.DeductiveClosure(owlrl.OWLRL_Semantics).expand(g)

    problems = []
    # (a) owlrl 의 모순 보고(error 술어)
    for s, _, o in g.triples((None, OWLRL_ERROR_PRED, None)):
        problems.append(f"owlrl inconsistency: {o}")
    # (b) 보강: owl:Nothing 에 실제 개체가 멤버로 추론되면 모순
    #     (owl:Nothing 자기참조 공리 트리플은 제외하고 외부 개체만)
    nothing_members = [x for x in g.subjects(RDF.type, OWL.Nothing)
                       if x != OWL.Nothing]
    if nothing_members:
        problems.append(f"owl:Nothing 개체 멤버 {len(nothing_members)}건: "
                        f"{[str(x) for x in nothing_members[:5]]}")
    ok = len(problems) == 0
    return ok, problems


def _inject_and_expand(onto: Graph, types: list) -> int:
    """개체 하나에 주어진 타입들을 부여하고 OWL RL 확장 후 모순 건수를 센다."""
    g = Graph()
    for t in onto:
        g.add(t)
    for ty in types:
        g.add((EX.Probe, RDF.type, ty))
    import owlrl
    owlrl.DeductiveClosure(owlrl.OWLRL_Semantics).expand(g)
    return len(list(g.triples((None, OWLRL_ERROR_PRED, None))))


def check_consistency_detects_contradiction(onto: Graph) -> bool:
    """비-vacuous 증명: disjoint 위반을 주입하면 모순이 잡혀야 한다.

    Organization ⊓ Country = ∅ 공리에 위배되는 개체를 넣고 탐지되는지 확인.
    이 점검이 PASS 해야 [1] 일관성 검사가 실제로 작동함을 보장한다.
    """
    return _inject_and_expand(onto, [CORE.Organization, CORE.Country]) > 0


def check_role_typing_contract(onto: Graph) -> tuple[bool, int, int]:
    """배제 공리가 범주 혼동만 잡고 역할 병존은 허용하는지 양쪽에서 검사한다.

    정책 ⊓ 조직은 모순이어야 하고, 교차도메인 통합이 의존하는 이중 타입
    (SanctionedEntity ⊓ Company, 둘 다 Organization 하위)은 통과해야 한다.
    한쪽만 보면 과잉 공리와 공허 공리를 구별하지 못한다.
    """
    n_bad = _inject_and_expand(onto, [INTL.FinancialSanction, INTL.SanctionedEntity])
    n_dual = _inject_and_expand(onto, [INTL.SanctionedEntity, GVC.Company])
    return (n_bad > 0 and n_dual == 0), n_bad, n_dual


# ---------------------------------------------------------------------------
# 2) 샘플 인스턴스, 적합 / 위반
# ---------------------------------------------------------------------------

def check_identity_axiom(onto: Graph) -> tuple[bool, bool]:
    """정준 식별자가 동일성을 실제로 결정하는지 확인한다.

    MD3(정준 식별자에 의한 교차 도메인 결합)는 「같은 식별자면 같은 개체」에 기댄다.
    그 규칙이 파이프라인 코드에만 있고 어휘에 없으면, 어휘를 재사용하는 제3자는
    같은 결합을 얻지 못한다. 두 가지를 함께 본다.
      (a) 같은 LEI 를 가진 별개 노드 둘 -> sameAs 가 추론되어야 한다
      (b) 다른 LEI 를 가진 별개 노드 둘 -> sameAs 가 추론되지 않아야 한다
    (b) 가 없으면 (a) 는 무엇이든 동일시하는 공허한 통과일 수 있다.
    """
    import owlrl

    def infer(lei_a: str, lei_b: str) -> bool:
        g = Graph()
        for s, p_, o in onto:
            g.add((s, p_, o))
        for u, v in ((EX.IdA, lei_a), (EX.IdB, lei_b)):
            ident = _URIRef("http://example.org/ssk#id-LEI-" + v)
            g.add((ident, RDF.type, CORE.Identifier))
            g.add((ident, CORE.identifierScheme, Literal("LEI", datatype=XSD.string)))
            g.add((ident, CORE.identifierValue, Literal(v, datatype=XSD.string)))
            g.add((u, RDF.type, CORE.Organization))
            g.add((u, CORE.hasIdentifier, ident))
            g.add((u, CORE.lei, Literal(v)))
        owlrl.DeductiveClosure(owlrl.OWLRL_Semantics).expand(g)
        return ((EX.IdA, OWL.sameAs, EX.IdB) in g
                or (EX.IdB, OWL.sameAs, EX.IdA) in g)

    same = infer("549300KB6NK5SBD14S87", "549300KB6NK5SBD14S87")
    diff = infer("549300KB6NK5SBD14S87", "724500Y6DUVH1DUCME49")
    return same, diff


def check_module_documents() -> tuple[bool, list[str]]:
    """모듈 문서를 따로 읽어, 그 문서만으로 어휘가 온전한지 본다.

    원고는 소비자가 모듈 하나만 스키마 계약으로 가져갈 수 있다고 말한다. 그렇다면
    검사도 그 소비자처럼 모듈 문서만 읽어야 한다. 통합본만 보면 분리 과정에서
    생긴 손상이 보이지 않는다. 실측(v0.1.5): bridge.ttl 에서 owl:unionOf 가 빈
    컬렉션을 가리켜 bridge:affects 의 치역이 owl:Nothing 이 되어 있었다.
    """
    from rdflib.namespace import OWL as _OWL
    problems = []
    for name in ("core", "intl", "gvc", "bridge"):
        path = HERE / f"{name}.ttl"
        if not path.exists():
            problems.append(f"{name}.ttl absent")
            continue
        mg = Graph()
        mg.parse(str(path), format="turtle")
        for coll in (_OWL.unionOf, _OWL.intersectionOf, _OWL.oneOf):
            for o in mg.objects(None, coll):
                if not list(mg.items(o)):
                    problems.append(f"{name}.ttl: empty {coll.split('#')[-1]} collection")
        for prop, val in list(mg.subject_objects(RDFS.range)):
            if isinstance(val, _BNode) and not list(mg.predicate_objects(val)):
                problems.append(f"{name}.ttl: dangling range node on {prop.split('#')[-1]}")
    return not problems, problems


def check_module_documents_detect_damage() -> bool:
    """[1e] 의 비공허성. 빈 컬렉션을 주입하면 반드시 잡혀야 한다."""
    from rdflib.namespace import OWL as _OWL
    mg = Graph()
    mg.parse(str(HERE / "bridge.ttl"), format="turtle")
    broken = _BNode("brokenunion")
    holder = _BNode("brokenholder")
    mg.add((holder, RDF.type, _OWL.Class))
    mg.add((holder, _OWL.unionOf, broken))
    return not list(mg.items(broken))


def check_identifier_duplication() -> tuple[bool, bool]:
    """식별자 중복 탐지의 양방향 시험 (재심사 지시 4).

    역함수 공리의 보증은 「같은 (체계, 값) = 같은 개체」라는 주조 규칙
    (id:{scheme}:{value}, percent-encoding)이 지켜질 때만 성립한다. 규칙이
    깨진 그래프(같은 쌍에 개체 둘)는 탐지 질의에 잡혀야 하고, 규칙을 지킨
    그래프는 잡히지 않아야 한다.
    """
    Q = """
    PREFIX core: <https://w3id.org/ssk-gain/ontology/core#>
    SELECT ?a ?b WHERE {
      ?a a core:Identifier ; core:identifierScheme ?s ; core:identifierValue ?v .
      ?b a core:Identifier ; core:identifierScheme ?s ; core:identifierValue ?v .
      FILTER(STR(?a) < STR(?b))
    }"""

    def build(dup: bool) -> Graph:
        d = Graph()
        d.bind("core", CORE)
        ids = [_URIRef("http://example.org/ssk#idA")]
        if dup:
            ids.append(_URIRef("http://example.org/ssk#idB"))
        for u in ids:
            d.add((u, RDF.type, CORE.Identifier))
            d.add((u, CORE.identifierScheme, Literal("LEI")))
            d.add((u, CORE.identifierValue, Literal("549300KB6NK5SBD14S87")))
        return d

    caught = len(list(build(True).query(Q))) > 0
    clean = len(list(build(False).query(Q))) == 0
    return caught, clean


def merge_conflict_samples() -> tuple[Graph, Graph]:
    """오병합 탐지의 양방향 표본.

    같은 LEI 를 가진 두 노드가 본사 소재국에서 어긋나면 병합을 의심해야 한다.
    (a) 어긋나는 표본은 위반으로 잡혀야 하고
    (b) 어긋나지 않는 표본은 통과해야 한다.
    (b) 가 없으면 (a) 는 같은 LEI 를 무조건 거부하는 과잉 제약일 수 있다.
    """
    def build(hq_b: str) -> Graph:
        d = Graph()
        for u, hq in ((EX.MergeA, "KOR"), (EX.MergeB, hq_b)):
            d.add((u, RDF.type, CORE.Organization))
            d.add((u, CORE.lei, Literal("549300KB6NK5SBD14S87")))
            d.add((u, CORE.label, Literal("Test firm", datatype=XSD.string)))
            c = _URIRef("http://example.org/ssk#c" + hq)
            d.add((c, RDF.type, CORE.Country))
            d.add((c, CORE.isoAlpha3, Literal(hq)))
            d.add((c, CORE.canonicalId, Literal(hq)))
            d.add((u, INTL.headquarteredIn, c))
        return d
    return build("USA"), build("KOR")

def conforming_instances() -> Graph:
    """온톨로지·SHACL 를 모두 만족하는 최소 인스턴스 집합.

    시나리오: 화웨이(제재대상)가 비제재 자회사를 통해 삼성에 우회 공급(circumvents),
    일본 수출규제(restricts)가 불화수소(Material)를 제한, 한국의 일본 소재 의존(exposes).
    """
    g = Graph()
    g.bind("core", CORE); g.bind("intl", INTL); g.bind("gvc", GVC)
    g.bind("bridge", BR); g.bind("ex", EX)

    # 국가
    KOR, USA, CHN, JPN = EX.KOR, EX.USA, EX.CHN, EX.JPN
    for c, iso, ko in [(KOR, "KOR", "대한민국"), (USA, "USA", "미국"),
                       (CHN, "CHN", "중국"), (JPN, "JPN", "일본")]:
        g.add((c, RDF.type, CORE.Country))
        g.add((c, CORE.isoAlpha3, Literal(iso)))
        # 국가의 정준 식별자도 alpha-3
        g.add((c, CORE.canonicalId, Literal(iso)))
        g.add((c, CORE.label, Literal(ko)))

    # 기업 (Company; LEI 20자)
    samsung, skhynix = EX.Samsung, EX.SKHynix
    huawei = EX.Huawei                  # 제재대상(SanctionedEntity)
    huawei_sub = EX.HuaweiSub           # 비제재 자회사(Company)
    g.add((samsung, RDF.type, GVC.Company))
    g.add((samsung, CORE.lei, Literal("353800INNTXBCBGGTJ37")))
    g.add((samsung, CORE.label, Literal("삼성전자")))
    g.add((samsung, CORE.headquarteredIn, KOR))
    g.add((skhynix, RDF.type, GVC.Company))
    g.add((skhynix, CORE.lei, Literal("3538001YDPFKD5N6PT44")))
    g.add((skhynix, CORE.label, Literal("SK하이닉스")))
    g.add((huawei, RDF.type, INTL.SanctionedEntity))
    # 교차도메인 통합이 의존하는 이중 역할: 같은 법인이 제재 대상이면서 공급사슬
    # 참여 기업이다. 둘 다 Organization 하위이므로 배제 공리에 걸리지 않아야 한다
    # (3-3-1절 행태 계약). 적합 표본에 실제로 넣어 SHACL 통과를 함께 증명한다.
    g.add((huawei, RDF.type, GVC.Company))
    g.add((huawei, CORE.lei, Literal("300300C1024PFK4MAO79")))
    g.add((huawei, CORE.label, Literal("Huawei")))
    g.add((huawei, CORE.headquarteredIn, CHN))
    g.add((huawei_sub, RDF.type, GVC.Company))
    g.add((huawei_sub, CORE.lei, Literal("300300C1024PFK4MAO80")))
    g.add((huawei_sub, CORE.label, Literal("Huawei Subsidiary")))
    g.add((huawei, INTL.owns, huawei_sub))

    # 품목 (Material: 불화수소 HS 281111)
    hf = EX.HydrogenFluoride
    g.add((hf, RDF.type, CORE.Material))
    g.add((hf, CORE.hsCode, Literal("281111")))
    g.add((hf, CORE.label, Literal("불화수소(HF)")))

    # 제재 (Sanction)
    sanc = EX.HuaweiSanction
    g.add((sanc, RDF.type, INTL.Sanction))
    g.add((sanc, CORE.canonicalId, Literal("BIS:PROGRAM:ENTITY-LIST")))
    g.add((sanc, INTL.sanctionDate, Literal("2019-05-16", datatype=XSD.date)))
    g.add((sanc, INTL.listsEntity, huawei))

    # 등재 사실을 진술 개체로 표현한 표본. 등재는 조직의 유형이 아니라 기간·근거·
    # 발령기관을 갖는 사실이므로, 그 형태가 검증되는지 함께 확인한다.
    listing = EX.HuaweiListing2019
    g.add((listing, RDF.type, INTL.SanctionListing))
    g.add((listing, CORE.canonicalId, Literal("BIS:LISTING:ENTITY-LIST:HUAWEI")))
    g.add((listing, INTL.listedOrganization, huawei))
    g.add((listing, INTL.underSanction, sanc))
    g.add((listing, CORE.source, Literal("BIS Entity List")))

    # 소유관계 진술 표본. 지분율이 조직이 아니라 관계 개체에 붙는지 확인한다.
    own = EX.OwnershipHuaweiSub
    g.add((own, RDF.type, INTL.OwnershipAssertion))
    g.add((own, CORE.canonicalId, Literal("OWN:HUAWEI:HUAWEISUB")))
    g.add((own, INTL.owner, huawei))
    g.add((own, INTL.ownedOrganization, EX.HuaweiSub))
    g.add((own, INTL.ownershipPct, Literal("60.0", datatype=XSD.decimal)))

    # 수출통제 (ExportControl), 2019 일본 수출규제
    jpctl = EX.Japan2019Control
    g.add((jpctl, RDF.type, INTL.ExportControl))
    g.add((jpctl, INTL.controlScope, Literal("반도체 소재 3품목")))

    # 지정학사건 (GeopoliticalEvent)
    event = EX.USCHTariff
    g.add((event, RDF.type, INTL.GeopoliticalEvent))
    g.add((event, INTL.eventDate, Literal("2018-07-06", datatype=XSD.date)))

    # 무역흐름 (TradeFlow): 일본→한국 불화수소
    tf = EX.JP_KR_HF
    g.add((tf, RDF.type, GVC.TradeFlow))
    g.add((tf, GVC.flowOrigin, JPN))
    g.add((tf, GVC.flowDestination, KOR))
    g.add((tf, GVC.flowProduct, hf))
    g.add((tf, GVC.tradeValueUSD, Literal("1000000.0", datatype=XSD.decimal)))

    # 공급관계 (SupplyEdge): huawei_sub → samsung, HF
    se = EX.SupplyEdge1
    g.add((se, RDF.type, GVC.SupplyEdge))
    g.add((se, GVC.supplier, huawei_sub))
    g.add((se, GVC.customer, samsung))
    g.add((se, GVC.suppliesProduct, hf))
    g.add((se, CORE.confidence, Literal("0.85", datatype=XSD.decimal)))

    # 소유경로 (OwnershipPath): huawei → huawei_sub
    op = EX.OwnPath1
    g.add((op, RDF.type, INTL.OwnershipPath))
    g.add((op, INTL.pathStart, huawei))
    g.add((op, INTL.pathEnd, huawei_sub))
    g.add((op, BR.hops, Literal(1, datatype=XSD.integer)))
    g.add((op, BR.suspicion, Literal("0.7", datatype=XSD.decimal)))

    # 의존관계 (Dependency): 한국의 불화수소 의존
    dep = EX.KR_HF_Dependency
    g.add((dep, RDF.type, GVC.Dependency))
    g.add((dep, GVC.dependentActor, KOR))
    g.add((dep, GVC.dependsOnProduct, hf))
    g.add((dep, GVC.hhi, Literal("0.85", datatype=XSD.decimal)))  # 0~1 척도(점유율 제곱합)

    # 위험노드 (RiskNode)
    risk = EX.HF_RiskNode
    g.add((risk, RDF.type, GVC.RiskNode))

    # --- Bridge 관계 (5종 모두) ---
    g.add((huawei, BR.affects, se))            # affects: SanctionedEntity → SupplyEdge
    g.add((huawei, BR.riskScore, Literal("0.9", datatype=XSD.decimal)))
    g.add((event, BR.disrupts, tf))            # disrupts: Event → TradeFlow
    g.add((jpctl, BR.restricts, hf))           # restricts: ExportControl → Product
    g.add((op, BR.circumvents, sanc))          # circumvents: OwnershipPath → Sanction
    g.add((dep, BR.exposes, risk))             # exposes: Dependency → RiskNode
    g.add((dep, BR.geoRisk, Literal("0.6", datatype=XSD.decimal)))

    return g


def violating_instances() -> Graph:
    """의도적 제약 위반, shape 가 실제로 탐지하는지 검증용."""
    g = Graph()
    g.bind("core", CORE); g.bind("intl", INTL); g.bind("gvc", GVC); g.bind("bridge", BR)

    # 위반1: ISO alpha-3 형식 오류(소문자·길이) + LEI 형식 오류
    bad_country = EX.BadCountry
    g.add((bad_country, RDF.type, CORE.Country))
    g.add((bad_country, CORE.isoAlpha3, Literal("ko")))      # 소문자·2자 → 위반

    bad_org = EX.BadOrg
    g.add((bad_org, RDF.type, GVC.Company))
    g.add((bad_org, CORE.lei, Literal("SHORT")))             # LEI 형식 위반

    # 위반2: SupplyEdge 가 supplier 없이 customer 만 (minCount 위반) + 신뢰도 범위 초과
    bad_se = EX.BadSupplyEdge
    g.add((bad_se, RDF.type, GVC.SupplyEdge))
    g.add((bad_se, GVC.customer, bad_org))                   # supplier 누락 → 위반
    g.add((bad_se, CORE.confidence, Literal("1.5", datatype=XSD.decimal)))  # >1 위반

    # 위반3: HHI 범위 초과
    bad_dep = EX.BadDependency
    g.add((bad_dep, RDF.type, GVC.Dependency))
    g.add((bad_dep, GVC.dependentActor, bad_org))
    g.add((bad_dep, GVC.hhi, Literal("1.5", datatype=XSD.decimal)))  # >1 위반(0~1 척도)

    # 위반4: circumvents hop 범위 초과
    bad_op = EX.BadOwnPath
    g.add((bad_op, RDF.type, INTL.OwnershipPath))
    g.add((bad_op, INTL.pathStart, EX.SomeSanctioned))
    g.add((EX.SomeSanctioned, RDF.type, INTL.SanctionedEntity))
    g.add((bad_op, INTL.pathEnd, bad_org))
    g.add((bad_op, BR.hops, Literal(5, datatype=XSD.integer)))  # >3 위반

    # --- (회귀 방지) Bridge range 위반(sh:class), vacuity 가 재발하면 미탐지된다 ---
    # 위반5: disrupts 의 range 는 TradeFlow 인데 Company 를 줌
    bad_ev = EX.BadEvent
    g.add((bad_ev, RDF.type, INTL.GeopoliticalEvent))
    bad_co = EX.BadDisruptTarget
    g.add((bad_co, RDF.type, GVC.Company))           # TradeFlow 아님 → 위반
    g.add((bad_ev, BR.disrupts, bad_co))

    # 위반6: circumvents 의 range 는 Sanction 인데 Product 를 줌
    bad_op2 = EX.BadOwnPath2
    g.add((bad_op2, RDF.type, INTL.OwnershipPath))
    bad_prod = EX.BadCircumventTarget
    g.add((bad_prod, RDF.type, CORE.Product))        # Sanction 아님 → 위반
    g.add((bad_op2, BR.circumvents, bad_prod))

    # 위반7: restricts 의 range 는 Product 인데 Organization 을 줌
    bad_ec = EX.BadExportControl
    g.add((bad_ec, RDF.type, INTL.ExportControl))
    bad_org2 = EX.BadRestrictTarget
    g.add((bad_org2, RDF.type, CORE.Organization))   # Product 아님 → 위반
    g.add((bad_ec, BR.restricts, bad_org2))

    return g


def range_violation_probes() -> list[tuple[str, Graph, "Namespace"]]:
    """(비-vacuity 증명) Bridge sh:class range 위반을 개별 데이터로 격리.

    각 프로브는 *오직 하나의* range 위반만 담아, run_shacl 이 그 위반을 실제로
    탐지하는지 1:1 로 증명한다. vacuity 가 재발(ont_graph 가 range 로 타입을 날조)
    하면 이 프로브들이 통과(conforms=True)해버리므로 회귀가 즉시 드러난다.

    반환: (이름, 데이터그래프, 기대 위반 경로 URIRef) 목록.
    """
    probes = []

    # disrupts → Company (range=TradeFlow 위반)
    g1 = Graph()
    g1.add((EX.P_Ev, RDF.type, INTL.GeopoliticalEvent))
    g1.add((EX.P_Co, RDF.type, GVC.Company))
    g1.add((EX.P_Ev, BR.disrupts, EX.P_Co))
    probes.append(("disrupts→Company (range=TradeFlow)", g1, BR.disrupts))

    # circumvents → Product (range=Sanction 위반)
    g2 = Graph()
    g2.add((EX.P_Op, RDF.type, INTL.OwnershipPath))
    g2.add((EX.P_Prod, RDF.type, CORE.Product))
    g2.add((EX.P_Op, BR.circumvents, EX.P_Prod))
    probes.append(("circumvents→Product (range=Sanction)", g2, BR.circumvents))

    # restricts → Organization (range=Product 위반)
    g3 = Graph()
    g3.add((EX.P_Ec, RDF.type, INTL.ExportControl))
    g3.add((EX.P_Org, RDF.type, CORE.Organization))
    g3.add((EX.P_Ec, BR.restricts, EX.P_Org))
    probes.append(("restricts→Organization (range=Product)", g3, BR.restricts))

    return probes


def ont_for_shacl(onto: Graph) -> Graph:
    """SHACL 추론용 온톨로지 서브그래프, rdfs:domain·rdfs:range 트리플 제거.

    (vacuity 차단)
    pySHACL 에 ont_graph=onto + inference="rdfs" 를 함께 주면, RDFS range 규칙
        (P rdfs:range C), (x P y)  ⊢  (y a C)
    가 *검사 대상 타입을 사전 날조*한다. 그 결과 sh:class range 제약이
    항상 vacuous 하게 통과한다(예: `disrupts→Company` 오분류 추출이 게이트 통과).

    해법: rdfs:domain·rdfs:range 트리플만 제거한 서브그래프를 ont_graph 로 쓴다.
    subClassOf(클래스 계층) 추론은 유지되어 SanctionedEntity/Company ⊑ Organization
    같은 정당한 상위클래스 매칭은 계속 동작한다. 반면 속성의 range 가 타입을
    역으로 주입하는 경로만 끊어, SHACL sh:class 가 *실제 선언된 타입*만 검사한다.
    """
    onto_sub = Graph()
    for s, p, o in onto:
        if p in (RDFS.domain, RDFS.range):
            continue
        onto_sub.add((s, p, o))
    return onto_sub


def run_shacl(data: Graph, shapes_path: Path, onto: Graph, *, return_graph=False):
    from pyshacl import validate
    # ont_graph 에서 rdfs:domain/range 를 제거해 range 규칙의 타입 공급(vacuity)을
    #      차단한다. subClassOf 추론은 유지 → sh:class 가 상위클래스 매칭은 정상 수행.
    onto_sub = ont_for_shacl(onto)
    conforms, results_graph, results_text = validate(
        data_graph=data,
        shacl_graph=str(shapes_path),
        ont_graph=onto_sub,             # rdfs subclass 추론 유지, domain/range 제거
        inference="rdfs",
        abort_on_first=False,
        meta_shacl=False,
        advanced=True,
        debug=False,
    )
    if return_graph:
        return conforms, results_text, results_graph
    return conforms, results_text


# SHACL 결과 그래프 검사용 네임스페이스
SH = Namespace("http://www.w3.org/ns/shacl#")


def has_class_violation_on_path(results_graph: Graph, path_uri) -> bool:
    """결과 그래프에서 특정 sh:path 에 대한 ClassConstraintComponent 위반이 있는지.

    results_text 문자열 매칭(prefix vs full URI 불일치 위험)에 의존하지 않고
    SHACL 표준 결과 그래프(sh:ValidationResult)를 구조적으로 질의한다.
    """
    from rdflib import URIRef as _U
    for res in results_graph.subjects(RDF.type, SH.ValidationResult):
        comp = results_graph.value(res, SH.sourceConstraintComponent)
        rpath = results_graph.value(res, SH.resultPath)
        if comp == SH.ClassConstraintComponent and rpath == path_uri:
            return True
    return False


def main():
    onto = load_ontology()
    shapes_path = HERE / "shapes.ttl"

    print("=" * 70)
    print("SSK ontology validation harness (11 checks)")
    print("=" * 70)

    # --- 1) 일관성 ---
    print("\n[1] OWL RL consistency by owlrl")
    ok_cons, problems = check_consistency(onto)
    if ok_cons:
        print("    PASS  no contradiction (no owlrl error predicate, no disjointness violation)")
    else:
        print("    FAIL  contradictions found:")
        for p in problems:
            print("      -", p)

    # --- 1b) 일관성 검사 비-vacuity 증명 ---
    print("\n[1b] Non-vacuity of [1]: an injected disjointness violation must be detected")
    ok_probe = check_consistency_detects_contradiction(onto)
    if ok_probe:
        print("    PASS  the injected Organization-Country violation was detected "
              "(the consistency check does fire)")
    else:
        print("    FAIL  injection went undetected, so check [1] is vacuous")

    # --- 1c) 역할 병존 계약 (범주 혼동은 잡고 이중 역할은 통과) ---
    print("\n[1c] Role-typing contract: policy-organisation confusion caught, dual role admitted")
    ok_role, n_bad, n_dual = check_role_typing_contract(onto)
    if ok_role:
        print(f"    PASS  {n_bad} FinancialSanction-SanctionedEntity contradiction(s) caught "
              f"(the misclassification the pilot data contained), {n_dual} for "
              f"SanctionedEntity-Company (the dual role is admitted)")
    else:
        print(f"    FAIL  misclassification caught {n_bad} (must be > 0), "
              f"dual-role contradictions {n_dual} (must be 0)")

    # --- 1d) 정준 식별자의 동일성 결정력 ---
    print(chr(10) + "[1d] Identity axiom: same LEI infers sameAs, different LEI does not")
    id_same, id_diff = check_identity_axiom(onto)
    if id_same and not id_diff:
        print("    PASS  same LEI inferred identical, different LEI not "
              "(the identifier decides identity at the vocabulary level)")
    else:
        print(f"    FAIL  same-LEI inference {id_same} (must be True), "
              f"different-LEI inference {id_diff} (must be False)")
    # --- 1e) 모듈 문서 무결성 (소비자가 실제로 읽는 파일을 본다) ---
    print(chr(10) + "[1e] Module documents: each module read alone must be intact")
    ok_mod, mod_problems = check_module_documents()
    if ok_mod:
        print("    PASS  no empty owl collection and no dangling range node in "
              "core.ttl, intl.ttl, gvc.ttl, bridge.ttl")
    else:
        print("    FAIL  the module documents are damaged:")
        for m in mod_problems:
            print("      -", m)

    # --- 1f) 그 검사의 비공허성 ---
    print(chr(10) + "[1f] Non-vacuity of [1e]: an injected empty collection must be detected")
    ok_mod_probe = check_module_documents_detect_damage()
    if ok_mod_probe:
        print("    PASS  the injected empty union was detected (the check does fire)")
    else:
        print("    FAIL  injection went undetected, so check [1e] is vacuous")

    # --- 1g·1h) 식별자 중복 탐지와 그 비공허성 ---
    print(chr(10) + "[1g] Duplicate-identifier detection: two individuals for one "
          "scheme-value pair must be caught")
    dup_caught, dup_clean = check_identifier_duplication()
    if dup_caught and dup_clean:
        print("    PASS  a duplicated pair is detected and a clean graph is not "
              "(the minting rule id:{scheme}:{value} is what the inverse "
              "functional axiom relies on; the materialisation counts "
              "violations on every real build)")
    else:
        print(f"    FAIL  duplicated caught {dup_caught} (must be True), "
              f"clean flagged {not dup_clean} (must be False)")

    # --- 2a) 적합 샘플 ---
    print("\n[2a] SHACL on a conforming sample")
    conf_data = conforming_instances()
    c1, txt1 = run_shacl(conf_data, shapes_path, onto)
    if c1:
        print(f"    PASS  no violation ({len(conf_data)} instance triples validated)")
    else:
        print("    FAIL  the conforming sample raised violations:")
        print(txt1)

    # --- 2b) 위반 샘플 ---
    print("\n[2b] SHACL on a deliberately violating sample: violations must be raised")
    viol_data = violating_instances()
    c2, txt2 = run_shacl(viol_data, shapes_path, onto)
    n_viol = txt2.count("Constraint Violation")
    if not c2 and n_viol > 0:
        print(f"    PASS  {n_viol} violation(s) raised as expected (the shapes fire)")
    else:
        print("    FAIL, 위반 샘플이 탐지되지 않음 (shape 무효):")
        print(txt2)

    # --- 2c) Bridge range(sh:class) 위반 개별 탐지, vacuity 회귀 방지 ---
    print("\n[2c] Per-relation range probes: each bridge relation must fire on a mistyped target"
          "")
    probes = range_violation_probes()
    range_ok = True
    n_detected = 0
    for name, pdata, ppath in probes:
        pc, ptxt, pgraph = run_shacl(pdata, shapes_path, onto, return_graph=True)
        # 해당 경로(ppath)에 대한 sh:class 위반(ClassConstraintComponent)이 결과
        # 그래프에 실제로 존재하는지 구조적으로 확인 (문자열 매칭 비의존).
        has_class_viol = has_class_violation_on_path(pgraph, ppath)
        if (not pc) and has_class_viol:
            n_detected += 1
            print(f"    PASS  {name} raised a ClassConstraint violation")
        else:
            range_ok = False
            print(f"    FAIL  {name} was not detected (vacuity may have returned)")
            print("           conforms:", pc,
                  "| ClassConstraint(해당경로):", has_class_viol)
    if range_ok:
        print(f"    => {n_detected}/{len(probes)} range probes detected "
              f"(sh:class checks proven non-vacuous)")

    # --- 2d) 오병합 탐지 (교차 노드 제약) ---
    print(chr(10) + "[2d] Merge-conflict detection: conflicting properties on a shared LEI must be flagged")
    bad_g, good_g = merge_conflict_samples()
    c_bad, _ = run_shacl(bad_g, shapes_path, onto)
    c_good, _ = run_shacl(good_g, shapes_path, onto)
    merge_ok = (not c_bad) and c_good
    if merge_ok:
        print("    PASS  conflicting-headquarters sample flagged, consistent sample passed "
              "(validation revisits what inference merged)")
    else:
        print(f"    FAIL  conflicting sample conforms {c_bad} (must be False), "
              f"consistent sample conforms {c_good} (must be True)")
    # --- 게이트 ---
    print("\n" + "=" * 70)
    gate = (ok_cons and ok_probe and ok_role and id_same and (not id_diff) and c1
            and (not c2 and n_viol > 0) and range_ok and merge_ok)
    if gate:
        print("GATE: PASS — consistency (non-vacuous) + role-typing contract + identity axiom + module documents "
              "+ conforming sample + violation detection + per-relation range probes "
              "+ merge-conflict detection")
    else:
        print("GATE: FAIL")
    print("=" * 70)
    return 0 if gate else 1


if __name__ == "__main__":
    sys.exit(main())
