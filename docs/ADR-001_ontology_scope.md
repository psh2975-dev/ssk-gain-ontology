# ADR-001. 온톨로지 범위 원칙 (4단 프레임)

> **Summary (English).** This record fixes what the ontology represents and what it deliberately does not. The criterion: the ontology represents queryable, inferable *facts* (what exists), not the *computational machinery* that produces them (how it is calculated).
>
> **The decision in brief.** The four tiers are T0 core representation (entities, relations,
> canonical identifiers, time, provenance, constraints), complete at the released version;
> T1 observed parameters (capacity, inventory, demand, unit price, transport mode, spatial
> subtypes such as chokepoints and maritime routes), planned for v0.2.0; T2 analytical
> results carried as provenance-tagged derived facts (predicted links with probabilities,
> anomaly flags, causal claims with method and interval, simulation scenarios and outcomes),
> planned for v0.2.0 to v0.3.0; and T3 the computational machinery itself (embedding weights,
> stock-flow equations and feedback loops, causal computation graphs, optimisation
> internals), permanently out of scope.
>
> **Why T3 is excluded.** T0 and T1 are domain knowledge and observed fact. T2 is derived
> fact, and the graph must hold downstream results as provenance-tagged facts if modules are
> to be cross-queried, audited and reused; this extends the existing provenance vocabulary
> (source, tier, confidence, evidence type) rather than adding a new mechanism. T3 is the
> form of a model. Representing simulation equations or embedding weights as ontology terms
> runs against ontology engineering practice and harms maintenance and reuse. Under this
> scope the ontology is not the simulation's equations but the interface that holds its
> inputs (T1) and outputs (T2) as facts.
>
> **Consequences.** The resource article describes the T0 layer; T1 and T2 are the roadmap,
> and the article states that the simulation junction lies outside its scope. The causal
> claim vocabulary of T2 is the channel by which subsequent theoretical work will load its
> results into the graph as facts. Contribution boundaries between the successor studies are
> unchanged: the ontology design belongs to this resource article, while the formalisation of
> the simulation junction, the extraction work and the federated methodology each belong to a
> separate study. The rest of this record sets out the same decision in Korean, with the
> v0.2.0 vocabulary backlog.

- 상태: 확정 (2026-07-09)
- 관련: 온톨로지 기여 경계, 어휘 갭, 시뮬레이션·잠재경로·연합방법론 후속 연구

## 맥락

시스템은 KG(Data) → KGE 링크예측 → 이상신호 → 인과추정 → SD 시뮬레이션(중심 가치) → GraphRAG 서비스로 이어진다. "공유 온톨로지가 시스템 근간"이라는데, 온톨로지가 시스템의 어디까지를 표현해야 하는가가 반복 쟁점이었다(특히 중심 가치인 SD를 온톨로지가 표현하지 못한다는 위상 모순).

## 판정 기준

온톨로지는 **질의·추론 가능한 사실("무엇이 있는가")** 을 표현하고, **계산 기계("어떻게 계산하는가")** 는 표현하지 않는다. 결정적 함의: 분석 모듈이 *산출한 결과*는 사실이므로 온톨로지에 들어가고, 그 결과를 *만드는 알고리즘*은 들어가지 않는다.

## 결정: 4단 범위 (T0 + T1 + T2 IN, T3 영구 OUT)

| 계층 | 내용 | 판정 |
|---|---|:---:|
| T0 핵심 표현 | 엔티티·관계·정준식별자·시간·출처·제약 | IN (v0.1.0 완성) |
| T1 관측 파라미터 | 생산능력·재고·수요·단가·운송모드·공간 하위유형(초크포인트·항로) | IN (v0.2.0) |
| T2 분석 결과(출처 태그된 파생 사실) | KGE 예측 링크(확률)·이상신호 플래그·인과 주장(원인·결과·계수·방법·CI)·SD 시나리오·결과 | IN (v0.2.0~0.3.0) |
| T3 계산 기계 | KGE 임베딩·가중치, SD 재고유량 방정식·피드백루프·적분, 인과 계산그래프, 최적화 내부 | OUT (영구) |

## 근거

- T0/T1은 도메인 지식·관측 사실. T2는 파생 사실이며, KG가 하류 결과를 *출처 태그된 사실*로 보유해야 모듈 간 교차질의·감사·재사용이 가능하다(PROV 패턴; 현 provenance 어휘 source·tier·confidence·evidenceType의 자연 확장).
- T3는 모델의 형식이다. 시뮬레이션 방정식·임베딩 가중치를 온톨로지로 모델링하는 것은 온톨로지 공학 관례에 반하고 유지보수·재사용을 해친다.
- 이 범위에서 온톨로지는 SD의 방정식이 아니라 SD의 입력(T1)·출력(T2)을 사실로 담는 **접합면**이 되어 "중심 가치를 근간이 못 담는다"는 위상 모순을 해소한다.

## 결과·경계

- **자원 논문은 T0 범위로 확정**. T1·T2는 로드맵이며 논문 수정은 불요하다(논의 절이 시뮬레이션 접합을 범위 밖으로 명시). 즉 본 ADR은 논문 변경이 아니라 온톨로지 v0.2.0 로드맵이다.
- T2의 인과 주장 어휘는 후속 이론 연구가 결과를 지식그래프에 사실로 적재하는 통로가 된다.
- 후속 연구별 기여 경계는 불변이다: 온톨로지 설계는 본 자원 논문, 시뮬레이션 접합 형식화·추출·연합방법론은 각각 별도 연구.

## v0.2.0 백로그 (T1·T2 구체 어휘, 설계 목표)

T1 관측 파라미터
- 공간 하위유형: core:Chokepoint, core:MaritimeRoute, core:Strait (⊑ core:Location)
- gvc:productionCapacity, gvc:inventoryLevel, gvc:demandVolume (SD 입력 파라미터)
- gvc:unitPrice, gvc:transportMode, gvc:leadTime (TradeFlow/SupplyEdge; 이상신호·SD 입력)

T2 분석 결과(파생 사실, 출처 필수)
- 예측 링크 provenance: derivedBy(모델·버전), predictedProbability — circumvents·reroutedSupplies에 KGE 예측 출처 부착
- gvc:AnomalySignal (또는 데이터속성 mirrorDiscrepancy·thirdCountrySurge·priceAnomaly), 거울통계·제3국 급증·단가 이상 플래그
- causal:CausalClaim: cause, effect, coefficient, method(예: 이중차분), confidenceInterval, evidenceType, source — 인과 결과의 재화 사실
- sd:Scenario + sd:ScenarioOutcome: shockType, policyLever(비축·대체·우회), recoveryTime, peakShortage — 시나리오 정의·결과만(방정식은 T3, 제외)

T3 제외(영구): 재고유량 방정식·피드백루프·적분, 임베딩 가중치, 인과 계산그래프, 최적화 내부.
