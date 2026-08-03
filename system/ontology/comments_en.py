# -*- coding: utf-8 -*-
"""English definitions for the ontology and shapes (primary language of the release).

Maps each Korean definition string (as written in the generators) to its English
counterpart. The generators add both language-tagged literals, English first.
Keys must match the generator strings byte-for-byte; a missed key means that
term ships without an English definition, so build_ontology.py counts and
reports unmatched entries instead of failing silently.
"""

COMMENTS_EN = {
 '정준 식별자가 아닌 보조 식별자. 병합 이전의 소스 키를 보존해 추적을 가능하게 하되, 동일성 판단에는 쓰지 않는다.':
 'Secondary identifier that is not the canonical one. It preserves the source key from before a merge so that provenance remains traceable, and it is not used to decide identity.',

 '자회사 관계(기업: 자회사). GLEIF L2·ICIJ 소유구조. 이행적이되 이는 지배 관계의 이행성이며 지분율의 이행성이 아니다. 합산 지분 판정은 소유관계진술의 지분율로 별도 계산한다. 비반사적: 법인은 자기 자신의 자회사가 아니다.':
 'Subsidiary relation, from GLEIF Level-2 and ICIJ ownership structures. Transitive, but the transitivity is that of control and not of equity share: aggregate shareholding is computed separately from the share carried on the ownership assertion. Irreflexive: a legal person is not its own subsidiary.',
 '지분 소유(OWNS). 소유경로(circumvents)의 기반 엣지. 비반사적: 법인은 자기 자신을 소유하지 않는다.':
 'Equity ownership. The base edge on which ownership paths, and hence circumvention, are traced. Irreflexive: a legal person does not own itself.',

 '법인·기업·기관. 정준 식별자는 LEI(GLEIF, ISO 17442)를 우선한다. LEI 미보유 법인은 관할과 등록번호의 결합을 쓰며, 둘 다 없으면 큐레이션 키를 잠정 식별자로 둔다(core:identifierStatus 로 표시). 이름은 동일성 기준이 아니다.':
 'Legal person, firm or institution. The canonical identifier is the LEI (GLEIF, ISO 17442) where one exists; otherwise the pair of jurisdiction and registration number; failing both, a curation key marked as provisional through core:identifierStatus. A name is not an identity criterion.',
 '정준 식별자의 근거. authoritative=표준 등록부(LEI·ISO·HS), provisional=큐레이션 키(표준 식별자 미보유).':
 'Warrant of the canonical identifier: authoritative for a standard register (LEI, ISO, HS), provisional for a curation key where no standard identifier exists.',

 '제재·통제 리스트에 등재된 조직(OFAC SDN·BIS Entity·중국 UEL 등). core:Organization 의 하위, 같은 LEI 노드로 GVC 행위자와 통합. 등재는 해제 가능한 상태이므로 이 분류는 현행 등재 조회용 파생 분류이며, 등재 사실 자체는 intl:SanctionListing 이 담는다.':
 'Organisation listed on a sanctions or control register (OFAC SDN, BIS Entity List, China UEL and similar). Subclass of core:Organization, merged with supply chain actors on the same LEI node. Listing is a revocable status, so this class is a derived classification for querying current listings; the listing fact itself is carried by intl:SanctionListing.',
 '특정 제재 목록에 특정 기간 등재된 사실. 등재 조직·근거 조치·발령 기관·효력기간·출처를 함께 담는다.':
 'The fact of being listed on a given sanctions register for a given period, carrying the listed organisation, the underlying measure, the issuing authority, the period of effect and the source.',
 '두 조직 사이의 지분 소유 관계를 개체로 재화한 것. 지분율·유효기간·출처를 이 개체에 부여한다.':
 'Reified equity ownership relation between two organisations. The share, the period of validity and the source are asserted on this individual.',
 '등재 사실이 가리키는 조직.':
 'The organisation the listing refers to.',
 '등재의 근거가 되는 제재 조치.':
 'The sanction measure on which the listing rests.',
 '등재를 발령한 기관 또는 목록 관할.':
 'The authority that issued the listing, or the jurisdiction of the register.',
 '지분을 보유한 조직.':
 'The organisation holding the equity share.',
 '지분이 보유된 조직.':
 'The organisation whose equity is held.',
 '소유 지분율(%). 소유관계진술 개체의 속성이며 조직의 속성이 아니다.':
 'Ownership share in percent. An attribute of the ownership assertion individual, not of an organisation.',

 "KG의 모든 1급 개체의 최상위 클래스.":
   "Top-level class of every first-class individual in the knowledge graph.",
 "valid_time(시작·종료) 등 시간 유효구간을 표현하는 reification 노드.":
   "Reification node expressing a validity interval (valid-time start and end).",
 "LEI·ISO·HS 등 표준 식별자 값 객체.":
   "Value object for standard identifiers such as LEI, ISO codes and HS codes.",
 "법인·기업·기관. canonical_id = LEI(GLEIF, ISO 17442).":
   "Legal person, firm or institution. Canonical identifier: LEI (GLEIF, ISO 17442).",
 "주권국가. canonical_id = ISO 3166-1 alpha-3.":
   "Sovereign state. Canonical identifier: ISO 3166-1 alpha-3.",
 "교역·통제 대상 품목. canonical_id = HS code(6자리), fallback ECCN.":
   "Product subject to trade or control. Canonical identifier: HS code (six digits), ECCN as fallback.",
 "시점·기간을 갖는 사건. 국제관계 모듈이 GeopoliticalEvent로 세분.":
   "Occurrence with a time point or interval; specialised by the international relations module as GeopoliticalEvent.",
 "정부·국제기구의 법령·조치. 국제관계 모듈이 세분.":
   "Statute or measure of a government or international body; specialised by the international relations module.",
 "지리적 위치(시설·항만·좌표). GIS 공간조인 기반.":
   "Geographic location (facility, port, coordinates); basis for GIS spatial joins.",
 "반도체 부품·메모리 등 (HS 8541·8542). Product의 하위.":
   "Semiconductor components and memory (HS 8541, 8542). Subclass of Product.",
 "반도체 소재 (HS 2804·2811·3707). Product의 하위.":
   "Semiconductor materials (HS 2804, 2811, 3707). Subclass of Product.",
 "반도체 제조장비 (HS 8486). Product의 하위.":
   "Semiconductor manufacturing equipment (HS 8486). Subclass of Product.",
 "한 데이터 소스의 수집 대상 기간과 관측 밀도를 선언하는 reification 노드. 수집 윈도 내 희박은 결측이 아니라 관측된 부재를 뜻한다.":
   "Reification node declaring a source's intended collection window and observation density. Sparsity inside the window means observed absence, not missingness.",
 "제재·통제 리스트에 등재된 조직(OFAC SDN·BIS Entity·중국 UEL 등). core:Organization 의 하위, 같은 LEI 노드로 GVC 행위자와 통합.":
   "Organisation listed on a sanctions or control register (OFAC SDN, BIS Entity List, China UEL and similar). Subclass of core:Organization; merged with supply chain actors through the shared LEI node.",
 "분쟁·관세·정책 변화 등 지정학적 사건. disrupts 의 주체.":
   "Geopolitical occurrence such as a conflict, tariff or policy shift. Subject of disrupts.",
 "제재 조치(금융·투자·기술이전). circumvents 의 대상.":
   "Sanction measure (financial, investment, technology transfer). Object of circumvents.",
 "자금·거래 동결 등 금융제재.":
   "Financial sanction such as an asset or transaction freeze.",
 "기술·지식 이전 금지.":
   "Prohibition on transferring technology or know-how.",
 "지분투자·인수 제한.":
   "Restriction on equity investment or acquisition.",
 "수출통제 조치(BIS·중국 양용물품·일본 수출규제). restricts 의 주체.":
   "Export control measure (BIS rules, China dual-use rules, the 2019 Japanese export controls). Subject of restricts.",
 "무역정책 개입(GTA·WTO 반덤핑·상계관세·NTM).":
   "Trade policy intervention (GTA records, WTO anti-dumping, countervailing duties, non-tariff measures).",
 "제재대상→(OWNS*1-3)→비제재 법인으로 이어지는 소유 연쇄. circumvents 의 주체(우회 의심 경로 reification).":
   "Ownership chain from a sanctioned entity through one to three ownership hops to a non-sanctioned legal person. Subject of circumvents (reification of a suspected circumvention path).",
 "공급사슬 행위자로서의 기업(삼성·SK하이닉스·TSMC·ASML 등). core:Organization 의 하위, 같은 LEI 로 intl:SanctionedEntity 와 통합.":
   "Firm as a supply chain actor (Samsung, SK hynix, TSMC, ASML and similar). Subclass of core:Organization; merged with intl:SanctionedEntity through the shared LEI.",
 "ETO Supply Chain Explorer 의 input(소재·공정 투입).":
   "Process input in the sense of the ETO Supply Chain Explorer (materials and process inputs).",
 "국가→국가 품목별 무역 흐름(HS·금액·수량) reification 노드. Comtrade·BACI 기반. disrupts 의 대상.":
   "Reified country-to-country trade flow per product (HS code, value, quantity), built from UN Comtrade and BACI. Object of disrupts.",
 "기업→기업 공급관계의 reification 노드(방향성·시점·신뢰도 보유). 거래액은 공시 부재로 미부여(방향성·존재성만). affects 의 대상.":
   "Reified firm-to-firm supply relation carrying direction, time and confidence. Transaction values are not assigned for lack of disclosure; only direction and existence. Object of affects.",
 "특정 품목·공급원에 대한 의존(단일의존·고집중) reification. HHI 보유. exposes 의 주체.":
   "Reified dependency of an actor on a product or supplier (single-sourcing, high concentration), carrying an HHI value. Subject of exposes.",
 "지정학·집중 위험이 결합되는 노출 대상(기업·품목·경로·지역). exposes 의 대상.":
   "Exposure target where geopolitical and concentration risk combine (firm, product, route or region). Object of exposes.",
 "메모리 가격 시계열 지수(ECOS D램 수출물가지수 등).":
   "Price index time series for memory products (for example the ECOS DRAM export price index).",
 "단일 공유 온톨로지. core+intl+gvc+bridge 4모듈을 owl:imports 로 결합. 도메인 분리 구축 아님. Bridge 관계와 LEI 조인이 공통 어휘를 요구하기 때문이다. 이 파일은 4모듈 트리플을 하나로 합친 export 본이다.":
   "Single shared ontology combining the four modules (core, intl, gvc, bridge) by owl:imports rather than building the domains separately, because the bridge relations and LEI joins require a common vocabulary. This file is the merged export of all four modules; each module also ships as its own document.",
 "사사: 이 저작물은 2024년 대한민국 교육부와 한국연구재단의 지원을 받아 수행된 연구임(NRF-2024S1A3A2A07046144).":
   "Acknowledgement: this work was supported by the Ministry of Education of the Republic of Korea and the National Research Foundation of Korea (NRF-2024S1A3A2A07046144).",
 "국제관계 도메인과 공급사슬 도메인을 잇는 유일한 통로. 다섯 교차관계(affects·disrupts·restricts·circumvents·exposes)가 각각 제약된 정의역·치역을 가지며, 이 모듈은 명명 클래스를 두지 않는다.":
   "The sole junction between the international relations domain and the supply chain domain: five cross-domain relations (affects, disrupts, restricts, circumvents, exposes), each with a constrained domain and range, and no named classes of its own.",
 "국제관계↔GVC 교차도메인 관계의 공통 상위 속성.":
   "Common superproperty of the cross-domain relations between the international relations and supply chain domains.",
 "제재대상이 공급사슬 행위자·공급관계에 영향을 미친다(위험 표시). 판정 규칙: 제재대상이 공급관계의 끝점이면 그 공급관계를 위험으로 본다.":
   "A sanctioned entity affects a supply chain actor or supply relation (at-risk marking). Rule of thumb: if a sanctioned entity is an endpoint of a supply relation, that relation is at risk.",
 "지정학 사건이 무역흐름을 교란한다. 판정 규칙: 사건 관련국과 교역국이 겹치면 영향 후보이며 시차를 적용한다.":
   "A geopolitical event disrupts a trade flow. Rule of thumb: overlap between event countries and trading countries yields impact candidates, with a lag.",
 "수출통제가 품목을 제한한다. 판정 규칙: 정책의 HS 범위와 품목 HS 가 겹치면 통제 대상이다.":
   "An export control restricts a product. Rule of thumb: overlap between the policy's HS scope and the product's HS code implies control.",
 "소유경로가 제재를 우회한다(의심). 판정 규칙: 제재대상이 1~3 홉 소유로 비제재 법인을 거쳐 타깃에 공급하면 우회 의심으로 본다.":
   "An ownership path circumvents a sanction (suspicion). Rule of thumb: a sanctioned entity owning, within one to three hops, a non-sanctioned supplier of the target raises circumvention suspicion.",
 "의존관계가 위험노드를 노출시킨다. 판정 규칙: 단일 공급원 의존과 지정학 위험이 겹치면 위험 노출로 본다.":
   "A dependency exposes a risk node. Rule of thumb: single-source dependency combined with geopolitical risk implies risk exposure.",
 "지정학 이벤트와 정책(제재·수출통제·무역조치)의 문서화된 연관. 무방향(대칭). 인과 불포함(인과 추정은 별도 분석의 몫). 예: 정책 이벤트와 그에 수반된 제재의 연결.":
   "Documented association between a geopolitical event and a policy (sanction, export control, trade measure). Symmetric; carries no causal claim. Example: linking a policy event with the sanction that accompanied it.",
 "인수·합병(기업: 인수합병).":
   "Acquisition or merger between firms.",
 "기술이전금지가 적용되는 조직.":
   "Organisation to which a technology transfer ban applies.",
 "엔티티 정규 식별자(접점 명세 canonical_id 규칙의 일반 슬롯).":
   "Canonical identifier of an entity (the generic slot for the canonical-identifier scheme).",
 "데이터 수집일. 재현성·계보 태그.":
   "Date the record was collected; reproducibility and lineage tag.",
 "추출 트리플 confidence(0~1). 0.7 미만 제거 기준.":
   "Confidence of the record or triple (0 to 1); values below 0.7 are dropped by convention.",
 "수출통제 범위(품목군·국가 등).":
   "Scope of an export control (product families, countries and similar).",
 "이 소스의 수집 대상 기간 종료 연도(2025).":
   "End year of the source's intended collection window.",
 "이 소스의 수집 대상 기간 시작 연도. 연구 기간 설계(2008~)와 정합.":
   "Start year of the source's intended collection window, aligned with the study period design (2008 onwards).",
 "공급관계의 수요 측 기업.":
   "Customer side of a supply relation.",
 "데이터셋/모듈이 소스별 커버리지 선언을 갖는다.":
   "Links a dataset or module to its per-source coverage declaration.",
 "의존하는 주체(기업·국가).":
   "Actor that depends (firm or country).",
 "의존 대상 품목.":
   "Product depended upon.",
 "의존 대상 공급원 기업.":
   "Supplier firm depended upon.",
 "직접 공급(1차 거래).":
   "Direct supply (first-tier trade).",
 "공시 해상도 메타(국가비대칭: 한국 조밀·해외 희박).":
   "Disclosure resolution metadata (asymmetric by country: dense for Korea, sparse elsewhere).",
 "수출통제 분류번호(ECCN). HS의 통제 측 fallback 식별자.":
   "Export Control Classification Number (ECCN); control-side fallback identifier for HS.",
 "정책을 제정한 국가.":
   "Country that enacted the policy.",
 "관계 종료 연도.":
   "End year of the relation.",
 "지정학 사건 발생일.":
   "Date of the geopolitical event.",
 "관측(observed) vs 추론(inferred) 구분, 불확실성 태그.":
   "Distinguishes observed from inferred evidence; uncertainty tag.",
 "품목이 수출통제 조치의 대상임.":
   "The product is subject to an export control measure.",
 "금융제재가 조직을 대상으로 함.":
   "A financial sanction targets the organisation.",
 "무역흐름의 수입(도착)국.":
   "Importing (destination) country of the trade flow.",
 "무역흐름의 수출(원산)국.":
   "Exporting (origin) country of the trade flow.",
 "무역흐름의 대상 품목(HS).":
   "Product (HS) of the trade flow.",
 "exposes 의 지정학 위험(GPR 등).":
   "Geopolitical risk attribute of exposes (for example a GPR reading).",
 "조직의 생산시설 위치(지리: 생산시설).":
   "Location of the organisation's production facility.",
 "엔티티/관계의 유효 시간범위 연결.":
   "Links an entity or relation to its validity interval.",
 "조직의 본사 소재 국가(지리: 본사위치).":
   "Country where the organisation is headquartered.",
 "허핀달-허쉬만 집중지수(0~1, 점유율 제곱합). 의존·위험 집중도.":
   "Herfindahl-Hirschman index (0 to 1; sum of squared shares). Concentration of dependency or risk.",
 "circumvents 의 소유경로 hop 수(1~3).":
   "Number of ownership hops on the circumvention path (1 to 3).",
 "WCO HS code. 품목 canonical_id(6자리), 정밀은 HS10.":
   "WCO HS code; canonical product identifier (six digits, HS10 where finer).",
 "국가가 무역조치를 부과함.":
   "The country imposes a trade measure.",
 "조직의 법인 설립국(지리: 법인설립국).":
   "Country of incorporation of the organisation.",
 "가격지수 값.":
   "Value of the price index.",
 "간접 공급(2차+ 또는 경유).":
   "Indirect supply (second tier or beyond, or via intermediaries).",
 "국가 ISO 3166-1 alpha-3 코드(KOR·USA·CHN·JPN·NLD). canonical_id.":
   "ISO 3166-1 alpha-3 country code (KOR, USA, CHN, JPN, NLD); canonical identifier.",
 "합작법인 관계(기업: 합작법인).":
   "Joint venture relation between firms.",
 "엔티티 표기명(추출 원문 표면형 포함).":
   "Display name of the entity (including the source surface form).",
 "disrupts 의 시차(개월). 제재 t → 무역 t+lag.":
   "Lag of disrupts in months: measure at t, trade effect at t plus lag.",
 "GLEIF Legal Entity Identifier (ISO 17442, 20자). 기업 canonical_id.":
   "GLEIF Legal Entity Identifier (ISO 17442, 20 characters); canonical firm identifier.",
 "제재 조치가 제재대상을 등재함.":
   "The sanction measure lists the sanctioned entity.",
 "disrupts 의 영향 크기.":
   "Magnitude attribute of disrupts (observed relative change).",
 "독점도 지표 시장점유율(%). ETO share_provided 등. 0~100.":
   "Market share in percent (0 to 100), for example ETO share_provided.",
 "커버리지 기간에 실제 관측된 레코드 수. 0 또는 소수여도 결측이 아닌 관측된 부재.":
   "Number of records actually observed in the coverage window. Zero or few still means observed absence, not missingness.",
 "OEM 공급(주문자상표부착).":
   "OEM supply (original equipment manufacturing).",
 "소유의 역관계.":
   "Inverse of the ownership relation.",
 "소유 지분율(%). owns 엣지 속성.":
   "Ownership share in percent; attribute of the owns edge.",
 "지분 소유(OWNS). 소유경로(circumvents)의 기반 엣지.":
   "Equity ownership; the base edge of ownership paths and circumvention screening.",
 "소유경로의 끝(비제재 법인).":
   "End of the ownership path (the non-sanctioned legal person).",
 "소유경로의 시작(제재대상).":
   "Start of the ownership path (the sanctioned entity).",
 "가격지수가 가리키는 품목.":
   "Product the price index refers to.",
 "기업이 생산하는 품목.":
   "Product the firm produces.",
 "기업이 특정 투입재·장비를 공급함(ETO PROVIDES, share% 동반).":
   "The firm provides a specific input or equipment (ETO PROVIDES, with a share percentage).",
 "우회 공급(제3국·경유 우회). 우회 스크리닝 신호.":
   "Rerouted supply (via third countries or intermediaries); a circumvention screening signal.",
 "투자제한이 적용되는 조직.":
   "Organisation to which an investment restriction applies.",
 "affects 의 위험 점수(0~1).":
   "Risk score attribute of affects (0 to 1).",
 "제재 발효일(valid_time 근사 기준).":
   "Effective date of the sanction (approximation basis for valid time).",
 "restricts 의 통제 범위.":
   "Scope attribute of restricts (licensing scope).",
 "데이터 출처(소스명). provenance 태그.":
   "Data source name; provenance tag.",
 "관계 시작 연도(공급·계약 등 시간 어휘).":
   "Start year of the relation (temporal vocabulary for supply, contracts and similar).",
 "전략적 제휴(기업: 전략적제휴).":
   "Strategic alliance between firms.",
 "자회사 관계(기업: 자회사). GLEIF L2·ICIJ 소유구조.":
   "Subsidiary relation between firms (GLEIF Level-2 and ICIJ ownership structures).",
 "공급관계의 공급 측 기업.":
   "Supplier side of a supply relation.",
 "기업→기업 공급(상위 공급 관계). DART 사업의 내용 실명 거래처.":
   "Firm-to-firm supply (the superproperty of the supply family); named counterparties from DART business reports.",
 "공급관계의 대상 품목.":
   "Product of the supply relation.",
 "circumvents 의 우회 의심도(0~1).":
   "Circumvention suspicion attribute (0 to 1).",
 "공식성 4-Tier(T1~T4).":
   "Officiality tier of the source (T1 to T4).",
 "무역흐름 수량.":
   "Quantity of the trade flow.",
 "무역흐름 금액(USD).":
   "Value of the trade flow in USD.",
 "valid_time 시작일. 모든 노드/엣지 시점 정합에 사용.":
   "Start of valid time; used for temporal alignment of all nodes and edges.",
 "valid_time 종료일.":
   "End of valid time.",
 "Wikidata QID. LEI 미매칭 시 기업 fallback 식별자.":
   "Wikidata QID; fallback identifier for organisations without an LEI, and canonical identifier for spatial nodes.",
    '표준 등록부가 발급한 식별자. 값이 아니라 개체로 세워, 동일성 추론이 데이터 속성이 아닌 객체 속성 위에서 이루어지게 한다.':
        'An identifier issued by a standard registry. It is raised to an individual rather than left as a value, so that identity inference runs over an object property rather than a data property and stays within OWL 2 DL.',
    '엔티티가 보유한 표준 식별자. 역함수적이므로 같은 식별자 개체를 가리키는 두 엔티티는 동일하다. 이 축이 교차 도메인 결합의 논리적 근거다.':
        'The standard identifier an entity bears. The property is inverse functional, so two entities pointing at the same identifier individual are the same entity. This axis is the logical warrant for the cross-domain join.',
    '식별자를 발급한 등록 체계(LEI·ISO3166-1-alpha-3·HS·Wikidata).':
        'The registry scheme that issued the identifier (LEI, ISO 3166-1 alpha-3, HS, Wikidata).',
    '식별자의 문자열 값. 체계와 값의 쌍이 식별자 개체를 결정한다.':
        'The string value of the identifier. The pair of scheme and value determines the identifier individual.',
    '발급 등록부가 보고하는 등록 상태(ISSUED·LAPSED·RETIRED 등). 제재 대상 기업에서 실효 등록이 흔하므로, 식별자의 현재성을 값과 분리해 기록한다.':
        'The registration status reported by the issuing registry (ISSUED, LAPSED, RETIRED and the like). Lapsed registrations are common among sanctioned organisations, so currency is recorded separately from the value.',
    '어떤 도메인 대상에 관해 한 출처가 남긴 자료 레코드. 수집일·출처·등급·라이선스와 PROV 계보가 여기에 붙는다.':
        'A data record left by one source about some domain object. Collection date, source, tier, licence and the PROV lineage attach here rather than to the object itself.',
    '이 레코드가 진술하는 도메인 대상.':
        'The domain object this record states something about.',
}

