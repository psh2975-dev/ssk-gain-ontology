# -*- coding: utf-8 -*-
"""제재 대상 조직의 LEI 해소 가능성 실측.

원고는 정준 식별자로 두 도메인을 잇는다고 말한다. 그런데 파일럿의 제재 대상
579건 가운데 LEI 칸이 채워진 것은 0건이다. 그것이 「LEI가 없다」는 뜻인지
「우리가 조회하지 않았다」는 뜻인지는 세어 보기 전에는 알 수 없다. SMIC 한 건을
조회하니 LEI가 실재했으므로(등록은 실효 상태), 후자일 가능성이 크다.

이 스크립트는 표본으로 해소율을 재고, 그 수치를 원고가 인용할 수 있게 남긴다.
개인은 LEI 대상이 아니므로 조직으로 보이는 것만 조회한다. 이름 대조는 자동
해소 방법이 아니라 **적용 범위를 재는 진단**이다. 실제 부착은 사람이 확인한
건에 한정한다(이름 기반 해소는 원고가 향후 과제로 선언한 사항이다).

실행: $env:PYTHONUTF8=1; python probe_lei_resolution.py [표본수]
산출: out/lei_resolution_probe.json
"""
from __future__ import annotations

import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data" / "curated"
OUT = HERE / "out"
API = "https://api.gleif.org/api/v1/lei-records"

# 법인격을 나타내는 접미. 개인을 걸러내는 데 쓴다. 완벽할 필요는 없다.
# 목적은 해소율의 분모를 조직으로 한정하는 것이지 법인격 판정이 아니다.
ORG_MARKS = re.compile(
    r"\b(CO|CO\.|LTD|LIMITED|INC|CORP|CORPORATION|COMPANY|LLC|LLP|PLC|GMBH|AG|"
    r"S\.?A\.?|SARL|BV|B\.V\.|NV|N\.V\.|PTE|PTY|OAO|OOO|JSC|PJSC|KFT|SP|SPA|"
    r"GROUP|HOLDING|HOLDINGS|TRADING|TECHNOLOG\w*|INDUSTR\w*|ELECTRONICS?|"
    r"SEMICONDUCTORS?|MANUFACTURING|ENTERPRISE|BANK|SHIPPING|LOGISTICS)\b",
    re.I)
# 「성, 이름」 형태는 개인으로 본다.
PERSON = re.compile(r"^[A-Z][A-Za-z'-]+,\s+[A-Z]")

STOP = {"co", "ltd", "inc", "corp", "corporation", "company", "limited", "llc",
        "the", "and", "group", "holding", "holdings"}


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def core_tokens(s: str) -> set[str]:
    # 괄호 안의 약칭은 GLEIF 표제에 없다. 남겨 두면 SMIC 처럼 실제로 해소되는
    # 건이 전부 탈락한다(첫 실행에서 겪음). 대조 전에 걷어낸다.
    s = re.sub(r"\([^)]*\)", " ", s or "")
    return {t for t in re.findall(r"[a-z]{3,}", s.lower()) if t not in STOP}


def covers(tq: set[str], tc: set[str], floor: float = 0.75) -> bool:
    """질의 토큰이 후보에 얼마나 담겼는가. 완전 포함만 인정하면 표기 차이
    (Technologies vs Technology, 지점명 추가) 하나에 전부 탈락한다."""
    if not tq:
        return False
    return len(tq & tc) / len(tq) >= floor


def gleif(name: str, size: int = 5) -> list[dict]:
    q = urllib.parse.urlencode({"filter[fulltext]": name, "page[size]": size})
    req = urllib.request.Request(f"{API}?{q}", headers={"Accept": "application/vnd.api+json"})
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.loads(r.read().decode()).get("data", [])


def names_of(rec: dict) -> list[str]:
    a = rec["attributes"]["entity"]
    out = [a["legalName"]["name"]]
    for k in ("otherNames", "transliteratedOtherNames"):
        for o in a.get(k) or []:
            if o.get("name"):
                out.append(o["name"])
    return out


def main() -> int:
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 40
    src = sorted(DATA.glob("curated_intl_*_conformant.json"))[-1]
    nodes = json.loads(src.read_text(encoding="utf-8"))["nodes"]
    sanc = [n for n in nodes if n["rdf_type"].endswith("SanctionedEntity")]

    orgs, persons = [], []
    for n in sanc:
        lb = n.get("label") or ""
        (persons if PERSON.match(lb) and not ORG_MARKS.search(lb) else
         orgs if ORG_MARKS.search(lb) else persons).append(n)

    print(f"제재 대상 {len(sanc)}건 = 조직 추정 {len(orgs)} + 개인·기타 {len(persons)}")
    print(f"표본 {min(limit, len(orgs))}건 조회 (GLEIF 전문 검색)\n")

    rows, hit = [], 0
    for i, n in enumerate(orgs[:limit]):
        lb = n["label"]
        plain = re.sub(r"\([^)]*\)", " ", lb).strip()
        try:
            recs = gleif(lb)
            if plain and plain != lb:
                recs = recs + gleif(plain)
                time.sleep(0.7)
        except Exception as e:                       # 네트워크·한도는 실패로 기록
            rows.append({"label": lb, "status": "ERROR", "detail": str(e)[:80]})
            continue
        tq = core_tokens(lb)
        best = None
        for rec in recs:
            for cand in names_of(rec):
                tc = core_tokens(cand)
                if covers(tq, tc):                   # 질의 토큰의 대부분이 후보에
                    best = (rec["id"], cand,
                            rec["attributes"]["registration"]["status"],
                            rec["attributes"]["entity"]["status"])
                    break
            if best:
                break
        if best:
            hit += 1
            rows.append({"label": lb, "status": "MATCH", "lei": best[0],
                         "gleif_name": best[1], "registration": best[2],
                         "entity": best[3]})
            print(f"  [{best[2]:9}] {lb[:44]:44} -> {best[0]}")
        else:
            rows.append({"label": lb, "status": "NO_MATCH", "returned": len(recs)})
        time.sleep(0.7)                              # 예의상 간격

    n_probe = len([r for r in rows if r["status"] != "ERROR"])
    rate = hit / n_probe if n_probe else 0.0
    print(f"\n표본 해소 {hit}/{n_probe} = {rate:.0%}")
    lapsed = sum(1 for r in rows if r.get("registration") == "LAPSED")
    if hit:
        print(f"  그중 등록 실효(LAPSED) {lapsed}건 = 해소분의 {lapsed/hit:.0%}")

    OUT.mkdir(exist_ok=True)
    (OUT / "lei_resolution_probe.json").write_text(json.dumps({
        "source": src.name,
        "sanctioned_total": len(sanc),
        "organization_like": len(orgs),
        "person_or_other": len(persons),
        "probed": n_probe,
        "matched": hit,
        "match_rate": round(rate, 4),
        "lapsed_among_matched": lapsed,
        "rows": rows,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"저장 -> out/lei_resolution_probe.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
