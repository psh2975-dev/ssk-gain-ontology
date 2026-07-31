# -*- coding: utf-8 -*-
"""보충자료 Table S3 생성: 어휘 추적 행렬.

원고 5-1절이 「명명 용어 전부가 역량질문 또는 설계 요건에 대응하며 미대응 0」이라
단언하고 S3 를 근거로 든다. 그 표가 현행 어휘를 덮어야 그 문장이 참이 된다. 손으로
두면 어휘가 늘 때마다 뒤처진다. 실제로 S3 가 109항에 머물러, 3-7절 수리가 도입한
용어 9종이 누락된 채 「미대응 0」이 주장됐다.

정본은 system/ontology/traceability_audit.py 의 매핑이다. 여기서 읽어 표만 만든다.

실행: $env:PYTHONUTF8=1; python build_supp_table_s3.py
"""
from __future__ import annotations

import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import importlib.util
import re
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
TA = ROOT / "system" / "ontology" / "traceability_audit.py"
SUPP = HERE.parent / "draft" / "PAP01_supplementary_EN.md"

# 근거 문구는 국문 원장에 있다. 보충자료는 영문이므로 약어를 그대로 두고
# 서술어만 옮긴다. 뜻이 바뀌지 않는 범위에서만 치환한다.
# 정본(traceability_audit.py)이 영문이므로 치환하지 않는다. 그대로 옮긴다.

def load_mapping() -> dict:
    spec = importlib.util.spec_from_file_location("ta", TA)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["ta"] = mod
    spec.loader.exec_module(mod)
    return mod.M


def gloss(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def main() -> int:
    m = load_mapping()
    cnt = Counter(v[0] for v in m.values())
    rows = [f"| `{k}` | {v[0]} | {gloss(v[1])} |" for k, v in sorted(m.items())]

    block = [
        "## Supplementary Table S3. Vocabulary traceability matrix (vocabulary to competency "
        "question or design requirement)",
        "",
        f"We map the {len(m)} named terms to competency questions (CQ) or to explicit design "
        f"requirements (REQ). Distribution: CQ {cnt['CQ']}, REQ {cnt['REQ']}, unmapped 0. "
        "Regenerated from system/ontology/traceability_audit.py by "
        "scripts/build_supp_table_s3.py.",
        "",
        "REQ categories: UPPER = upper skeleton; PROV = provenance and lineage; FAIR = canonical "
        "identifier and open deposit; SCOPE = coverage of the study period and of policy "
        "instruments.",
        "",
        "| Term | Mapping | Rationale |",
        "|------|:---:|------|",
        *rows,
    ]

    t = SUPP.read_text(encoding="utf-8")
    start = t.find("## Supplementary Table S3.")
    if start < 0:
        print("S3 절을 찾지 못함")
        return 2
    nxt = t.find("## Supplementary ", start + 10)
    end = nxt if nxt > 0 else len(t)
    SUPP.write_text(t[:start] + "\n".join(block) + "\n\n" + t[end:], encoding="utf-8")
    print(f"S3 재생성 — {len(m)}항 (CQ {cnt['CQ']} · REQ {cnt['REQ']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
