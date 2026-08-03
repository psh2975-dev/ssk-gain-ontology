# -*- coding: utf-8 -*-
"""
반도체 공급사슬 지정학 교차도메인 온톨로지 생성기

NRF-2024S1A3A2A07046144 | 동아대학교 경영정보학과 | 박성호

단일 공유 온톨로지(분리 구축 금지)를 rdflib로 프로그래밍 생성한다.
모듈은 네임스페이스로 구분하되 하나의 온톨로지 안에서 owl:imports로 결합한다.

  core   : 공유 상위 클래스 · LEI(GLEIF) 식별 · 시공간(valid_time, ISO)
  intl   : 국제관계 도메인 (owl:imports core)
  gvc    : 반도체 소부장 GVC 도메인 (owl:imports core)
  bridge : 교차도메인 5관계 affects·disrupts·restricts·circumvents·exposes
           (owl:imports intl + gvc)

출력:
  core.ttl · intl.ttl · gvc.ttl · bridge.ttl , 모듈별 문서(소비자가 필요한
    모듈만 가져가 owl:imports 로 의존 문서를 따라갈 수 있게 한다)
  ontology.ttl , 4모듈을 하나로 합친 단일 TTL (전체 어휘용 표준 export)

의존성: rdflib (설치: python -m pip install rdflib)
실행: $env:PYTHONUTF8=1; python build_ontology.py
"""

from __future__ import annotations

# 콘솔 인코딩 방어. 윈도 기본 콘솔(cp949 등)에서는 비ASCII 문자를 출력할 때
# UnicodeEncodeError 로 죽는다. 표준 출력만 UTF-8 로 재설정한다.
import sys as _sys
if hasattr(_sys.stdout, "reconfigure"):
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from pathlib import Path

from rdflib import Graph, Namespace, Literal, BNode, URIRef
from rdflib.namespace import RDF, RDFS, OWL, XSD, DCTERMS, SKOS

# ---------------------------------------------------------------------------
# 네임스페이스, 단일 온톨로지 base + 4 모듈
# ---------------------------------------------------------------------------
BASE = "https://w3id.org/ssk-gain/ontology/"
SSK = Namespace(BASE)                 # 온톨로지 메타 / 공통 어노테이션
CORE = Namespace(BASE + "core#")      # 공유 상위·LEI·시공간
INTL = Namespace(BASE + "intl#")      # 국제관계
GVC = Namespace(BASE + "gvc#")        # 소부장 GVC
BR = Namespace(BASE + "bridge#")      # 교차 5관계
TIME = Namespace("http://www.w3.org/2006/time#")   # OWL-Time 재사용
PROV = Namespace("http://www.w3.org/ns/prov#")     # PROV-O 재사용
ORG = Namespace("http://www.w3.org/ns/org#")       # W3C Org 재사용

VERSION = "0.1.7"   # 2026-08-03: 재심사 대응 — 중복 식별자 검사, 사례 서지 공식화(공리 불변)
# 릴리스 날짜는 고정한다. 실행일을 쓰면 재생성물이 날마다 달라져
# 체크섬으로 기탁물을 검증할 수 없다.
TODAY = "2026-08-03"

# 모듈 온톨로지 IRI (owl:imports 대상)
ONT = URIRef(BASE.rstrip("/"))                     # 통합 온톨로지
ONT_CORE = URIRef(BASE + "core")
ONT_INTL = URIRef(BASE + "intl")
ONT_GVC = URIRef(BASE + "gvc")
ONT_BRIDGE = URIRef(BASE + "bridge")


def new_graph() -> Graph:
    g = Graph()
    g.bind("ssk", SSK)
    g.bind("core", CORE)
    g.bind("intl", INTL)
    g.bind("gvc", GVC)
    g.bind("bridge", BR)
    g.bind("owl", OWL)
    g.bind("rdfs", RDFS)
    g.bind("rdf", RDF)
    g.bind("xsd", XSD)
    g.bind("dcterms", DCTERMS)
    g.bind("skos", SKOS)
    g.bind("time", TIME)
    g.bind("prov", PROV)
    g.bind("org", ORG)
    return g


# ---------------------------------------------------------------------------
# 헬퍼
# ---------------------------------------------------------------------------
def cls(g, uri, label_ko, label_en, parent=None, comment=None, defined_by=None):
    g.add((uri, RDF.type, OWL.Class))
    g.add((uri, RDFS.label, Literal(label_ko, lang="ko")))
    g.add((uri, RDFS.label, Literal(label_en, lang="en")))
    if parent is not None:
        g.add((uri, RDFS.subClassOf, parent))
    if comment:
        g.add((uri, RDFS.comment, Literal(comment, lang="ko")))
    if defined_by is not None:
        g.add((uri, RDFS.isDefinedBy, defined_by))
    return uri


def obj_prop(g, uri, label_ko, label_en, domain=None, rng=None,
             comment=None, parent=None, defined_by=None,
             inverse=None, characteristics=None):
    g.add((uri, RDF.type, OWL.ObjectProperty))
    g.add((uri, RDFS.label, Literal(label_ko, lang="ko")))
    g.add((uri, RDFS.label, Literal(label_en, lang="en")))
    if domain is not None:
        g.add((uri, RDFS.domain, domain))
    if rng is not None:
        g.add((uri, RDFS.range, rng))
    if comment:
        g.add((uri, RDFS.comment, Literal(comment, lang="ko")))
    if parent is not None:
        g.add((uri, RDFS.subPropertyOf, parent))
    if defined_by is not None:
        g.add((uri, RDFS.isDefinedBy, defined_by))
    if inverse is not None:
        g.add((uri, OWL.inverseOf, inverse))
    for ch in (characteristics or []):
        g.add((uri, RDF.type, ch))
    return uri


def data_prop(g, uri, label_ko, label_en, domain=None, rng=None,
              comment=None, parent=None, defined_by=None, functional=False,
              inverse_functional=False):
    g.add((uri, RDF.type, OWL.DatatypeProperty))
    if functional:
        g.add((uri, RDF.type, OWL.FunctionalProperty))
    # 함수적은 "한 개체는 이 값을 최대 하나 갖는다"이고, 역함수적은 "한 값은 최대
    # 하나의 개체에 속한다"이다. 정준 식별자로서 동일성을 결정하는 것은 후자다.
    if inverse_functional:
        g.add((uri, RDF.type, OWL.InverseFunctionalProperty))
    g.add((uri, RDFS.label, Literal(label_ko, lang="ko")))
    g.add((uri, RDFS.label, Literal(label_en, lang="en")))
    if domain is not None:
        g.add((uri, RDFS.domain, domain))
    if rng is not None:
        g.add((uri, RDFS.range, rng))
    if comment:
        g.add((uri, RDFS.comment, Literal(comment, lang="ko")))
    if parent is not None:
        g.add((uri, RDFS.subPropertyOf, parent))
    if defined_by is not None:
        g.add((uri, RDFS.isDefinedBy, defined_by))
    return uri



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

