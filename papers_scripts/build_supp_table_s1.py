# -*- coding: utf-8 -*-
"""Supplementary Table S1(클래스 계층)을 ontology.ttl 실측에서 결정론 생성.

배경: 분량 감축(2026-07-29)으로 본문 클래스 카탈로그 표 3개를 S1으로 이관했다.
      이관 전 본문 표에는 정의(Definition) 열이 있었으나 S1에는 없어, 정의가
      소실될 뻔했다. 이 스크립트가 계층은 TTL에서 기계 추출하고, 영문 정의는
      본문에서 이관한 정본(DEFS)을 주입해 두 정보를 한 표로 합친다.

원칙: 클래스명·상위클래스·개수는 TTL이 정본(기억 타이핑 금지).
      DEFS 키가 TTL 클래스 집합과 정확히 일치하지 않으면 실패시킨다.
"""

# 콘솔 인코딩 방어. 윈도 기본 콘솔(cp949 등)에서는 비ASCII 문자를 출력할 때
# UnicodeEncodeError 로 죽는다. 표준 출력만 UTF-8 로 재설정한다.
import sys as _sys
if hasattr(_sys.stdout, "reconfigure"):
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import io
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
ONT = ROOT / "system" / "ontology" / "ontology.ttl"
SUPP = ROOT / "papers" / "PAP-01_Data" / "draft" / "PAP01_supplementary_EN.md"

MODULES = [
    ("core", "core (upper shared)"),
    ("intl", "intl (international relations)"),
    ("gvc", "gvc (supply chain)"),
]

# 본문 Tables 5·6·7에서 이관한 영문 정의 정본(2026-07-29 이관).
DEFS = {
    "core:Entity": "Top-level class from which all individual classes of the ontology derive",
    "core:Organization": "Legal persons, firms and institutions (canonical identifier: legal entity identifier)",
    "core:Country": "Sovereign states (canonical identifier: ISO 3166-1 alpha-3)",
    "core:Product": "Products subject to trade and control (canonical identifier: HS (Harmonized System) code)",
    "core:Material": "Semiconductor materials",
    "core:Equipment": "Semiconductor manufacturing equipment",
    "core:Component": "Semiconductor components and memory",
    "core:Event": "An occurrence with a time point or interval",
    "core:Policy": "Statutes and measures of governments and international organisations",
    "core:Location": "Geographic locations (facilities, ports, coordinates)",
    "core:Identifier": ("Identifier issued by a standard registry, raised to an "
                        "individual so that identity inference runs over an object "
                        "property and stays within OWL 2 DL"),
    "core:Record": ("Data record a source left about a domain object; collection "
                    "date, source, tier and the PROV lineage attach here rather "
                    "than to the object itself"),
    "core:TemporalScope": "Reified node expressing a temporal validity interval",
    "core:SourceCoverage": "Reified node declaring the collection period and observation density of a source",
    "intl:SanctionListing": "The fact of an organisation being listed on a given sanctions register for a given period, with its issuing authority and source",
    "intl:OwnershipAssertion": "A reified equity ownership relation between two organisations, carrying the share, the period of validity and the source",
    "intl:Sanction": "A sanction imposed by a sending state on a target",
    "intl:FinancialSanction": "A sanction restricting financial transactions",
    "intl:TechTransferBan": "A sanction prohibiting transfer of technology and knowledge",
    "intl:InvestmentRestriction": "A sanction restricting equity investment and acquisition",
    "intl:ExportControl": "A control placing product exports under licensing",
    "intl:SanctionedEntity": "An organisation designated on a sanctions list",
    "intl:GeopoliticalEvent": "A geopolitical occurrence",
    "intl:OwnershipPath": "An ownership chain from a sanctioned target to a non-sanctioned legal person",
    "intl:TradeMeasure": "Upper type for trade policy intervention",
    "gvc:Company": "A firm participating in the supply chain",
    "gvc:TradeFlow": "A product trade flow from origin to destination (reified node)",
    "gvc:SupplyEdge": "A reified supply relation joining supplier and customer",
    "gvc:Dependency": "A given actor's dependency on a product or supplier",
    "gvc:RiskNode": "A node where vulnerability concentrates",
    "gvc:Input": "Materials and process inputs",
    "gvc:PriceIndex": "A price time-series index for a product",
}

CLASS_BLOCK = re.compile(
    r"^((?:core|intl|gvc):[A-Z]\w*)\s+a\s+owl:Class\s*;(.*?)(?=\n\n|\Z)",
    re.M | re.S,
)


def parse_classes(text):
    """TTL에서 {클래스: (내부 상위클래스, 외부 정렬)} 추출."""
    out = {}
    for m in CLASS_BLOCK.finditer(text):
        name, body = m.group(1), m.group(2)
        sup = re.search(r"rdfs:subClassOf\s+(.*?)(?=;|\.\s*$|\Z)", body, re.S)
        parents = []
        if sup:
            parents = [p.strip() for p in sup.group(1).split(",") if p.strip()]
        internal = next(
            (p for p in parents if p.split(":")[0] in ("core", "intl", "gvc")), None
        )
        # owl:Thing 은 최상위 클래스의 실제 선언이므로 그대로 적는다("(top level)"
        # 로 바꾸면 TTL 에 있는 선언이 논문에서 사라진다).
        if internal is None and "owl:Thing" in parents:
            internal = "owl:Thing"
        external = [p for p in parents if p != internal and p != "owl:Thing"]
        out[name] = (internal or "(top level)", "; ".join(external) or "")
    return out


def main():
    classes = parse_classes(io.open(ONT, encoding="utf-8").read())

    missing = sorted(set(classes) - set(DEFS))
    extra = sorted(set(DEFS) - set(classes))
    if missing or extra:
        print(f"FAIL 정의 집합 불일치 — TTL에만: {missing} / DEFS에만: {extra}")
        return 1

    lines = [
        "## Supplementary Table S1. Ontology class hierarchy and class definitions "
        "(measured, ontology.ttl v0.1.9)",
        "",
        f"The {len(classes)} named classes by module, with the definition of each. "
        "Superclass is the internal rdfs:subClassOf parent; alignment gives the "
        "external standard vocabulary the class is additionally declared beneath.",
        "",
    ]
    for prefix, heading in MODULES:
        rows = sorted(k for k in classes if k.startswith(prefix + ":"))
        lines += [f"### {heading}", ""]
        lines += ["| Class | Definition | Superclass | Alignment |", "|------|------|------|------|"]
        for k in rows:
            internal, external = classes[k]
            lines.append(f"| {k} | {DEFS[k]} | {internal} | {external or '-'} |")
        lines.append("")

    new_block = "\n".join(lines)

    supp = io.open(SUPP, encoding="utf-8").read()
    start = supp.index("## Supplementary Table S1.")
    end = supp.index("## Supplementary Table S2.")
    io.open(SUPP, "w", encoding="utf-8", newline="\n").write(
        supp[:start] + new_block + "\n" + supp[end:]
    )

    n = sum(len([k for k in classes if k.startswith(p + ":")]) for p, _ in MODULES)
    print(f"OK S1 재생성 — 클래스 {n}건(core/intl/gvc), 정의 열 추가")
    for p, _ in MODULES:
        print(f"   {p}: {len([k for k in classes if k.startswith(p + ':')])}건")
    return 0


if __name__ == "__main__":
    sys.exit(main())
