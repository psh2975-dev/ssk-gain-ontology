# -*- coding: utf-8 -*-
"""국가 코드 정준화 수리 (재현 가능, 손편집 아님).

배경:
  core:Country 는 정준 식별자를 ISO 3166-1 alpha-3 로 규정하지만, 원자료
  curated_intl_*.json 의 국가 코드 필드에 alpha-2 가 섞여 들어온다. 같은 국가가
  다른 소스에서 alpha-3 로 들어오면 별개 노드가 되므로 정준화가 필요하다.

수리:
  pycountry 없이 결정론적으로 처리한다. 각 노드가 이미 보유한 alpha-3 값
  (iso_alpha3 / isoAlpha3 필드)이 있으면 그것을 canonical_id 로 삼고, 없으면
  아래 표준 대응표(ISO 3166-1 공표값)를 쓴다. 추측 매핑은 하지 않는다.

사용: python repair_country_codes.py [--apply]
      기본은 건조 실행(변경 없이 보고).
"""

# 콘솔 인코딩 방어. 윈도 기본 콘솔(cp949 등)에서는 비ASCII 문자를 출력할 때
# UnicodeEncodeError 로 죽는다. 표준 출력만 UTF-8 로 재설정한다.
import sys as _sys
if hasattr(_sys.stdout, "reconfigure"):
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import argparse
import io
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CURATED = HERE / "curated"

# ISO 3166-1 공표 대응(alpha-2 → alpha-3). 본 파일럿에서 실제로 등장한 값만 둔다.
ALPHA2_TO_3 = {
    "ES": "ESP",   # Spain
    "LB": "LBN",   # Lebanon
    "MX": "MEX",   # Mexico
    "PM": "SPM",   # Saint Pierre and Miquelon
}

CODE_FIELDS = ("country_iso3", "iso_alpha3", "isoAlpha3")


def fix_node(n: dict) -> list[str]:
    """노드 하나를 수리하고 변경 내역을 반환."""
    changes = []
    for f in CODE_FIELDS:
        v = n.get(f)
        if isinstance(v, str) and len(v) == 2:
            a3 = ALPHA2_TO_3.get(v.upper())
            if a3:
                n[f] = a3
                changes.append(f"{f}: {v} -> {a3}")
    # canonicalId(및 스네이크 표기)가 alpha-2 면 같은 노드의 alpha-3 로 교체.
    # 국가 노드만 대상, 조직·품목의 canonicalId 는 다른 체계다.
    is_country = "core:Country" in (n.get("ontology_classes") or [])
    for cid_field in ("canonicalId", "canonical_id"):
        cid = n.get(cid_field)
        if is_country and isinstance(cid, str) and len(cid) == 2:
            a3 = next((n[f] for f in CODE_FIELDS
                       if isinstance(n.get(f), str) and len(n[f]) == 3), None) \
                or ALPHA2_TO_3.get(cid.upper())
            if a3:
                n[cid_field] = a3
                changes.append(f"{cid_field}: {cid} -> {a3}")
                # 라벨이 코드 자체면 함께 갱신(라벨 'LB' → 'LBN')
                if n.get("label") == cid:
                    n["label"] = a3
                    changes.append(f"label: {cid} -> {a3}")
    # id 가 country:XX 형태면 함께 정정(그래프 IRI 결정 요소)
    nid = n.get("id")
    if isinstance(nid, str) and nid.startswith("country:"):
        code = nid.split(":", 1)[1]
        if len(code) == 2:
            a3 = ALPHA2_TO_3.get(code.upper())
            if a3:
                n["id"] = f"country:{a3}"
                changes.append(f"id: {nid} -> country:{a3}")
    return changes


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    if not CURATED.exists() or not any(CURATED.glob("curated_intl_*.json")):
        print("""원자료(curated/curated_intl_*.json) 없음: 이 배포본에는 라이선스상
제외된 원자료가 없어 수리기는 절차 공개용이다. 원자료를 확보해 curated/ 에 두면
동일 절차가 재현된다.""")
        return 2

    total = 0
    for path in sorted(CURATED.glob("curated_intl_*.json")):
        data = json.loads(io.open(path, encoding="utf-8").read())
        nodes = data.get("nodes", [])
        edits = []
        for n in nodes:
            for c in fix_node(n):
                edits.append(f"{n.get('id', '?')}  {c}")
        # 간선의 종단 참조도 country:XX 를 쓰면 함께 정정
        for e in data.get("edges", []):
            for k in ("source", "target", "source_node"):
                v = e.get(k)
                if isinstance(v, str) and v.startswith("country:"):
                    code = v.split(":", 1)[1]
                    if len(code) == 2 and code.upper() in ALPHA2_TO_3:
                        e[k] = f"country:{ALPHA2_TO_3[code.upper()]}"
                        edits.append(f"edge.{k}: {v} -> {e[k]}")
        if edits:
            total += len(edits)
            print(f"[{path.name}] {len(edits)}건")
            for x in edits[:12]:
                print("   ", x)
            if a.apply:
                io.open(path, "w", encoding="utf-8").write(
                    json.dumps(data, ensure_ascii=False, indent=1))
    if total == 0:
        print("정준화 위반 없음: 수리할 것이 없습니다.")
        return 0
    print(f"\n총 {total}건" + (" 적용됨" if a.apply else " (건조 실행, --apply 로 기록)"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