def union_of(g, members):
    """owl:unionOf RDF 리스트를 익명 클래스로 생성하여 반환."""
    node = bnode()
    g.add((node, RDF.type, OWL.Class))
    g.add((node, OWL.unionOf, rdf_list(g, members)))
    return node


# ===========================================================================
# 1) CORE 모듈, 공유 상위 클래스 · LEI · 시공간
# ===========================================================================
def build_core(g: Graph):
    g.add((ONT_CORE, RDF.type, OWL.Ontology))
    g.add((ONT_CORE, DCTERMS.title,
           Literal("SSK 온톨로지: core 모듈 (공유 상위·LEI·시공간)", lang="ko")))
    g.add((ONT_CORE, OWL.versionInfo, Literal(VERSION)))
    g.add((ONT_CORE, DCTERMS.created, Literal(TODAY, datatype=XSD.date)))

    d = ONT_CORE

    # --- 최상위 ---
    Entity = cls(g, CORE.Entity, "엔티티", "Entity", OWL.Thing,
                 "KG의 모든 1급 개체의 최상위 클래스.", d)

    # --- 시공간 / 식별 보조 클래스 ---
    cls(g, CORE.TemporalScope, "시간범위", "TemporalScope", Entity,
        "valid_time(시작·종료) 등 시간 유효구간을 표현하는 reification 노드.", d)
    # Identifier 는 아래 「식별자 재화」 블록에서 정의한다(v0.1.5 의 값 객체 선언을
    # 동일성 축 설명이 있는 정의로 통합, 중복 선언 제거).

    # --- 공유 1급 엔티티 (도메인 모듈이 세분) ---
    Org = cls(g, CORE.Organization, "조직", "Organization", Entity,
              "법인·기업·기관. 정준 식별자는 LEI(GLEIF, ISO 17442)를 우선한다. LEI 미보유 법인은 관할과 등록번호의 결합을 쓰며, 둘 다 없으면 큐레이션 키를 잠정 식별자로 둔다(core:identifierStatus 로 표시). 이름은 동일성 기준이 아니다.", d)
    Country = cls(g, CORE.Country, "국가", "Country", Entity,
                  "주권국가. canonical_id = ISO 3166-1 alpha-3.", d)
    Product = cls(g, CORE.Product, "품목", "Product", Entity,
                  "교역·통제 대상 품목. canonical_id = HS code(6자리), fallback ECCN.", d)
    Event = cls(g, CORE.Event, "사건", "Event", Entity,
                "시점·기간을 갖는 사건. 국제관계 모듈이 GeopoliticalEvent로 세분.", d)
    Policy = cls(g, CORE.Policy, "정책", "Policy", Entity,
                 "정부·국제기구의 법령·조치. 국제관계 모듈이 세분.", d)
    cls(g, CORE.Location, "지점", "Location", Entity,
        "지리적 위치(시설·항만·좌표). GIS 공간조인 기반.", d)
    # GVC 상위(소부장)도 core 에 둔다, 공유 어휘(Bridge·LEI 조인)가 참조하기 때문.
    cls(g, CORE.Component, "부품", "Component", Product,
        "반도체 부품·메모리 등 (HS 8541·8542). Product의 하위.", d)
    cls(g, CORE.Material, "소재", "Material", Product,
        "반도체 소재 (HS 2804·2811·3707). Product의 하위.", d)
    cls(g, CORE.Equipment, "장비", "Equipment", Product,
        "반도체 제조장비 (HS 8486). Product의 하위.", d)

    # 동일성 기준은 역함수적 속성으로 선언한다(위 lei·isoAlpha3·hsCode).
    # owl:hasKey 도 같은 목적의 OWL 2 구문이나 채택하지 않았다. 실측 결과 owlrl 의
    # hasKey 구현이 키 값을 대조하지 않고 같은 클래스의 개체를 무조건 동일시해,
    # 서로 다른 LEI 를 가진 조직까지 sameAs 로 추론했다(validate.py [1d] 로 확인).
    # 역함수적 속성은 같은 조건에서 정확히 동작한다. 식별자 표준(ISO 17442·3166-1·HS)
    # 자체가 값의 전역 유일성을 보증하므로 클래스 범위 한정도 필요하지 않다.

    # 최상위 6유형 상호배타 분할. 조치(Policy)·발생(Event)·장소(Location)는
    # 개체(Organization·Country·Product)와 존재론적 범주가 다르다. 이 분리가
    # 없으면 조치와 그 대상을 혼동한 오분류가 검사를 그대로 통과한다.
    identified = [Org, Country, Product]        # 정준 식별자를 갖는 개체
    occurrent = [Policy, Event]                  # 조치·발생
    for i, a in enumerate(identified):
        for b in identified[i + 1:]:
            g.add((a, OWL.disjointWith, b))
    for a in occurrent:
        for b in identified:
            g.add((a, OWL.disjointWith, b))
    g.add((Policy, OWL.disjointWith, Event))
    for b in identified + occurrent:
        g.add((CORE.Location, OWL.disjointWith, b))

    # --- 식별 데이터 속성 (canonical_id) ---
    # 편의 조회용 데이터 속성. 함수적이기만 하다. 동일성을 결정하는 역함수성은
    # 아래 core:hasIdentifier 가 진다. 데이터 속성에 역함수성을 붙이면 OWL 2 DL
    # 밖으로 나가기 때문이다(구문 명세 9.3절에 그런 공리가 없다).
    data_prop(g, CORE.lei, "LEI", "lei", Org, XSD.string,
              "GLEIF Legal Entity Identifier (ISO 17442, 20자). 기업 canonical_id.",
              defined_by=d, functional=True)
    data_prop(g, CORE.isoAlpha3, "ISO3166-1 alpha-3", "isoAlpha3", Country, XSD.string,
              "국가 ISO 3166-1 alpha-3 코드(KOR·USA·CHN·JPN·NLD). canonical_id.",
              defined_by=d, functional=True)
    data_prop(g, CORE.hsCode, "HS코드", "hsCode", Product, XSD.string,
              "WCO HS code. 품목 canonical_id(6자리), 정밀은 HS10.",
              defined_by=d, functional=True)
    data_prop(g, CORE.eccn, "ECCN", "eccn", Product, XSD.string,
              "수출통제 분류번호(ECCN). HS의 통제 측 fallback 식별자.", defined_by=d)
    data_prop(g, CORE.wikidataQID, "Wikidata QID", "wikidataQID", Entity, XSD.string,
              "Wikidata QID. LEI 미매칭 시 기업 fallback 식별자.", defined_by=d)
    data_prop(g, CORE.canonicalId, "정규식별자", "canonicalId", Entity, XSD.string,
              "엔티티 정규 식별자(접점 명세 canonical_id 규칙의 일반 슬롯).",
              defined_by=d)
    data_prop(g, CORE.label, "명칭", "name", Entity, XSD.string,
              "엔티티 표기명(추출 원문 표면형 포함).", defined_by=d)
    data_prop(g, CORE.alternateId, "별칭식별자", "alternateId",
              CORE.Entity, XSD.string,
              "정준 식별자가 아닌 보조 식별자. 병합 이전의 소스 키를 보존해 추적을 "
              "가능하게 하되, 동일성 판단에는 쓰지 않는다.", defined_by=d)
    data_prop(g, CORE.identifierStatus, "식별자상태", "identifierStatus",
              CORE.Entity, XSD.string,
              "정준 식별자의 근거. authoritative=표준 등록부(LEI·ISO·HS), provisional=큐레이션 키(표준 식별자 미보유).", defined_by=d)

    # --- 식별자 재화 (동일성 추론의 DL 적합 경로) ---
    # 표준 등록부의 식별자를 개체로 세운다. 한 식별자 개체는 최대 하나의 엔티티에
    # 속하므로(역함수적), 두 출처가 같은 식별자를 가리키면 같은 엔티티라는 추론이
    # OWL 2 DL 안에서 성립한다. 식별자 개체는 (체계, 값)에서 결정론적으로 주조해야
    # 서로 다른 출처가 같은 개체에 닿는다. 주조 규칙은 적재기에 있다.
    Identifier = cls(g, CORE.Identifier, "식별자", "Identifier", Entity,
                     "표준 등록부가 발급한 식별자. 값이 아니라 개체로 세워, 동일성 "
                     "추론이 데이터 속성이 아닌 객체 속성 위에서 이루어지게 한다.",
                     defined_by=d)
    obj_prop(g, CORE.hasIdentifier, "식별자보유", "hasIdentifier", Entity, Identifier,
             "엔티티가 보유한 표준 식별자. 역함수적이므로 같은 식별자 개체를 가리키는 "
             "두 엔티티는 동일하다. 이 축이 교차 도메인 결합의 논리적 근거다.",
             defined_by=d, characteristics=[OWL.InverseFunctionalProperty])
    data_prop(g, CORE.identifierScheme, "식별체계", "identifierScheme",
              Identifier, XSD.string,
              "식별자를 발급한 등록 체계(LEI·ISO3166-1-alpha-3·HS·Wikidata).",
              defined_by=d, functional=True)
    data_prop(g, CORE.identifierValue, "식별자값", "identifierValue",
              Identifier, XSD.string,
              "식별자의 문자열 값. 체계와 값의 쌍이 식별자 개체를 결정한다.",
              defined_by=d, functional=True)
    data_prop(g, CORE.registrationStatus, "등록상태", "registrationStatus",
              Identifier, XSD.string,
              "발급 등록부가 보고하는 등록 상태(ISSUED·LAPSED·RETIRED 등). 제재 대상 "
              "기업에서 실효 등록이 흔하므로, 식별자의 현재성을 값과 분리해 기록한다.",
              defined_by=d)

    # --- 데이터 레코드 계층 (출처는 대상이 아니라 레코드에 붙는다) ---
    # 국가나 기업 자체가 데이터셋에서 생성되지는 않는다. 생성된 것은 그 대상에
    # 관한 레코드다. PROV-O 어휘는 이 레코드에 부착한다.
    Record = cls(g, CORE.Record, "자료레코드", "Record", Entity,
                 "어떤 도메인 대상에 관해 한 출처가 남긴 자료 레코드. 수집일·출처·"
                 "등급·라이선스와 PROV 계보가 여기에 붙는다.", defined_by=d)
    obj_prop(g, CORE.recordOf, "레코드대상", "recordOf", Record, Entity,
             "이 레코드가 진술하는 도메인 대상.", defined_by=d)

    # --- 시공간 데이터 속성 (valid_time) ---
    data_prop(g, CORE.validFrom, "유효시작", "validFrom", None, XSD.date,
              "valid_time 시작일. 모든 노드/엣지 시점 정합에 사용.", defined_by=d)
    data_prop(g, CORE.validTo, "유효종료", "validTo", None, XSD.date,
              "valid_time 종료일.", defined_by=d)
    data_prop(g, CORE.startYear, "시작연도", "startYear", None, XSD.gYear,
              "관계 시작 연도(공급·계약 등 시간 어휘).", defined_by=d)
    data_prop(g, CORE.endYear, "종료연도", "endYear", None, XSD.gYear,
              "관계 종료 연도.", defined_by=d)

    # --- 출처·신뢰도·재현성 메타 (provenance / B2·C 원칙) ---
    data_prop(g, CORE.confidence, "신뢰도", "confidence", None, XSD.decimal,
              "추출 트리플 confidence(0~1). 0.7 미만 제거 기준.", defined_by=d)
    data_prop(g, CORE.source, "출처", "source", None, XSD.string,
              "데이터 출처(소스명). provenance 태그.", defined_by=d)
    data_prop(g, CORE.tier, "공식성등급", "tier", None, XSD.string,
              "공식성 4-Tier(T1~T4).", defined_by=d)
    data_prop(g, CORE.evidenceType, "근거유형", "evidenceType", None, XSD.string,
              "관측(observed) vs 추론(inferred) 구분, 불확실성 태그.", defined_by=d)
    data_prop(g, CORE.collectedDate, "수집일", "collectedDate", None, XSD.date,
              "데이터 수집일. 재현성·계보 태그.", defined_by=d)

    # --- 공유 지리·시간 객체 속성 ---
    obj_prop(g, CORE.hasTemporalScope, "시간범위가짐", "hasTemporalScope",
             Entity, CORE.TemporalScope,
             "엔티티/관계의 유효 시간범위 연결.", defined_by=d)

    # 대칭 속성이므로 domain·range 를 Event ∪ Policy 합집합으로 두어 방향과
    # 무관하게 성립시킨다. 인과 함의는 없으며 관측 가능한 연관만 표현한다.
    _ev_pol = union_of(g, [CORE.Event, CORE.Policy])
    obj_prop(g, CORE.associatedWith, "연관", "associatedWith",
             _ev_pol, _ev_pol,
             "지정학 이벤트와 정책(제재·수출통제·무역조치)의 문서화된 연관. "
             "무방향(대칭). 인과 불포함(인과 추정은 별도 분석의 몫). 예: 정책 이벤트와 그에 수반된 제재의 연결.",
             defined_by=d, characteristics=[OWL.SymmetricProperty])

    # --- 소스 커버리지 선언 ---
    # 수집 대상 기간과 그 기간의 실제 관측 수를 함께 선언해, 윈도 내의 희박을
    # 결측이 아니라 관측된 부재로 구분할 수 있게 한다.
    Coverage = cls(g, CORE.SourceCoverage, "소스커버리지", "SourceCoverage", Entity,
                   "한 데이터 소스의 수집 대상 기간과 관측 밀도를 선언하는 reification 노드. "
                   "수집 윈도 내 희박은 결측이 아니라 관측된 부재를 뜻한다.", d)
    data_prop(g, CORE.coverageStart, "커버리지시작", "coverageStart", Coverage, XSD.gYear,
              "이 소스의 수집 대상 기간 시작 연도. 연구 기간 설계(2008~)와 정합.", defined_by=d)
    data_prop(g, CORE.coverageEnd, "커버리지종료", "coverageEnd", Coverage, XSD.gYear,
              "이 소스의 수집 대상 기간 종료 연도(2025).", defined_by=d)
    data_prop(g, CORE.observedCount, "관측수", "observedCount", Coverage, XSD.integer,
              "커버리지 기간에 실제 관측된 레코드 수. 0 또는 소수여도 결측이 아닌 관측된 부재.",
              defined_by=d)
    obj_prop(g, CORE.declaresCoverage, "커버리지선언", "declaresCoverage",
             Entity, Coverage,
             "데이터셋/모듈이 소스별 커버리지 선언을 갖는다.", defined_by=d)


