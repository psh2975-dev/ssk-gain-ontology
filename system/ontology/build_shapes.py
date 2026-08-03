# -*- coding: utf-8 -*-
"""
SHACL 제약(shapes.ttl) 생성기

NRF-2024S1A3A2A07046144 | 동아대학교 경영정보학과 | 박성호

각 관계·속성의 도메인·레인지·카디널리티·값 범위를 SHACL NodeShape/PropertyShape로
규정한다. pySHACL 로 인스턴스 데이터를 검증할 때 사용.

sh:targetClass 로 노드별 형태를 묶고, sh:property 로 속성 제약을 건다.
- 도메인: 어떤 클래스 인스턴스가 이 속성을 가질 수 있는가 (targetClass)
- 레인지: sh:class / sh:datatype / sh:nodeKind
- 카디널리티: sh:minCount / sh:maxCount
- 값 범위: sh:minInclusive / sh:maxInclusive / sh:pattern / sh:in

실행: $env:PYTHONUTF8=1; python build_shapes.py
"""
from __future__ import annotations

# 콘솔 인코딩 방어. 윈도 기본 콘솔(cp949 등)에서는 비ASCII 문자를 출력할 때
# UnicodeEncodeError 로 죽는다. 표준 출력만 UTF-8 로 재설정한다.
import sys as _sys
if hasattr(_sys.stdout, "reconfigure"):
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from pathlib import Path

from rdflib import Graph, Namespace, Literal, BNode, URIRef
from rdflib.namespace import RDF, RDFS, OWL, XSD, DCTERMS
from rdflib.collection import Collection

BASE = "https://w3id.org/ssk-gain/ontology/"
SSK = Namespace(BASE)
CORE = Namespace(BASE + "core#")
INTL = Namespace(BASE + "intl#")
GVC = Namespace(BASE + "gvc#")
BR = Namespace(BASE + "bridge#")
SH = Namespace("http://www.w3.org/ns/shacl#")
SHAPES = Namespace(BASE + "shapes#")

VERSION = "0.1.6"
# 릴리스 날짜는 고정한다. 실행일을 쓰면 재생성물이 날마다 달라져
# 체크섬으로 기탁물을 검증할 수 없다.
TODAY = "2026-08-01"


