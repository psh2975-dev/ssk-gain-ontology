# -*- coding: utf-8 -*-
"""배포본 한 번에 검증하기 (Run all checks).

이 배포본만으로 실행 가능한 검사를 순서대로 돌리고 결과를 한 표로 보고한다.
원자료가 필요한 스크립트는 그 사실을 표시하고 건너뛴다.

  python verify_all.py

Requires Python 3.11+ with rdflib, owlrl, pyshacl.
Scripts needing the excluded source data are reported as skipped, not failed.
Failures print the underlying output so the cause is visible.

주의: 이 스크립트는 ontology.ttl·shapes.ttl 을 재생성한 뒤 그 파일을 검증한다.
두 개를 동시에 실행하면 한쪽이 쓰는 중인 파일을 다른 쪽이 읽어 실패할 수 있다.
한 번에 하나만 실행할 것.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

# 콘솔 인코딩 방어. 윈도 기본 콘솔(cp949 등)에서 비ASCII 출력이 죽지 않게 한다.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
PY = sys.executable

# 하위 스크립트도 같은 조건에서 돌린다(각 스크립트가 자체 방어를 갖지만 이중 안전).
CHILD_ENV = {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}

# (표시명, 작업 디렉터리, 스크립트, 원자료 필요 여부)
STEPS = [
    ("Regenerate ontology      build_ontology",    "system/ontology", "build_ontology.py",     False),
    ("Regenerate shapes        build_shapes",      "system/ontology", "build_shapes.py",       False),
    ("Validation, 11 checks     validate",          "system/ontology", "validate.py",           False),
    ("Structural metrics       ontology_metrics",  "system/ontology", "ontology_metrics.py",   False),
    ("Vocabulary traceability  traceability_audit","system/ontology", "traceability_audit.py", False),
    ("OntoClean meta-property  ontoclean_audit", "system/ontology", "ontoclean_audit.py", False),
    ("Third-party reuse demo   reuse_demo",        "system/kg",       "reuse_demo.py",         False),
    ("Materialise graphs       materialize_pilot_kg", "system/kg",    "materialize_pilot_kg.py", True),
    ("Competency question runs run_cq_queries",    "system/kg",       "run_cq_queries.py",     True),
    # 마지막에 둔다: 위의 재생성 단계들이 실제로 아카이브된 바이트를 재현했는지를
    # 매니페스트 대조로 증명한다. 하나라도 다르면 결정론 주장이 성립하지 않는다.
    ("Checksum manifest       make_checksums --check", ".",           "make_checksums.py --check", False),
]


def main() -> int:
    print("=" * 72)
    print("Verifying the deposited release")
    print("=" * 72)
    rows, failed, details = [], 0, []
    for name, cwd, script, needs_data in STEPS:
        r = subprocess.run([PY, *script.split()], cwd=str(HERE / cwd),
                           capture_output=True, text=True,
                           encoding="utf-8", errors="replace", env=CHILD_ENV)
        out = (r.stdout or "") + (r.stderr or "")
        if r.returncode == 0:
            verdict = "PASS"
        elif needs_data and r.returncode == 2:
            verdict = "SKIP (source data needed)"
        else:
            verdict = f"FAIL (exit {r.returncode})"
            failed += 1
            details.append((name, script, out))
        rows.append((name, verdict, out.strip().split("\n")[-1][:60]))
        print(f"  {verdict:<20} {name}")

    # 실패는 마지막 한 줄로 알 수 없다. 원인을 그대로 보여준다.
    for name, script, out in details:
        print("\n" + "=" * 72)
        print(f"Failure detail: {name}  ({script})")
        print("=" * 72)
        tail = out.strip().split("\n")
        print("\n".join(tail[-25:]) if len(tail) > 25 else out.strip())

    print("-" * 72)
    print(f"{'Step':<34}{'Verdict':<20}Last line")
    print("-" * 72)
    for name, verdict, tail in rows:
        print(f"{name:<34}{verdict:<20}{tail}")
    print("-" * 72)

    print("\n산출물 위치 (Where the outputs are):")
    for f in sorted((HERE / "system" / "kg" / "out").glob("*")):
        print(f"  {f.relative_to(HERE)}   {f.stat().st_size:,} bytes")
    for f in sorted((HERE / "system" / "ontology").glob("*.ttl")):
        print(f"  {f.relative_to(HERE)}   {f.stat().st_size:,} bytes")

    if failed:
        print(f"\n실패 {failed}건. 위 표의 FAIL 항목을 확인할 것.")
        return 1
    print("\n이 배포본으로 가능한 검사는 모두 통과했다.")
    print("The SKIP steps need source records that may not be redistributed")
    print("(UN Comtrade, ETO); their outputs are enclosed in system/kg/out/.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