# ===========================================================================
# 2) INTL 모듈, 국제관계 (owl:imports core)
# ===========================================================================
def build_intl(g: Graph):
    g.add((ONT_INTL, RDF.type, OWL.Ontology))
    g.add((ONT_INTL, DCTERMS.title,
           Literal("SSK 온톨로지: intl 모듈 (국제관계)", lang="ko")))
    g.add((ONT_INTL, OWL.versionInfo, Literal(VERSION)))
    g.add((ONT_INTL, OWL.imports, ONT_CORE))

    d = ONT_INTL

    # --- 클래스 계층: Organization·Country·Event·Policy 세분 ---
    SanctionedEntity = cls(
        g, INTL.SanctionedEntity, "제재대상", "SanctionedEntity",
        CORE.Organization,
        "제재·통제 리스트에 등재된 조직(OFAC SDN·BIS Entity·중국 UEL 등). "
        "core:Organization 의 하위, 같은 LEI 노드로 GVC 행위자와 통합. "
        "등재는 해제 가능한 상태이므로 이 분류는 현행 등재 조회용 파생 분류이며, "
        "등재 사실 자체는 intl:SanctionListing 이 담는다.", d)

    # 등재를 진술 개체로 분리한다. 등재는 조직의 본질이 아니라 특정 목록에 특정
    # 기간 성립하는 상태다(OntoClean 반강성). 정적 하위 클래스로만 두면 해제·복수
    # 목록 등재·목록별 근거·효력기간을 표현할 수단이 없다.
    SanctionListing = cls(
        g, INTL.SanctionListing, "제재등재사실", "SanctionListing", CORE.Entity,
        "특정 제재 목록에 특정 기간 등재된 사실. 등재 조직·근거 조치·발령 기관·"
        "효력기간·출처를 함께 담는다.", d)

    GeoEvent = cls(g, INTL.GeopoliticalEvent, "지정학사건", "GeopoliticalEvent",
                   CORE.Event,
                   "분쟁·관세·정책 변화 등 지정학적 사건. disrupts 의 주체.", d)

    # 정책 계층
    Policy = CORE.Policy
    ExportControl = cls(g, INTL.ExportControl, "수출통제", "ExportControl", Policy,
                        "수출통제 조치(BIS·중국 양용물품·일본 수출규제). restricts 의 주체.", d)
    Sanction = cls(g, INTL.Sanction, "제재", "Sanction", Policy,
                   "제재 조치(금융·투자·기술이전). circumvents 의 대상.", d)
    cls(g, INTL.FinancialSanction, "금융제재", "FinancialSanction", Sanction,
        "자금·거래 동결 등 금융제재.", d)
    cls(g, INTL.TechTransferBan, "기술이전금지", "TechTransferBan", Sanction,
        "기술·지식 이전 금지.", d)
    cls(g, INTL.InvestmentRestriction, "투자제한", "InvestmentRestriction", Sanction,
        "지분투자·인수 제한.", d)

    # 국제관계 보조 엔티티
    # 지분율은 두 조직 사이 관계의 속성이지 어느 한 조직의 속성이 아니다.
    # 한 조직이 여러 지분관계에 참여하면 어느 쌍의 지분율인지 알 수 없다.
    OwnershipAssertion = cls(
        g, INTL.OwnershipAssertion, "소유관계진술", "OwnershipAssertion", CORE.Entity,
        "두 조직 사이의 지분 소유 관계를 개체로 재화한 것. 지분율·유효기간·출처를 "
        "이 개체에 부여한다.", d)

    OwnershipPath = cls(
        g, INTL.OwnershipPath, "소유경로", "OwnershipPath", CORE.Entity,
        "제재대상→(OWNS*1-3)→비제재 법인으로 이어지는 소유 연쇄. "
        "circumvents 의 주체(우회 의심 경로 reification).", d)
    TradeMeasure = cls(g, INTL.TradeMeasure, "무역조치", "TradeMeasure", Policy,
                       "무역정책 개입(GTA·WTO 반덤핑·상계관세·NTM).", d)

    # --- 공급/제재/지리/기업 객체 속성 (국제관계 측) ---
    # 제재 어휘
    obj_prop(g, INTL.exportControlledBy, "수출통제대상", "exportControlledBy",
             CORE.Product, INTL.ExportControl,
             "품목이 수출통제 조치의 대상임.", defined_by=d)
    obj_prop(g, INTL.financiallySanctions, "금융제재함", "financiallySanctions",
             INTL.FinancialSanction, CORE.Organization,
             "금융제재가 조직을 대상으로 함.", defined_by=d)
    obj_prop(g, INTL.bansTechTransferTo, "기술이전금지대상", "bansTechTransferTo",
             INTL.TechTransferBan, CORE.Organization,
             "기술이전금지가 적용되는 조직.", defined_by=d)
    obj_prop(g, INTL.restrictsInvestmentIn, "투자제한대상", "restrictsInvestmentIn",
             INTL.InvestmentRestriction, CORE.Organization,
             "투자제한이 적용되는 조직.", defined_by=d)
    obj_prop(g, INTL.listsEntity, "제재등재", "listsEntity",
             INTL.Sanction, INTL.SanctionedEntity,
             "제재 조치가 제재대상을 등재함.", defined_by=d)

    # SanctionListing 연결
    obj_prop(g, INTL.listedOrganization, "등재조직", "listedOrganization",
             INTL.SanctionListing, CORE.Organization,
             "등재 사실이 가리키는 조직.", defined_by=d)
    # 치역을 Sanction 으로 한정하면 수출통제 등재(BIS Entity List 의 SMIC 등재가
    # 실사례)가 표현되지 않는다. 등재의 근거는 금융제재이거나 수출통제다. 공통
    # 상위클래스 신설은 용어 검증이 필요하므로 v0.2.0 으로 미루고 합집합으로 둔다.
    obj_prop(g, INTL.underSanction, "근거조치", "underSanction",
             INTL.SanctionListing, union_of(g, [INTL.Sanction, INTL.ExportControl]),
             "등재의 근거가 되는 조치(금융제재 또는 수출통제).", defined_by=d)
    obj_prop(g, INTL.listAuthority, "발령기관", "listAuthority",
             INTL.SanctionListing, CORE.Organization,
             "등재를 발령한 기관 또는 목록 관할.", defined_by=d)

    # OwnershipAssertion 연결
    obj_prop(g, INTL.owner, "소유자", "owner",
             INTL.OwnershipAssertion, CORE.Organization,
             "지분을 보유한 조직.", defined_by=d)
    obj_prop(g, INTL.ownedOrganization, "피소유조직", "ownedOrganization",
             INTL.OwnershipAssertion, CORE.Organization,
             "지분이 보유된 조직.", defined_by=d)

    # 지리 어휘
    obj_prop(g, INTL.headquarteredIn, "본사위치", "headquarteredIn",
             CORE.Organization, CORE.Country,
             "조직의 본사 소재 국가(지리: 본사위치).", defined_by=d)
    obj_prop(g, INTL.incorporatedIn, "법인설립국", "incorporatedIn",
             CORE.Organization, CORE.Country,
             "조직의 법인 설립국(지리: 법인설립국).", defined_by=d)
    obj_prop(g, INTL.hasProductionFacility, "생산시설", "hasProductionFacility",
             CORE.Organization, CORE.Location,
             "조직의 생산시설 위치(지리: 생산시설).", defined_by=d)

    # 기업 구조 어휘
    obj_prop(g, INTL.subsidiaryOf, "자회사", "subsidiaryOf",
             CORE.Organization, CORE.Organization,
             "자회사 관계(기업: 자회사). GLEIF L2·ICIJ 소유구조. "
             "이행적이되 이는 지배 관계의 이행성이며 지분율의 이행성이 아니다. "
             "합산 지분 판정은 소유관계진술의 지분율로 별도 계산한다. "
             "비반사적: 법인은 자기 자신의 자회사가 아니다.",
             defined_by=d,
             characteristics=[OWL.TransitiveProperty, OWL.IrreflexiveProperty])
    obj_prop(g, INTL.owns, "소유", "owns",
             CORE.Organization, CORE.Organization,
             "지분 소유(OWNS). 소유경로(circumvents)의 기반 엣지. "
             "비반사적: 법인은 자기 자신을 소유하지 않는다.",
             defined_by=d, inverse=INTL.ownedBy,
             characteristics=[OWL.IrreflexiveProperty])
    obj_prop(g, INTL.ownedBy, "피소유", "ownedBy",
             CORE.Organization, CORE.Organization,
             "소유의 역관계.", defined_by=d)
    obj_prop(g, INTL.jointVentureWith, "합작법인", "jointVentureWith",
             CORE.Organization, CORE.Organization,
             "합작법인 관계(기업: 합작법인).",
             defined_by=d, characteristics=[OWL.SymmetricProperty])
    obj_prop(g, INTL.acquired, "인수합병", "acquired",
             CORE.Organization, CORE.Organization,
             "인수·합병(기업: 인수합병).", defined_by=d)
    obj_prop(g, INTL.strategicAllianceWith, "전략적제휴", "strategicAllianceWith",
             CORE.Organization, CORE.Organization,
             "전략적 제휴(기업: 전략적제휴).",
             defined_by=d, characteristics=[OWL.SymmetricProperty])

    # 조치 연결
    obj_prop(g, INTL.imposes, "조치부과", "imposes",
             CORE.Country, INTL.TradeMeasure,
             "국가가 무역조치를 부과함.", defined_by=d)
    obj_prop(g, INTL.enactedBy, "제정주체", "enactedBy",
             CORE.Policy, CORE.Country,
             "정책을 제정한 국가.", defined_by=d)

    # OwnershipPath reification 연결 (circumvents 추론 기반)
    obj_prop(g, INTL.pathStart, "경로시작", "pathStart",
             INTL.OwnershipPath, INTL.SanctionedEntity,
             "소유경로의 시작(제재대상).", defined_by=d)
    obj_prop(g, INTL.pathEnd, "경로끝", "pathEnd",
             INTL.OwnershipPath, CORE.Organization,
             "소유경로의 끝(비제재 법인).", defined_by=d)

    # 국제관계 데이터 속성
    data_prop(g, INTL.sanctionDate, "제재일", "sanctionDate",
              INTL.Sanction, XSD.date,
              "제재 발효일(valid_time 근사 기준).", defined_by=d)
    data_prop(g, INTL.controlScope, "통제범위", "controlScope",
              INTL.ExportControl, XSD.string,
              "수출통제 범위(품목군·국가 등).", defined_by=d)
    data_prop(g, INTL.eventDate, "사건일", "eventDate",
              INTL.GeopoliticalEvent, XSD.date,
              "지정학 사건 발생일.", defined_by=d)
    data_prop(g, INTL.ownershipPct, "지분율", "ownershipPct",
              INTL.OwnershipAssertion, XSD.decimal,
              "소유 지분율(%). 소유관계진술 개체의 속성이며 조직의 속성이 아니다.",
              defined_by=d)


