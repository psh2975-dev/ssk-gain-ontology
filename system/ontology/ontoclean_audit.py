# -*- coding: utf-8 -*-
"""OntoClean 메타속성 감사.

명명 클래스마다 강성·동일성·단일성·의존성을 선언하고, 포섭 제약 셋을 검사한다.
어느 상위 온톨로지에도 적합성을 주장하지 않는다. OntoClean 은 분류를 점검하는
방법이며 존재론적 입장 선택과 독립이다(Guarino & Welty 2002).

판정은 사람이 내리고 이 파일에 선언한다. 스크립트가 하는 일은 셋이다.
  1) 선언이 실제 온톨로지의 클래스 집합과 어긋나지 않는지 대조
  2) 포섭 제약 위반 탐지
  3) 집계 산출(논문이 인용하는 수치의 근거)

실행: $env:PYTHONUTF8=1; python ontoclean_audit.py
"""
from __future__ import annotations

# 콘솔 인코딩 방어. 윈도 기본 콘솔(cp949 등)에서는 비ASCII 문자를 출력할 때
# UnicodeEncodeError 로 죽는다. 표준 출력만 UTF-8 로 재설정한다.
import sys as _sys
if hasattr(_sys.stdout, "reconfigure"):
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import json
import sys
from pathlib import Path

from rdflib import Graph, RDF, RDFS, OWL, URIRef

HERE = Path(__file__).resolve().parent
BASE = "https://w3id.org/ssk-gain/ontology/"

# 메타속성 선언. R: rigid / anti-rigid / category, O: 자체 동일성 기준,
# D: 의존, U: 단일성. 근거는 각 클래스의 정의문과 실제 데이터.
# (R, O, D, 동일성 기준)
DECL = {
    # 최상위 범주. 자체 동일성 기준을 공급하지 않는다.
    "core:Entity":              ("category", False, False, "-"),

    # 강성 종류. 자체 동일성 기준 보유.
    "core:Organization":        ("rigid", True,  False, "LEI; failing that, jurisdiction plus registration number"),
    "core:Country":             ("rigid", True,  False, "ISO 3166-1 alpha-3"),
    "core:Product":             ("rigid", True,  False, "HS code"),
    "core:Event":               ("rigid", True,  False, "spatiotemporal location"),
    "core:Policy":              ("rigid", True,  False, "issuing authority, date and measure"),
    "core:Location":            ("rigid", True,  False, "Wikidata QID"),
    # 강성 하위 종류. 상위의 동일성 기준을 상속.
    "core:Component":           ("rigid", False, False, "inherited from Product"),
    "core:Material":            ("rigid", False, False, "inherited from Product"),
    "core:Equipment":           ("rigid", False, False, "inherited from Product"),
    "intl:GeopoliticalEvent":   ("rigid", False, False, "inherited from Event"),
    "intl:ExportControl":       ("rigid", False, False, "inherited from Policy"),
    # 상위 Policy 의 기준(발령주체+시기+조치)을 정련한 것이지 다른 기준이 아니다.
    "intl:Sanction":            ("rigid", True,  False, "issuing authority and programme"),
    "intl:TradeMeasure":        ("rigid", False, False, "inherited from Policy"),
    "intl:FinancialSanction":   ("rigid", False, False, "inherited from Sanction"),
    "intl:InvestmentRestriction": ("rigid", False, False, "inherited from Sanction"),
    "intl:TechTransferBan":     ("rigid", False, False, "inherited from Sanction"),

    # 반강성. 어느 인스턴스도 본질적으로 갖지 않는 상태·역할.
    "intl:SanctionedEntity":    ("anti-rigid", False, False, "inherited from Organization"),
    "gvc:Company":              ("anti-rigid", False, False, "inherited from Organization"),
    "gvc:Input":                ("anti-rigid", False, False, "inherited from Product"),
    "gvc:RiskNode":             ("anti-rigid", False, False, "inherited from Organization or Product"),

    # 의존 개체. 관계 재화와 값 객체. 다른 개체 없이 존재하지 못한다.
    "core:TemporalScope":       ("rigid", True,  True,  "start and end"),
    "core:Identifier":          ("rigid", True,  True,  "scheme and value"),
    "core:SourceCoverage":      ("rigid", True,  True,  "source and collection window"),
    "intl:SanctionListing":     ("rigid", True,  True,  "issuing authority, programme and listed organisation"),
    "intl:OwnershipPath":       ("rigid", True,  True,  "start, end and path"),
    "intl:OwnershipAssertion":  ("rigid", True,  True,  "owner and owned organisation"),
    "gvc:TradeFlow":            ("rigid", True,  True,  "origin, destination, product and year"),
    "gvc:SupplyEdge":           ("rigid", True,  True,  "supplier, customer and product"),
    "gvc:Dependency":           ("rigid", True,  True,  "dependent actor, product and year"),
    "gvc:PriceIndex":           ("rigid", True,  True,  "product and base period"),
}