MESSAGES_EN = {
 "LEI 는 ISO 17442 형식(20자 영숫자)이어야 하며 1개만 허용.":
   "LEI must follow ISO 17442 (20 alphanumeric characters); at most one.",
 "본사위치 range 는 Country, 최대 1개.":
   "headquarteredIn must point to a Country; at most one.",
 "법인설립국 range 는 Country, 최대 1개.":
   "incorporatedIn must point to a Country; at most one.",
 "조직은 명칭(name) 1개 이상 권고.":
   "An organisation should carry at least one name (recommended).",
 "국가는 ISO 3166-1 alpha-3(대문자 3자) 정확히 1개.":
   "A country must carry exactly one ISO 3166-1 alpha-3 code (three uppercase letters).",
 "국가의 정준 식별자는 ISO 3166-1 alpha-3(대문자 3자).":
   "A country's canonical identifier must be ISO 3166-1 alpha-3 (three uppercase letters).",
 "HS코드는 4(헤딩)·6(소호)·8·10자리 숫자.":
   "HS code must be 4 (heading), 6 (subheading), 8 or 10 digits.",
 "제재일은 xsd:date, 최대 1개.":
   "Sanction date must be xsd:date; at most one.",
 "제재 등재 대상은 SanctionedEntity.":
   "listsEntity must point to a SanctionedEntity.",
 "지정학 사건은 사건일 정확히 1개.":
   "A geopolitical event must carry exactly one event date.",
"HHI 는 0~1 (점유율 제곱합).":
   "HHI must be 0 to 1 (sum of squared shares).",
 "affects 의 range 는 Company 또는 SupplyEdge.":
   "Range of affects must be Company or SupplyEdge.",
 "circumvents 소유경로 hop 은 1~3 (필수).":
   "Circumvention path hops must be 1 to 3 (required).",
 "circumvents 의 range 는 Sanction, 1개 이상.":
   "Range of circumvents must be Sanction; at least one.",
 "circumvents 의심도는 0~1.":
   "Circumvention suspicion must be 0 to 1.",
 "disrupts 의 range 는 TradeFlow.":
   "Range of disrupts must be TradeFlow.",
 "exposes 의 range 는 RiskNode.":
   "Range of exposes must be RiskNode.",
 "restricts 의 range 는 Product.":
   "Range of restricts must be Product.",
 "riskScore 는 0~1.":
   "riskScore must be 0 to 1.",
 "가격지수는 대상 품목 1개 이상.":
   "A price index must reference at least one product.",
 "공간노드 QID 는 Q+숫자 형식 최대 1개.":
   "A spatial node's QID must match Q followed by digits; at most one.",
 "공급관계는 공급자(Company) 정확히 1개.":
   "A supply edge must have exactly one supplier (Company).",
 "공급관계는 수요자(Company) 정확히 1개.":
   "A supply edge must have exactly one customer (Company).",
 "공급품목 range 는 Product.":
   "Range of suppliesProduct must be Product.",
 "관측수는 0 이상 정수 1개 필수(0도 관측된 부재).":
   "Observed count must be one non-negative integer (zero still means observed absence).",
 "무역수량은 0 이상.":
   "Trade quantity must be non-negative.",
 "무역액은 0 이상.":
   "Trade value must be non-negative.",
 "무역흐름 수입국은 Country 정확히 1개.":
   "A trade flow must have exactly one destination Country.",
 "무역흐름 수출국은 Country 정확히 1개.":
   "A trade flow must have exactly one origin Country.",
 "무역흐름은 품목(Product) 1개 이상.":
   "A trade flow must reference at least one Product.",
 "소유경로 끝은 Organization 정확히 1개.":
   "An ownership path must end at exactly one Organization.",
 "소유경로 시작은 SanctionedEntity 정확히 1개.":
   "An ownership path must start at exactly one SanctionedEntity.",
 "시장점유율은 0~100.":
   "Market share must be 0 to 100.",
 "신뢰도는 0~1.":
   "Confidence must be 0 to 1.",
 "의존관계는 의존주체 1개 이상.":
   "A dependency must have at least one dependent actor.",
 "지분율은 0~100.":
   "Ownership share must be 0 to 100.",
 "지정학위험은 0 이상.":
   "Geopolitical risk must be non-negative.",
 "커버리지 선언은 소스명 1개 필수.":
   "A coverage declaration must carry exactly one source name.",
 "커버리지 시작은 gYear 최대 1개(무시간 소스는 생략 가능).":
   "Coverage start must be at most one gYear (omitted for non-temporal sources).",
 "커버리지 종료는 gYear 최대 1개.":
   "Coverage end must be at most one gYear.",
}