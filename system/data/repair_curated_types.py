# -*- coding: utf-8 -*-
"""큐레이션 원자료의 ontology_classes 오분류 수리 (재현 가능, 손편집 아님).

배경:
  OFAC 원자료 일부가 조치와 그 대상을 함께 타입으로 갖는다. 곧
  intl:FinancialSanction(core:Policy 하위)이면서 동시에
  intl:SanctionedEntity(core:Organization 하위)인 노드다.

판정 근거:
  같은 노드의 rdf_type 필드가 정본이며 SanctionedEntity 를 가리킨다.
  프로그램 수준 제재는 materialize_pilot_kg.py 가 별도 노드로 실체화하므로,
  엔티티에 붙은 조치 타입은 중복이자 오류다.

큐레이터의 의도(이 대상이 금융제재를 받는다)를 표현할 어휘는 이미 있다:
  intl:financiallySanctions (정의역 FinancialSanction, 치역 Organization).
  타입이 아니라 관계로 표현해야 한다. 그 관계 부여는 프로그램별 제재 유형
  판정을 요구하므로 별도 큐레이션 결정으로 남긴다(이 스크립트 범위 밖).

사용: python repair_curated_types.py [--apply]
      기본은 건조 실행(변경 없이 보고). --apply 로 실제 기록.
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

# 조치(Policy 하위)와 개체(Organization·Country·Product 하위)는 존재론적 범주가
# 다르므로 한 노드에 함께 올 수 없다. 왼쪽이 오면 오른쪽과 공존 금지.
POLICY_CLASSES = {
    "intl:Sanction", "intl:FinancialSanction", "intl:TechTransferBan",
    "intl:InvestmentRestriction", "intl:ExportControl", "intl:TradeMeasure",
}
ENTITY_CLASSES = {
    "intl:SanctionedEntity", "core:Organization", "gvc:Company",
    "core:Country", "core:Product",
}


def repair_node(n: dict) -> list[str]:
    """반환 = 제거한 클래스 목록. rdf_type 을 정본으로 삼는다."""
    classes = list(n.get("ontology_classes") or [])
    if not (set(classes) & POLICY_CLASSES and set(classes) & ENTITY_CLASSES):
        return []
    rdf_type = str(n.get("rdf_type") or "")
    if not rdf_type:
        return []                      # 정본이 없으면 판정하지 않는다
    local = rdf_type.rsplit("#", 1)[-1]
    keep_side = ENTITY_CLASSES if any(
        c.endswith(local) for c in ENTITY_CLASSES) else POLICY_CLASSES
    drop_side = POLICY_CLASSES if keep_side is ENTITY_CLASSES else ENTITY_CLASSES
    removed = [c for c in classes if c in drop_side]
    if removed:
        n["ontology_classes"] = [c for c in classes if c not in drop_side]
    return removed


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="실제 파일에 기록")
    a = ap.parse_args()

    if not CURATED.exists() or not any(CURATED.glob("*.json")):
        print("""원자료(curated/*.json) 없음: 이 배포본에는 라이선스상 제외된
원자료가 없어 수리기는 절차 공개용이다. 원자료를 확보해 curated/ 에 두면
동일 절차가 재현된다.""")
        return 2

    total_files = total_fixed = 0
    for p in sorted(CURATED.glob("*.json")):
        d = json.load(io.open(p, encoding="utf-8"))
        raw = d.get("nodes")
        nodes = raw if isinstance(raw, list) else list((raw or {}).values())
        fixed = []
        for n in nodes:
            removed = repair_node(n)
            if removed:
                fixed.append((n.get("_node_id") or n.get("canonicalId"), removed))
        if not fixed:
            continue
        total_files += 1
        total_fixed += len(fixed)
        print(f"{p.name}: {len(fixed)}건")
        for nid, removed in fixed[:3]:
            print(f"   {nid}: -{removed}")
        if len(fixed) > 3:
            print(f"   … 외 {len(fixed) - 3}건")
        if a.apply:
            io.open(p, "w", encoding="utf-8", newline="\n").write(
                json.dumps(d, ensure_ascii=False, indent=2) + "\n")

    if total_fixed == 0:
        print("오분류 없음: 수리할 것이 없습니다.")
        return 0
    print(f"\n합계 {total_files}개 파일 {total_fixed}건",
          "기록 완료" if a.apply else "(건조 실행, --apply 로 기록)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