# 상위의 동일성 기준을 정련(specialise)한 하위. 다른 기준을 주장하는 것이 아니므로
# 충돌이 아니다. 정련인지 대체인지는 기계가 판정할 수 없어 사람이 선언한다.
IDENTITY_REFINEMENTS = {"intl:Sanction"}


def qname(u: URIRef) -> str | None:
    s = str(u)
    if not s.startswith(BASE) or "#" not in s:
        return None
    mod, local = s[len(BASE):].split("#", 1)
    return f"{mod}:{local}"


def main() -> int:
    g = Graph().parse(str(HERE / "ontology.ttl"), format="turtle")
    actual = {q for c in g.subjects(RDF.type, OWL.Class)
              if (q := qname(c)) is not None}

    missing = sorted(actual - set(DECL))
    ghost = sorted(set(DECL) - actual)
    print("=" * 70)
    print("OntoClean 메타속성 감사")
    print("=" * 70)
    print(f"온톨로지 명명 클래스 {len(actual)} / 선언 {len(DECL)}"
          f" / 미선언 {len(missing)} / 유령 {len(ghost)}")
    if missing:
        print("  !! 미선언:", missing)
    if ghost:
        print("  !! 유령 선언:", ghost)

    # 포섭 제약 검사
    viol = []
    for sub, sup in g.subject_objects(RDFS.subClassOf):
        a, b = qname(sub), qname(sup)
        if a not in DECL or b not in DECL:
            continue
        ra, oa, da, _ = DECL[a]
        rb, ob, db, _ = DECL[b]
        # 반강성은 강성을 포섭할 수 없다
        if rb == "anti-rigid" and ra == "rigid":
            viol.append(f"반강성 {b} 가 강성 {a} 를 포섭")
        # 의존은 비의존을 포섭할 수 없다
        if db and not da:
            viol.append(f"의존 {b} 가 비의존 {a} 를 포섭")
        # 하위가 상위와 다른 자체 동일성 기준을 주장할 수 없다
        if (oa and ob and DECL[a][3] != DECL[b][3]
                and not DECL[a][3].endswith("상속")
                and a not in IDENTITY_REFINEMENTS
                and b != "core:Entity"):
            viol.append(f"{a} 가 상위 {b} 와 다른 동일성 기준 주장")

    counts = {
        "named_classes": len(actual),
        "rigid": sum(1 for v in DECL.values() if v[0] == "rigid"),
        "anti_rigid": sum(1 for v in DECL.values() if v[0] == "anti-rigid"),
        "category": sum(1 for v in DECL.values() if v[0] == "category"),
        "own_identity": sum(1 for v in DECL.values() if v[1]),
        "dependent": sum(1 for v in DECL.values() if v[2]),
        "subsumption_violations": len(viol),
    }
    print()
    print("집계")
    for k, v in counts.items():
        print(f"  {k:26} {v}")
    print()
    if viol:
        print("포섭 제약 위반")
        for v in viol:
            print("  -", v)
    else:
        print("포섭 제약 위반 없음 (반강성·의존·동일성 세 제약 전건 통과)")

    out = HERE.parent / "kg" / "out" / "ontoclean_audit.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(
        {"counts": counts, "violations": viol,
         "declarations": {k: {"rigidity": v[0], "own_identity": v[1],
                              "dependent": v[2], "identity_criterion": v[3]}
                          for k, v in sorted(DECL.items())}},
        ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n저장 -> {out}")
    return 1 if (missing or ghost or viol) else 0


if __name__ == "__main__":
    sys.exit(main())