# ===========================================================================
# 3) GVC 모듈, 반도체 소부장 글로벌 공급사슬 (owl:imports core)
# ===========================================================================
def build_gvc(g: Graph):
    g.add((ONT_GVC, RDF.type, OWL.Ontology))
    g.add((ONT_GVC, DCTERMS.title,
           Literal("SSK 온톨로지: gvc 모듈 (반도체 소부장 GVC)", lang="ko")))
    g.add((ONT_GVC, OWL.versionInfo, Literal(VERSION)))
    g.add((ONT_GVC, OWL.imports, ONT_CORE))

    d = ONT_GVC

    # 소부장 3 layer 는 core 에서 Product 하위로 정의됨(Material/Equipment/Component).
    # GVC 모듈은 공급사슬 관계·흐름·의존·위험 노드를 정의한다.

    Company = cls(g, GVC.Company, "기업", "Company", CORE.Organization,
                  "공급사슬 행위자로서의 기업(삼성·SK하이닉스·TSMC·ASML 등). "
                  "core:Organization 의 하위, 같은 LEI 로 intl:SanctionedEntity 와 통합.", d)

    SupplyEdge = cls(
        g, GVC.SupplyEdge, "공급관계", "SupplyEdge", CORE.Entity,
        "기업→기업 공급관계의 reification 노드(방향성·시점·신뢰도 보유). "
        "거래액은 공시 부재로 미부여(방향성·존재성만). affects 의 대상.", d)

    TradeFlow = cls(
        g, GVC.TradeFlow, "무역흐름", "TradeFlow", CORE.Entity,
        "국가→국가 품목별 무역 흐름(HS·금액·수량) reification 노드. "
        "Comtrade·BACI 기반. disrupts 의 대상.", d)

    Dependency = cls(
        g, GVC.Dependency, "의존관계", "Dependency", CORE.Entity,
        "특정 품목·공급원에 대한 의존(단일의존·고집중) reification. "
        "HHI 보유. exposes 의 주체.", d)

    RiskNode = cls(
        g, GVC.RiskNode, "위험노드", "RiskNode", CORE.Entity,
        "지정학·집중 위험이 결합되는 노출 대상(기업·품목·경로·지역). "
        "exposes 의 대상.", d)

    PriceIndex = cls(
        g, GVC.PriceIndex, "가격지수", "PriceIndex", CORE.Entity,
        "메모리 가격 시계열 지수(ECOS D램 수출물가지수 등).", d)

    cls(g, GVC.Input, "투입재", "Input", CORE.Product,
        "ETO Supply Chain Explorer 의 input(소재·공정 투입).", d)

    # --- 공급 어휘 (4종: 직접·간접·OEM·우회) ---
    supplies = obj_prop(
        g, GVC.supplies, "공급", "supplies",
        GVC.Company, GVC.Company,
        "기업→기업 공급(상위 공급 관계). DART 사업의 내용 실명 거래처.",
        defined_by=d)
    obj_prop(g, GVC.directlySupplies, "직접공급", "directlySupplies",
             GVC.Company, GVC.Company,
             "직접 공급(1차 거래).", parent=supplies, defined_by=d)
    obj_prop(g, GVC.indirectlySupplies, "간접공급", "indirectlySupplies",
             GVC.Company, GVC.Company,
             "간접 공급(2차+ 또는 경유).", parent=supplies, defined_by=d)
    obj_prop(g, GVC.oemSupplies, "OEM공급", "oemSupplies",
             GVC.Company, GVC.Company,
             "OEM 공급(주문자상표부착).", parent=supplies, defined_by=d)
    obj_prop(g, GVC.reroutedSupplies, "우회공급", "reroutedSupplies",
             GVC.Company, GVC.Company,
             "우회 공급(제3국·경유 우회). 우회 스크리닝 신호.",
             parent=supplies, defined_by=d)

    # SupplyEdge reification 연결
    obj_prop(g, GVC.supplier, "공급자", "supplier",
             GVC.SupplyEdge, GVC.Company,
             "공급관계의 공급 측 기업.", defined_by=d)
    obj_prop(g, GVC.customer, "수요자", "customer",
             GVC.SupplyEdge, GVC.Company,
             "공급관계의 수요 측 기업.", defined_by=d)
    obj_prop(g, GVC.suppliesProduct, "공급품목", "suppliesProduct",
             GVC.SupplyEdge, CORE.Product,
             "공급관계의 대상 품목.", defined_by=d)

    # 무역흐름·생산·가격 연결
    obj_prop(g, GVC.flowOrigin, "수출국", "flowOrigin",
             GVC.TradeFlow, CORE.Country,
             "무역흐름의 수출(원산)국.", defined_by=d)
    obj_prop(g, GVC.flowDestination, "수입국", "flowDestination",
             GVC.TradeFlow, CORE.Country,
             "무역흐름의 수입(도착)국.", defined_by=d)
    obj_prop(g, GVC.flowProduct, "무역품목", "flowProduct",
             GVC.TradeFlow, CORE.Product,
             "무역흐름의 대상 품목(HS).", defined_by=d)
    obj_prop(g, GVC.producesProduct, "생산품목", "producesProduct",
             GVC.Company, CORE.Product,
             "기업이 생산하는 품목.", defined_by=d)
    obj_prop(g, GVC.providesInput, "투입공급", "providesInput",
             GVC.Company, CORE.Product,
             "기업이 특정 투입재·장비를 공급함(ETO PROVIDES, share% 동반).",
             defined_by=d)
    obj_prop(g, GVC.priceOf, "가격대상", "priceOf",
             GVC.PriceIndex, CORE.Product,
             "가격지수가 가리키는 품목.", defined_by=d)

    # 의존·위험 reification 연결
    obj_prop(g, GVC.dependentActor, "의존주체", "dependentActor",
             GVC.Dependency, CORE.Entity,
             "의존하는 주체(기업·국가).", defined_by=d)
    obj_prop(g, GVC.dependsOnProduct, "의존품목", "dependsOnProduct",
             GVC.Dependency, CORE.Product,
             "의존 대상 품목.", defined_by=d)
    obj_prop(g, GVC.dependsOnSupplier, "의존공급원", "dependsOnSupplier",
             GVC.Dependency, GVC.Company,
             "의존 대상 공급원 기업.", defined_by=d)

    # --- GVC 데이터 속성 ---
    data_prop(g, GVC.tradeValueUSD, "무역액USD", "tradeValueUSD",
              GVC.TradeFlow, XSD.decimal,
              "무역흐름 금액(USD).", defined_by=d)
    data_prop(g, GVC.tradeQuantity, "무역수량", "tradeQuantity",
              GVC.TradeFlow, XSD.decimal,
              "무역흐름 수량.", defined_by=d)
    data_prop(g, GVC.marketShare, "시장점유율", "marketShare",
              None, XSD.decimal,
              "독점도 지표 시장점유율(%). ETO share_provided 등. 0~100.",
              defined_by=d)
    data_prop(g, GVC.hhi, "HHI", "hhi",
              None, XSD.decimal,
              "허핀달-허쉬만 집중지수(0~1, 점유율 제곱합). 의존·위험 집중도.", defined_by=d)
    data_prop(g, GVC.indexValue, "지수값", "indexValue",
              GVC.PriceIndex, XSD.decimal,
              "가격지수 값.", defined_by=d)
    data_prop(g, GVC.disclosureResolution, "공시해상도", "disclosureResolution",
              None, XSD.string,
              "공시 해상도 메타(국가비대칭: 한국 조밀·해외 희박).", defined_by=d)