def new_graph() -> Graph:
    g = Graph()
    g.bind("sh", SH)
    g.bind("ssk", SSK)
    g.bind("core", CORE)
    g.bind("intl", INTL)
    g.bind("gvc", GVC)
    g.bind("bridge", BR)
    g.bind("shapes", SHAPES)
    g.bind("xsd", XSD)
    g.bind("dcterms", DCTERMS)

    # --- 교차 노드 검사 -------------------------------------------------
    # SHACL 은 노드를 하나씩 본다. 같은 식별자를 가진 다른 노드와의 모순은
    # 노드 단위 제약으로 잡히지 않아 SPARQL 제약이 필요하다.
    #
    # OWL 은 같은 LEI 를 보면 두 노드를 동일 개체로 추론한다(역함수적 속성).
    # 그 추론이 옳으려면 두 노드의 속성이 서로 어긋나지 않아야 한다. 어긋나면
    # 자료가 틀렸거나 식별자가 잘못 붙은 것이므로 병합을 의심해야 한다.
    # 추론(OWL)과 검사(SHACL)가 각자 할 일을 하는 지점이다.
    decl = URIRef(BASE + "shapes#prefixes")
    g.add((decl, RDF.type, OWL.Ontology))
    for pfx, ns in (("core", CORE), ("intl", INTL)):
        b = BNode()
        g.add((decl, SH.declare, b))
        g.add((b, SH.prefix, Literal(pfx)))
        g.add((b, SH.namespace, Literal(str(ns), datatype=XSD.anyURI)))

    for local, prop, ko in (("Headquarters", INTL.headquarteredIn, "본사 소재국"),
                            ("Incorporation", INTL.incorporatedIn, "법인설립국")):
        sh_node = URIRef(BASE + "shapes#SameLeiConsistent" + local)
        g.add((sh_node, RDF.type, SH.NodeShape))
        g.add((sh_node, SH.targetClass, CORE.Organization))
        g.add((sh_node, RDFS.label,
               Literal(f"같은 LEI {ko} 정합", lang="ko")))
        c = BNode()
        g.add((sh_node, SH.sparql, c))
        g.add((c, RDF.type, SH.SPARQLConstraint))
        g.add((c, SH.prefixes, decl))
        g.add((c, SH.severity, SH.Violation))
        g.add((c, SH.message,
               Literal(f"같은 LEI 를 가진 다른 노드와 {ko}이 어긋난다. "
                       f"식별자 오부여 또는 오병합을 의심할 것.", lang="ko")))
        g.add((c, SH.message,
               Literal(f"Conflicts with another node carrying the same LEI on "
                       f"{prop.split(chr(35))[-1]}. Suspect a misassigned identifier "
                       f"or a wrong merge.", lang="en")))
        g.add((c, SH.select, Literal(
            "SELECT $this ?value WHERE { "
            "$this core:lei ?lei . $this <" + str(prop) + "> ?mine . "
            "?other core:lei ?lei . ?other <" + str(prop) + "> ?value . "
            "FILTER (?other != $this && ?value != ?mine) }")))

    # 정준 식별자에는 근거 표시가 따라야 한다. 표준 등록부 근거인지 잠정 키인지
    # 구분되지 않으면 하류 이용자가 병합 신뢰도를 판단할 수 없다.
    idw = node_shape(g, SHAPES.IdentifierWarrantShape, CORE.Entity, "식별자 근거 형태")
    prop_shape(g, idw, CORE.identifierStatus, name="식별자상태",
               datatype=XSD.string, max_count=1,
               in_values=["authoritative", "provisional"],
               message="식별자 근거는 authoritative 또는 provisional 중 하나.")

    return g



# 결정론적 익명 노드. rdflib 의 BNode() 는 실행마다 임의 식별자를 만들어,
# 같은 코드가 매번 다른 파일을 낸다. 생성 순서가 고정돼 있으므로 순번을
# 부여해 재생성물이 바이트 단위로 같아지게 한다(체크섬 검증 가능).
_BN_SEQ = [0]


def bnode() -> BNode:
    _BN_SEQ[0] += 1
    return BNode(f"n{_BN_SEQ[0]:04d}")


def rdf_list(g, items):
    """RDF 컬렉션을 결정론적 익명 노드로 구성하고 첫 노드를 반환."""
    items = list(items)
    if not items:
        return RDF.nil
    head = cur = bnode()
    for i, item in enumerate(items):
        g.add((cur, RDF.first, item))
        if i + 1 < len(items):
            nxt = bnode()
            g.add((cur, RDF.rest, nxt))
            cur = nxt
        else:
            g.add((cur, RDF.rest, RDF.nil))
    return head

def prop_shape(g, parent_shape, path, *, name=None,
               cls=None, datatype=None, node_kind=None,
               min_count=None, max_count=None,
               min_inclusive=None, max_inclusive=None,
               pattern=None, in_values=None, severity=None,
               message=None):
    """parent NodeShape 에 sh:property 블록을 추가."""
    ps = bnode()
    g.add((parent_shape, SH.property, ps))
    g.add((ps, SH.path, path))
    if name:
        g.add((ps, SH.name, Literal(name, lang="ko")))
    if cls is not None:
        g.add((ps, SH["class"], cls))
    if datatype is not None:
        g.add((ps, SH.datatype, datatype))
    if node_kind is not None:
        g.add((ps, SH.nodeKind, node_kind))
    if min_count is not None:
        g.add((ps, SH.minCount, Literal(min_count)))
    if max_count is not None:
        g.add((ps, SH.maxCount, Literal(max_count)))
    if min_inclusive is not None:
        g.add((ps, SH.minInclusive, Literal(min_inclusive)))
    if max_inclusive is not None:
        g.add((ps, SH.maxInclusive, Literal(max_inclusive)))
    if pattern is not None:
        g.add((ps, SH.pattern, Literal(pattern)))
    if in_values is not None:
        g.add((ps, SH["in"], rdf_list(g, [Literal(v) for v in in_values])))
    g.add((ps, SH.severity, severity if severity is not None else SH.Violation))
    if message:
        g.add((ps, SH.message, Literal(message, lang="ko")))
    return ps


def node_shape(g, uri, target_class, label):
    g.add((uri, RDF.type, SH.NodeShape))
    g.add((uri, SH.targetClass, target_class))
    g.add((uri, RDFS.label, Literal(label, lang="ko")))
    return uri


def or_classes(g, shape, classes):
    """sh:or 로 여러 sh:class 대안을 허용 (union range 검증)."""
    members = []
    for c in classes:
        b = bnode()
        g.add((b, SH["class"], c))
        members.append(b)
    g.add((shape, SH["or"], rdf_list(g, members)))


def build_shapes(g: Graph):
    # 메타
    meta = URIRef(BASE + "shapes")
    g.add((meta, RDF.type, OWL.Ontology))
    g.add((meta, DCTERMS.title,
           Literal("SSK 온톨로지 SHACL 제약(shapes)", lang="ko")))
    g.add((meta, OWL.versionInfo, Literal(VERSION)))
    g.add((meta, DCTERMS.created, Literal(TODAY, datatype=XSD.date)))

    # -------------------------------------------------------------------
    # CORE, Organization / Country / Product
    # -------------------------------------------------------------------
    org = node_shape(g, SHAPES.OrganizationShape, CORE.Organization, "조직 형태")
    # LEI: 20자 영숫자, 최대 1개(functional), 권고(min 0, 미매칭 fallback 허용)
    prop_shape(g, org, CORE.lei, name="LEI", datatype=XSD.string,
               max_count=1, pattern=r"^[A-Z0-9]{18}[0-9]{2}$",
               message="LEI 는 ISO 17442 형식(20자 영숫자)이어야 하며 1개만 허용.")
    # 네임스페이스 주의: 두 속성은 intl 모듈 소속이다. core: 로 쓰면 온톨로지에
    # 없는 속성을 제약하게 되어 어떤 데이터에서도 발화하지 않는다.
    prop_shape(g, org, INTL.headquarteredIn, name="본사위치",
               cls=CORE.Country, max_count=1,
               message="본사위치 range 는 Country, 최대 1개.")
    prop_shape(g, org, INTL.incorporatedIn, name="법인설립국",
               cls=CORE.Country, max_count=1,
               message="법인설립국 range 는 Country, 최대 1개.")
    prop_shape(g, org, CORE.label, name="명칭", datatype=XSD.string,
               min_count=1, severity=SH.Warning,
               message="조직은 명칭(name) 1개 이상 권고.")

    country = node_shape(g, SHAPES.CountryShape, CORE.Country, "국가 형태")
    # ISO alpha-3: 정확히 3 대문자, functional → 정확히 1
    prop_shape(g, country, CORE.isoAlpha3, name="ISO3 코드", datatype=XSD.string,
               min_count=1, max_count=1, pattern=r"^[A-Z]{3}$",
               message="국가는 ISO 3166-1 alpha-3(대문자 3자) 정확히 1개.")
    # 정준 식별자도 alpha-3 로 제약한다. isoAlpha3 만 제약하면 alpha-2 canonicalId
    # 가 통과하고, 같은 국가가 두 표기로 들어와 별개 노드가 된다.
    prop_shape(g, country, CORE.canonicalId, name="정준 식별자", datatype=XSD.string,
               min_count=1, max_count=1, pattern=r"^[A-Z]{3}$",
               message="국가의 정준 식별자는 ISO 3166-1 alpha-3(대문자 3자).")

    product = node_shape(g, SHAPES.ProductShape, CORE.Product, "품목 형태")
    # HS code: HS 명명법 계층(4자리 헤딩 / 6자리 소호 / 8·10자리 국가세분)
    # 2026-07-09 교정: 실 카탈로그 SHACL 검증에서 4자리 헤딩(8541 등) 거부가 드러나 계층 수용으로 정정
    prop_shape(g, product, CORE.hsCode, name="HS코드", datatype=XSD.string,
               pattern=r"^([0-9]{4}|[0-9]{6}|[0-9]{8}|[0-9]{10})$",
               message="HS코드는 4(헤딩)·6(소호)·8·10자리 숫자.")

    # 공통 시간/신뢰도 값범위, TemporalScope·confidence
    tscope = node_shape(g, SHAPES.TemporalScopeShape, CORE.TemporalScope, "시간범위 형태")
    prop_shape(g, tscope, CORE.validFrom, name="유효시작", datatype=XSD.date, max_count=1)
    prop_shape(g, tscope, CORE.validTo, name="유효종료", datatype=XSD.date, max_count=1)

    # -------------------------------------------------------------------
    # INTL, Sanction / ExportControl / OwnershipPath / GeopoliticalEvent
    # -------------------------------------------------------------------
    sanction = node_shape(g, SHAPES.SanctionShape, INTL.Sanction, "제재 형태")
    prop_shape(g, sanction, INTL.sanctionDate, name="제재일",
               datatype=XSD.date, max_count=1,
               message="제재일은 xsd:date, 최대 1개.")
    prop_shape(g, sanction, INTL.listsEntity, name="제재등재",
               cls=INTL.SanctionedEntity,
               message="제재 등재 대상은 SanctionedEntity.")

    expctl = node_shape(g, SHAPES.ExportControlShape, INTL.ExportControl, "수출통제 형태")
    prop_shape(g, expctl, INTL.controlScope, name="통제범위",
               datatype=XSD.string, max_count=1)

    geoev = node_shape(g, SHAPES.GeopoliticalEventShape,
                       INTL.GeopoliticalEvent, "지정학사건 형태")
    prop_shape(g, geoev, INTL.eventDate, name="사건일",
               datatype=XSD.date, min_count=1, max_count=1,
               message="지정학 사건은 사건일 정확히 1개.")

    owns_path = node_shape(g, SHAPES.OwnershipPathShape,
                           INTL.OwnershipPath, "소유경로 형태")
    # circumvents 추론 기반: 시작=제재대상, 끝=조직, 둘 다 정확히 1
    prop_shape(g, owns_path, INTL.pathStart, name="경로시작",
               cls=INTL.SanctionedEntity, min_count=1, max_count=1,
               message="소유경로 시작은 SanctionedEntity 정확히 1개.")
    prop_shape(g, owns_path, INTL.pathEnd, name="경로끝",
               cls=CORE.Organization, min_count=1, max_count=1,
               message="소유경로 끝은 Organization 정확히 1개.")

    # 소유관계 진술. 지분율을 조직에 걸면 여러 지분관계에 참여한 조직에서 어느 쌍의
    # 값인지 알 수 없다. 관계 개체를 target 으로 삼아 양 끝점과 값을 함께 규정한다.
    own_a = node_shape(g, SHAPES.OwnershipAssertionShape,
                       INTL.OwnershipAssertion, "소유관계진술 형태")
    prop_shape(g, own_a, INTL.owner, name="소유자", cls=CORE.Organization,
               min_count=1, max_count=1,
               message="소유관계진술의 소유자는 Organization 정확히 1개.")
    prop_shape(g, own_a, INTL.ownedOrganization, name="피소유조직",
               cls=CORE.Organization, min_count=1, max_count=1,
               message="소유관계진술의 피소유조직은 Organization 정확히 1개.")
    prop_shape(g, own_a, INTL.ownershipPct, name="지분율",
               datatype=XSD.decimal, min_inclusive=0, max_inclusive=100, max_count=1,
               message="지분율은 0~100, 최대 1개.")

    # 제재 등재 사실. 등재 조직과 근거 조치가 없으면 등재 사실이 성립하지 않는다.
    listing = node_shape(g, SHAPES.SanctionListingShape,
                         INTL.SanctionListing, "제재등재사실 형태")
    prop_shape(g, listing, INTL.listedOrganization, name="등재조직",
               cls=CORE.Organization, min_count=1, max_count=1,
               message="등재 사실은 등재조직 정확히 1개.")
    ps_us = prop_shape(g, listing, INTL.underSanction, name="근거조치",
               min_count=1,
               message="등재 사실은 근거 조치(제재 또는 수출통제) 1개 이상.")
    or_classes(g, ps_us, [INTL.Sanction, INTL.ExportControl])
    prop_shape(g, listing, INTL.listAuthority, name="발령기관",
               cls=CORE.Organization, max_count=1,
               message="발령기관은 Organization, 최대 1개.")
    prop_shape(g, listing, CORE.source, name="출처", datatype=XSD.string,
               min_count=1, severity=SH.Warning,
               message="등재 사실은 출처 1개 이상 권고.")

    # 제재 조치의 정준 식별자. 프로그램 명칭은 개정·통합되므로 식별자가 필요하다.
    sanc_id = node_shape(g, SHAPES.SanctionIdShape, INTL.Sanction, "제재 식별 형태")
    prop_shape(g, sanc_id, CORE.canonicalId, name="정준 식별자",
               datatype=XSD.string, min_count=1, max_count=1,
               message="제재 조치는 정준 식별자 정확히 1개.")

    # 소스 커버리지도 동일하다.
    cov_id = node_shape(g, SHAPES.SourceCoverageIdShape,
                        CORE.SourceCoverage, "커버리지 식별 형태")
    prop_shape(g, cov_id, CORE.canonicalId, name="정준 식별자",
               datatype=XSD.string, min_count=1, max_count=1,
               message="소스 커버리지는 정준 식별자 정확히 1개.")

    # -------------------------------------------------------------------
    # GVC, SupplyEdge / TradeFlow / Dependency / PriceIndex / MarketShare
    # -------------------------------------------------------------------
    supedge = node_shape(g, SHAPES.SupplyEdgeShape, GVC.SupplyEdge, "공급관계 형태")
    prop_shape(g, supedge, GVC.supplier, name="공급자",
               cls=GVC.Company, min_count=1, max_count=1,
               message="공급관계는 공급자(Company) 정확히 1개.")
    prop_shape(g, supedge, GVC.customer, name="수요자",
               cls=GVC.Company, min_count=1, max_count=1,
               message="공급관계는 수요자(Company) 정확히 1개.")
    prop_shape(g, supedge, GVC.suppliesProduct, name="공급품목",
               cls=CORE.Product,
               message="공급품목 range 는 Product.")
    prop_shape(g, supedge, CORE.confidence, name="신뢰도",
               datatype=XSD.decimal, min_inclusive=0, max_inclusive=1,
               max_count=1,
               message="신뢰도는 0~1.")

    tflow = node_shape(g, SHAPES.TradeFlowShape, GVC.TradeFlow, "무역흐름 형태")
    prop_shape(g, tflow, GVC.flowOrigin, name="수출국",
               cls=CORE.Country, min_count=1, max_count=1,
               message="무역흐름 수출국은 Country 정확히 1개.")
    prop_shape(g, tflow, GVC.flowDestination, name="수입국",
               cls=CORE.Country, min_count=1, max_count=1,
               message="무역흐름 수입국은 Country 정확히 1개.")
    prop_shape(g, tflow, GVC.flowProduct, name="무역품목",
               cls=CORE.Product, min_count=1,
               message="무역흐름은 품목(Product) 1개 이상.")
    prop_shape(g, tflow, GVC.tradeValueUSD, name="무역액USD",
               datatype=XSD.decimal, min_inclusive=0, max_count=1,
               message="무역액은 0 이상.")
    prop_shape(g, tflow, GVC.tradeQuantity, name="무역수량",
               datatype=XSD.decimal, min_inclusive=0, max_count=1,
               message="무역수량은 0 이상.")

    dep = node_shape(g, SHAPES.DependencyShape, GVC.Dependency, "의존관계 형태")
    prop_shape(g, dep, GVC.dependentActor, name="의존주체",
               node_kind=SH.IRI, min_count=1,
               message="의존관계는 의존주체 1개 이상.")
    # HHI 척도는 0~1(점유율 제곱합). 0~10000 상한을 두면 만 배 단위 오류를
    # 잡지 못해 제약이 공허해진다.
    prop_shape(g, dep, GVC.hhi, name="HHI",
               datatype=XSD.decimal, min_inclusive=0, max_inclusive=1,
               max_count=1,
               message="HHI 는 0~1 (점유율 제곱합).")

    # SourceCoverage 를 target 하는 shape 가 없으면 커버리지 선언 자체가 기계
    # 검증 밖에 남는다. 시작·종료 순서 부등식은 SPARQL 제약이 필요해 v0.2.0
    # 으로 미루고, 존재·형·범위를 건다.
    cov = node_shape(g, SHAPES.SourceCoverageShape, CORE.SourceCoverage, "소스 커버리지 형태")
    prop_shape(g, cov, CORE.source, name="소스",
               min_count=1, max_count=1,
               message="커버리지 선언은 소스명 1개 필수.")
    prop_shape(g, cov, CORE.observedCount, name="관측수",
               datatype=XSD.integer, min_inclusive=0, min_count=1, max_count=1,
               message="관측수는 0 이상 정수 1개 필수(0도 관측된 부재).")
    prop_shape(g, cov, CORE.coverageStart, name="커버리지시작",
               datatype=XSD.gYear, max_count=1,
               message="커버리지 시작은 gYear 최대 1개(무시간 소스는 생략 가능).")
    prop_shape(g, cov, CORE.coverageEnd, name="커버리지종료",
               datatype=XSD.gYear, max_count=1,
               message="커버리지 종료는 gYear 최대 1개.")

    loc = node_shape(g, SHAPES.LocationShape, CORE.Location, "공간노드 형태")
    prop_shape(g, loc, CORE.wikidataQID, name="Wikidata QID",
               datatype=XSD.string, pattern=r"^Q[0-9]+$", max_count=1,
               message="공간노드 QID 는 Q+숫자 형식 최대 1개.")

    pidx = node_shape(g, SHAPES.PriceIndexShape, GVC.PriceIndex, "가격지수 형태")
    prop_shape(g, pidx, GVC.priceOf, name="가격대상",
               cls=CORE.Product, min_count=1,
               message="가격지수는 대상 품목 1개 이상.")
    prop_shape(g, pidx, GVC.indexValue, name="지수값",
               datatype=XSD.decimal, max_count=1)

    # 시장점유율 값범위 (Company 또는 SupplyEdge 에 부여 가능, Company 에 target)
    msh = node_shape(g, SHAPES.MarketShareShape, GVC.Company, "시장점유율 값범위")
    prop_shape(g, msh, GVC.marketShare, name="시장점유율",
               datatype=XSD.decimal, min_inclusive=0, max_inclusive=100,
               message="시장점유율은 0~100.")

    # -------------------------------------------------------------------
    # BRIDGE, 5관계 도메인/레인지/카디널리티/값범위
    #   Bridge 는 엣지 자체에 거는 제약이므로, 각 도메인 클래스를 target 으로
    #   sh:property(path=bridge 관계) 의 sh:class(range) 를 검증.
    # -------------------------------------------------------------------
    # affects: domain=SanctionedEntity, range=Company ∪ SupplyEdge
    aff = node_shape(g, SHAPES.AffectsShape, INTL.SanctionedEntity, "affects 제약")
    aff_ps = prop_shape(g, aff, BR.affects, name="affects",
                        message="affects 의 range 는 Company 또는 SupplyEdge.")
    or_classes(g, aff_ps, [GVC.Company, GVC.SupplyEdge])

    # disrupts: domain=GeopoliticalEvent, range=TradeFlow
    dis = node_shape(g, SHAPES.DisruptsShape, INTL.GeopoliticalEvent, "disrupts 제약")
    prop_shape(g, dis, BR.disrupts, name="disrupts", cls=GVC.TradeFlow,
               message="disrupts 의 range 는 TradeFlow.")

    # restricts: domain=ExportControl, range=Product
    res = node_shape(g, SHAPES.RestrictsShape, INTL.ExportControl, "restricts 제약")
    prop_shape(g, res, BR.restricts, name="restricts", cls=CORE.Product,
               message="restricts 의 range 는 Product.")

    # circumvents: domain=OwnershipPath, range=Sanction
    cir = node_shape(g, SHAPES.CircumventsShape, INTL.OwnershipPath, "circumvents 제약")
    cir_ps = prop_shape(g, cir, BR.circumvents, name="circumvents",
                        cls=INTL.Sanction, min_count=1,
                        message="circumvents 의 range 는 Sanction, 1개 이상.")
    # 우회 의심도·hop 값범위 (OwnershipPath 노드에)
    # [P3] hops 는 circumvents 추론의 핵심 신호(OWNS*1-3) → minCount 1 로 필수화.
    prop_shape(g, cir, BR.hops, name="경로길이",
               datatype=XSD.integer, min_count=1, min_inclusive=1, max_inclusive=3,
               message="circumvents 소유경로 hop 은 1~3 (필수).")
    prop_shape(g, cir, BR.suspicion, name="의심도",
               datatype=XSD.decimal, min_inclusive=0, max_inclusive=1,
               message="circumvents 의심도는 0~1.")

    # exposes: domain=Dependency, range=RiskNode
    exp = node_shape(g, SHAPES.ExposesShape, GVC.Dependency, "exposes 제약")
    prop_shape(g, exp, BR.exposes, name="exposes", cls=GVC.RiskNode,
               message="exposes 의 range 는 RiskNode.")
    prop_shape(g, exp, BR.geoRisk, name="지정학위험",
               datatype=XSD.decimal, min_inclusive=0,
               message="지정학위험은 0 이상.")

    # Bridge 공통 위험 점수 값범위 (riskScore 0~1), SanctionedEntity 도메인에 부착
    prop_shape(g, aff, BR.riskScore, name="위험점수",
               datatype=XSD.decimal, min_inclusive=0, max_inclusive=1,
               max_count=1,
               message="riskScore 는 0~1.")


def main():
    out_dir = Path(__file__).resolve().parent
    g = new_graph()
    build_shapes(g)

    # 영어 메시지 병기(릴리스 기본 언어). 제3자가 위반 메시지를 읽을 수 있어야 한다.
    from comments_en import MESSAGES_EN
    unmatched = set()
    for s, o in list(g.subject_objects(SH.message)):
        if getattr(o, "language", None) == "ko":
            en = MESSAGES_EN.get(str(o))
            if en:
                g.add((s, SH.message, Literal(en, lang="en")))
            else:
                unmatched.add(str(o)[:40])
    if unmatched:
        print(f"경고: 영어 메시지 미대응 {len(unmatched)}건")
        for u in sorted(unmatched)[:5]:
            print("   ", u)

    out = out_dir / "shapes.ttl"
    g.serialize(destination=str(out), format="turtle")

    n_node = len(set(g.subjects(RDF.type, SH.NodeShape)))
    n_prop = len(list(g.subject_objects(SH.property)))
    print(f"[shapes.ttl] triples={len(g)}  node_shapes={n_node}  "
          f"property_shapes={n_prop}")
    print(f"saved -> {out}")
    return g


if __name__ == "__main__":
    main()