# ===========================================================================
# 4) BRIDGE 모듈, 교차도메인 5관계 (owl:imports intl + gvc)
# ===========================================================================
def build_bridge(g: Graph):
    g.add((ONT_BRIDGE, RDF.type, OWL.Ontology))
    g.add((ONT_BRIDGE, DCTERMS.title,
           Literal("SSK 온톨로지: bridge 모듈 (교차도메인 5관계)", lang="ko")))
    g.add((ONT_BRIDGE, OWL.versionInfo, Literal(VERSION)))
    g.add((ONT_BRIDGE, OWL.imports, ONT_INTL))
    g.add((ONT_BRIDGE, OWL.imports, ONT_GVC))
    g.add((ONT_BRIDGE, RDFS.comment,
           Literal("국제관계 도메인과 공급사슬 도메인을 잇는 유일한 통로. "
                   "다섯 교차관계(affects·disrupts·restricts·circumvents·exposes)가 "
                   "각각 제약된 정의역·치역을 가지며, 이 모듈은 명명 클래스를 "
                   "두지 않는다.",
                   lang="ko")))

    d = ONT_BRIDGE

    # 모든 Bridge 관계의 공통 상위, KGE 가 '교차도메인 관계' 군집을 구분하도록
    bridgeRel = obj_prop(
        g, BR.bridgeRelation, "교차관계", "bridgeRelation",
        None, None,
        "국제관계↔GVC 교차도메인 관계의 공통 상위 속성.", defined_by=d)

    # range 가 union 인 affects 를 위해 union 클래스 준비
    company_or_supplyedge = union_of(g, [GVC.Company, GVC.SupplyEdge])

    # affects : SanctionedEntity -> (Company ∪ SupplyEdge) | riskScore
    obj_prop(g, BR.affects, "영향을줌", "affects",
             INTL.SanctionedEntity, company_or_supplyedge,
             "제재대상이 공급사슬 행위자·공급관계에 영향을 미친다(위험 표시). "
             "판정 규칙: 제재대상이 공급관계의 끝점이면 그 공급관계를 위험으로 본다.",
             parent=bridgeRel, defined_by=d)

    # disrupts : GeopoliticalEvent -> TradeFlow | magnitude, lag
    obj_prop(g, BR.disrupts, "교란함", "disrupts",
             INTL.GeopoliticalEvent, GVC.TradeFlow,
             "지정학 사건이 무역흐름을 교란한다. "
             "판정 규칙: 사건 관련국과 교역국이 겹치면 영향 후보이며 시차를 적용한다.",
             parent=bridgeRel, defined_by=d)

    # restricts : ExportControl -> Product | scope, date
    obj_prop(g, BR.restricts, "제한함", "restricts",
             INTL.ExportControl, CORE.Product,
             "수출통제가 품목을 제한한다. "
             "판정 규칙: 정책의 HS 범위와 품목 HS 가 겹치면 통제 대상이다.",
             parent=bridgeRel, defined_by=d)

    # circumvents : OwnershipPath -> Sanction | hops, suspicion
    obj_prop(g, BR.circumvents, "우회함", "circumvents",
             INTL.OwnershipPath, INTL.Sanction,
             "소유경로가 제재를 우회한다(의심). "
             "판정 규칙: 제재대상이 1~3 홉 소유로 비제재 법인을 거쳐 타깃에 "
             "공급하면 우회 의심으로 본다.",
             parent=bridgeRel, defined_by=d)

    # exposes : Dependency -> RiskNode | HHI, geoRisk
    obj_prop(g, BR.exposes, "노출시킴", "exposes",
             GVC.Dependency, GVC.RiskNode,
             "의존관계가 위험노드를 노출시킨다. "
             "판정 규칙: 단일 공급원 의존과 지정학 위험이 겹치면 위험 노출로 본다.",
             parent=bridgeRel, defined_by=d)

    # --- Bridge 엣지 속성 (reification 없이 엣지 reification 노드용 데이터 속성) ---
    # Bridge 관계는 weight·lag·suspicion 등을 부여해야 하므로 엣지 속성 정의.
    data_prop(g, BR.riskScore, "위험점수", "riskScore", None, XSD.decimal,
              "affects 의 위험 점수(0~1).", defined_by=d)
    data_prop(g, BR.magnitude, "영향크기", "magnitude", None, XSD.decimal,
              "disrupts 의 영향 크기.", defined_by=d)
    data_prop(g, BR.lag, "시차", "lag", None, XSD.integer,
              "disrupts 의 시차(개월). 제재 t → 무역 t+lag.", defined_by=d)
    data_prop(g, BR.scope, "범위", "scope", None, XSD.string,
              "restricts 의 통제 범위.", defined_by=d)
    data_prop(g, BR.hops, "경로길이", "hops", None, XSD.integer,
              "circumvents 의 소유경로 hop 수(1~3).", defined_by=d)
    data_prop(g, BR.suspicion, "의심도", "suspicion", None, XSD.decimal,
              "circumvents 의 우회 의심도(0~1).", defined_by=d)
    data_prop(g, BR.geoRisk, "지정학위험", "geoRisk", None, XSD.decimal,
              "exposes 의 지정학 위험(GPR 등).", defined_by=d)


# ===========================================================================
# 통합 온톨로지 메타 + 빌드
# ===========================================================================
def build_ontology_metadata(g: Graph):
    g.add((ONT, RDF.type, OWL.Ontology))
    g.add((ONT, DCTERMS.title,
           Literal("SSK 반도체 공급사슬 위기대응 단일 공유 온톨로지", lang="ko")))
    g.add((ONT, DCTERMS.title,
           Literal("SSK Semiconductor Supply Chain Crisis-Response Shared Ontology",
                   lang="en")))
    g.add((ONT, OWL.versionInfo, Literal(VERSION)))
    g.add((ONT, DCTERMS.created, Literal(TODAY, datatype=XSD.date)))
    g.add((ONT, DCTERMS.creator, Literal("박성호 (Park Sungho), 동아대학교 경영정보학과 (주저자)")))
    g.add((ONT, DCTERMS.contributor, Literal("이강배 (Lee Kangbae), 동아대학교 경영정보학과 (교신저자)")))
    g.add((ONT, DCTERMS.publisher, Literal("글로컬인공지능네트워크연구소(GAIN), 동아대학교")))
    g.add((ONT, DCTERMS.identifier, Literal("NRF-2024S1A3A2A07046144")))
    # 라이선스는 기계 판독 가능한 IRI 로 선언한다(자유문은 특정 불가).
    g.add((ONT, DCTERMS.license,
           URIRef("https://creativecommons.org/licenses/by/4.0/")))
    g.add((ONT, DCTERMS.rights,
           Literal("Ontology, shapes and curated data: CC-BY-4.0. Scripts: MIT. "
                   "Third-party source data retain their own licences; records "
                   "under non-redistributable terms are excluded from the deposit.",
                   lang="en")))
    g.add((ONT, RDFS.comment,
           Literal("사사: 이 저작물은 2024년 대한민국 교육부와 한국연구재단의 "
                   "지원을 받아 수행된 연구임(NRF-2024S1A3A2A07046144).", lang="ko")))
    g.add((ONT, RDFS.comment,
           Literal("Acknowledgment: This work was supported by the Ministry of "
                   "Education of the Republic of Korea and the National Research "
                   "Foundation of Korea (NRF-2024S1A3A2A07046144).", lang="en")))
    g.add((ONT, RDFS.comment,
           Literal("단일 공유 온톨로지. core+intl+gvc+bridge 4모듈을 "
                   "owl:imports 로 결합. 도메인 분리 구축 아님. Bridge 관계와 "
                   "LEI 조인이 공통 어휘를 요구하기 때문이다. "
                   "이 파일은 4모듈 트리플을 하나로 합친 export 본이다.", lang="ko")))
    # 통합본은 4 모듈을 모두 import 한 것으로 선언
    for m in (ONT_CORE, ONT_INTL, ONT_GVC, ONT_BRIDGE):
        g.add((ONT, OWL.imports, m))


def align_external(g: Graph):
    """표준 온톨로지 재사용(JWS 재사용 가치): 자체 상위·출처·시간 어휘를
    PROV-O·OWL-Time·Dublin Core·W3C Org에 정렬 공리로 연결한다. 제재·수출통제·
    bridge 등 도메인 특화 어휘는 대응 표준이 부재하여 신규 정의한다."""
    # 도메인 대상이 아니라 레코드가 prov:Entity 다. 대상을 prov:Entity 로 두면
    # 국가와 기업이 데이터셋에서 파생된 것으로 읽힌다.
    g.add((CORE.Record, RDFS.subClassOf, PROV.Entity))
    g.add((CORE.TemporalScope, RDFS.subClassOf, TIME.TemporalEntity))
    g.add((CORE.Organization, RDFS.subClassOf, ORG.Organization))
    g.add((CORE.source, RDFS.subPropertyOf, DCTERMS.source))
    g.add((CORE.collectedDate, RDFS.subPropertyOf, PROV.generatedAtTime))


def main():
    out_dir = Path(__file__).resolve().parent
    g = new_graph()

    build_ontology_metadata(g)
    build_core(g)
    build_intl(g)
    build_gvc(g)
    build_bridge(g)
    align_external(g)

    # 영어 정의 병기(릴리스 기본 언어). 미대응 키는 조용히 넘기지 않고 보고한다.
    from comments_en import COMMENTS_EN
    unmatched = set()
    for s, o in list(g.subject_objects(RDFS.comment)):
        if getattr(o, "language", None) == "ko":
            en = COMMENTS_EN.get(str(o))
            if en:
                g.add((s, RDFS.comment, Literal(en, lang="en")))
            else:
                unmatched.add(str(o)[:40])
    if unmatched:
        print(f"경고: 영어 정의 미대응 {len(unmatched)}건, comments_en.py 에 추가 필요")
        for u in sorted(unmatched)[:5]:
            print("   ", u)

    out = out_dir / "ontology.ttl"
    g.serialize(destination=str(out), format="turtle")

    # 모듈별 문서 분리 배포. 병합 문서 하나만 내면 네 모듈 IRI 가 같은 문서로
    # 역참조되어, 한 모듈만 필요한 소비자도 전체 어휘를 받게 된다.
    modules = write_module_documents(g, out_dir)

    # 요약 통계
    n_classes = len(set(g.subjects(RDF.type, OWL.Class)))
    n_obj = len(set(g.subjects(RDF.type, OWL.ObjectProperty)))
    n_data = len(set(g.subjects(RDF.type, OWL.DatatypeProperty)))
    print(f"[ontology.ttl] triples={len(g)}  classes={n_classes}  "
          f"object_props={n_obj}  data_props={n_data}")
    print(f"saved -> {out}")
    for name, (path, n) in modules.items():
        print(f"[{name}.ttl] triples={n}  -> {path.name}")
    return g


MODULE_IRIS = {
    "core": BASE + "core",
    "intl": BASE + "intl",
    "gvc": BASE + "gvc",
    "bridge": BASE + "bridge",
}


def write_module_documents(g: Graph, out_dir: Path) -> dict:
    """모듈별 TTL 문서를 낸다.

    각 문서는 (a) 그 모듈의 owl:Ontology 헤더와 (b) rdfs:isDefinedBy 가 그 모듈을
    가리키는 용어의 모든 트리플을 담는다. 정의 주체가 명시된 용어만 담으므로
    문서 간 중복이 없고, owl:imports 는 원본 헤더에 이미 있어 그대로 실린다.
    외부 어휘 정렬(prov·time·org·dcterms)은 그 용어의 트리플에 붙어 함께 간다.
    """
    ssk = Namespace(BASE)
    written = {}
    for name, iri in MODULE_IRIS.items():
        mod = URIRef(iri)
        mg = new_graph()
        # (a) 모듈 헤더
        for p, o in g.predicate_objects(mod):
            mg.add((mod, p, o))
        # (b) 이 모듈이 정의한 용어의 전 트리플
        for term in set(g.subjects(RDFS.isDefinedBy, mod)):
            for p, o in g.predicate_objects(term):
                mg.add((term, p, o))
            # 무명 노드(제약·합집합 등)의 내용을 **끝까지** 동반한다. 한 겹만 따라가면
            # owl:unionOf 가 가리키는 RDF 컬렉션의 rdf:first·rdf:rest 가 빠져, 모듈
            # 문서에서 그 합집합이 빈 클래스가 된다. 실측(v0.1.5 bridge.ttl):
            # bridge:affects 의 치역이 빈 합집합, 곧 owl:Nothing 이 되어 그 관계를
            # 재사용하는 소비자는 어떤 인스턴스도 적합하게 만들 수 없었다.
            seen, stack = set(), [o for o in g.objects(term, None)
                                  if isinstance(o, BNode)]
            while stack:
                b = stack.pop()
                if b in seen:
                    continue
                seen.add(b)
                for p2, o2 in g.predicate_objects(b):
                    mg.add((b, p2, o2))
                    if isinstance(o2, BNode):
                        stack.append(o2)
        path = out_dir / f"{name}.ttl"
        mg.serialize(destination=str(path), format="turtle")
        written[name] = (path, len(mg))
    return written


if __name__ == "__main__":
    main()
