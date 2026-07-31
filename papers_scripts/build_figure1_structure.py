# -*- coding: utf-8 -*-
"""Figure 2 생성: 온톨로지 전체 구조와 세 종류의 결합.

표 2는 다섯 관계의 정의역·치역을 규정하나, 그 관계들이 서로 다른 방식으로 두 도메인을
잇는다는 사실은 표로 드러나지 않는다. 이 그림은 셋을 구분해 보인다.
  (a) 끝점이 서로 다른 모듈에 있는 관계
  (b) 끝점이 한 모듈 안에 있으나 판정에 다른 도메인의 사실을 요구하는 관계
  (c) 정준 식별자에 의한 수직 결합

클래스명·관계명·정의역·치역은 ontology.ttl 에서 읽는다. 손으로 적지 않는다.
배치(행 순서)만 사람이 정한다. 자동 배치는 라벨이 겹쳐 판독 불가.
논문 순흑 표준에 따라 색·음영을 쓰지 않는다.

실행: $env:PYTHONUTF8=1; python build_figure2_join.py
"""
from __future__ import annotations

import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
from rdflib import Graph, Namespace, RDFS, OWL
from rdflib.collection import Collection

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
ONT = ROOT / "system" / "ontology" / "ontology.ttl"
OUT = HERE.parent / "draft" / "figures"

BASE = "https://w3id.org/ssk-gain/ontology/"
CORE, INTL = Namespace(BASE + "core#"), Namespace(BASE + "intl#")
GVC, BR = Namespace(BASE + "gvc#"), Namespace(BASE + "bridge#")

INK, GREY = "#000000", "#595959"

# 행 순서만 선언한다. 같은 행에 정의역과 치역을 두어 화살표가 수평이 되게 한다.
# 교차 끝점 셋을 위 세 행에 둔다. 화살표가 전부 수평이라 서로 교차하지 않는다.
CROSS_ROWS = [BR.disrupts, BR.affects, BR.restricts]
# 동일 모듈 끝점 둘은 아래 한 띠에 좌우로 나란히 둔다. 서로 간섭하지 않는다.
WITHIN_ROWS = [BR.circumvents, BR.exposes]

XI, XC, XG = 0.155, 0.50, 0.845      # intl 열 · 중앙 채널 · gvc 열
YS = [0.855, 0.745, 0.635]           # 교차 행
YW, YW2 = 0.495, 0.395               # 동일 모듈 띠(정의역·치역)
CORE_Y = 0.145


def local(u) -> str:
    return str(u).rsplit("#", 1)[-1]


def module_of(u) -> str:
    s = str(u)
    return s[len(BASE):].split("#")[0] if s.startswith(BASE) else "?"


def expand(g: Graph, node):
    """union range 를 구성 클래스 목록으로 편다."""
    if node is None:
        return []
    if (node, OWL.unionOf, None) in g:
        return list(Collection(g, next(g.objects(node, OWL.unionOf))))
    return [node]


def label_en(g: Graph, u) -> str:
    for o in g.objects(u, RDFS.label):
        if getattr(o, "language", None) == "en":
            return str(o)
    return local(u)


def box(ax, x, y, text, w=0.235, h=0.058, bold=False, fs=8.0):
    ax.add_patch(FancyBboxPatch((x - w / 2, y - h / 2), w, h,
                                boxstyle="round,pad=0.005", linewidth=1.15 if bold else 0.9,
                                edgecolor=INK, facecolor="white", zorder=4))
    ax.text(x, y, text, ha="center", va="center", fontsize=fs,
            fontweight="bold" if bold else "normal", zorder=5)


def arrow(ax, a, b, dashed=False, lw=1.2):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle="-|>", mutation_scale=10,
                                 linewidth=lw, color=GREY if dashed else INK,
                                 linestyle=(0, (3, 2.5)) if dashed else "solid",
                                 shrinkA=2, shrinkB=2, zorder=3))


def main() -> int:
    g = Graph().parse(str(ONT), format="turtle")

    fig, ax = plt.subplots(figsize=(7.6, 7.0))
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")

    # 도메인 영역
    for x, name in ((XI, "International relations (intl)"), (XG, "Supply chain (gvc)")):
        ax.add_patch(FancyBboxPatch((x - 0.145, 0.345), 0.29, 0.565,
                                    boxstyle="round,pad=0.008", linewidth=0.7,
                                    edgecolor=GREY, facecolor="none",
                                    linestyle=(0, (4, 3)), zorder=1))
        ax.text(x, 0.945, name, ha="center", va="center", fontsize=8.6, fontweight="bold")
    ax.text(XC, 0.945, "bridge", ha="center", va="center", fontsize=8.6,
            fontweight="bold", style="italic")
    # 모듈 구성. 종전 별도 그림이 담던 owl:imports 관계를 여기에 흡수했다.
    ax.text(XC, 0.905,
            "intl and gvc import core; bridge imports both and declares no classes",
            ha="center", va="center", fontsize=7.2, style="italic", color=GREY,
            bbox=dict(boxstyle="round,pad=0.28", facecolor="white", edgecolor="none"),
            zorder=6)

    n_cross = n_within = 0

    # --- 교차 끝점: 정의역과 치역을 같은 행에 두어 화살표를 수평으로 유지 ---
    for rel, y in zip(CROSS_ROWS, YS):
        dom = next(iter(g.objects(rel, RDFS.domain)), None)
        rngs = expand(g, next(iter(g.objects(rel, RDFS.range)), None))
        rmods = {module_of(r) for r in rngs}
        box(ax, XC, y, label_en(g, rel), w=0.2, h=0.05, fs=8.2)
        box(ax, XI, y, local(dom), fs=7.7)
        arrow(ax, (XI + 0.118, y), (XC - 0.1, y))
        n_cross += 1
        if rmods == {"core"}:
            # 치역이 공유 상위 계층이면 바로 아래로 내린다. Product 를 중앙에 두어
            # 수직 낙하가 다른 상자를 관통하지 않게 했다.
            arrow(ax, (XC, y - 0.026), (XC, CORE_Y + 0.032))
        else:
            lab = " / ".join(local(r) for r in rngs)
            box(ax, XG, y, lab, fs=6.9 if len(lab) > 16 else 7.7)
            arrow(ax, (XC + 0.1, y), (XG - 0.118, y))

    # --- 동일 모듈 끝점: 아래 한 띠에 좌우로 나란히. 서로 간섭하지 않는다 ---
    ax.text(XC, YW2 - 0.055, "endpoints within one module,",
            ha="center", va="center", fontsize=7.3, style="italic", color=GREY,
            bbox=dict(boxstyle="round,pad=0.18", facecolor="white", edgecolor="none"), zorder=6)
    ax.text(XC, YW2 - 0.079, "decided only with the other domain",
            ha="center", va="center", fontsize=7.3, style="italic", color=GREY,
            bbox=dict(boxstyle="round,pad=0.18", facecolor="white", edgecolor="none"), zorder=6)
    for rel in WITHIN_ROWS:
        dom = next(iter(g.objects(rel, RDFS.domain)), None)
        rng = expand(g, next(iter(g.objects(rel, RDFS.range)), None))[0]
        x = XI if module_of(dom) == "intl" else XG
        x_other = XG if x == XI else XI
        n_within += 1
        box(ax, x, YW, local(dom), fs=7.7)
        box(ax, x, YW2, local(rng), fs=7.7)
        # 관계 이름은 두 상자 사이 바깥쪽에 둔다(상자와 겹치지 않게).
        ax.text(x + (0.175 if x == XI else -0.175), (YW + YW2) / 2,
                label_en(g, rel), ha="center", va="center", fontsize=8.2,
                style="italic",
                bbox=dict(boxstyle="round,pad=0.25", facecolor="white",
                          edgecolor=INK, linewidth=0.9), zorder=5)
        arrow(ax, (x, YW - 0.029), (x, YW2 + 0.029))
        # 판정에 필요한 타 도메인 사실. 패널 경계까지만 긋는다.
        ymid = (YW + YW2) / 2
        if x == XI:
            arrow(ax, (x + 0.255, ymid), (XC - 0.055, ymid), dashed=True)
        else:
            arrow(ax, (x - 0.255, ymid), (XC + 0.055, ymid), dashed=True)

    # 공유 상위 계층. Product 를 중앙에 두어 restricts 의 수직 낙하를 받는다.
    ax.add_patch(FancyBboxPatch((0.035, 0.045), 0.93, 0.185,
                                boxstyle="round,pad=0.008", linewidth=0.7,
                                edgecolor=GREY, facecolor="none",
                                linestyle=(0, (4, 3)), zorder=1))
    ax.text(0.5, 0.212, "Shared upper layer (core): canonical identifiers join both domains",
            ha="center", va="center", fontsize=8.6, fontweight="bold")
    for x, cls, idr in ((0.185, CORE.Organization, "LEI (ISO 17442)"),
                        (XC, CORE.Product, "HS code"),
                        (0.815, CORE.Country, "ISO 3166-1 alpha-3")):
        box(ax, x, CORE_Y, local(cls), w=0.235, bold=True)
        ax.text(x, 0.093, idr, ha="center", va="center", fontsize=7.0,
                style="italic", color=GREY)

    # 수직 결합. 두 도메인의 개체가 같은 식별자면 하나의 노드가 된다.
    for x in (XI, XG):
        arrow(ax, (x, 0.325), (x, 0.243), dashed=True, lw=0.9)
    ax.text(XC, 0.283, "same identifier, one node", ha="center", va="center",
            fontsize=7.4, style="italic", color=GREY, bbox=dict(boxstyle="round,pad=0.18", facecolor="white", edgecolor="none"), zorder=6)

    ax.text(0.5, 0.008,
            "Solid: domain and range of a bridge relation.   "
            "Dashed: a fact required to decide it, or an identifier join.",
            ha="center", va="center", fontsize=7.4, color=GREY)

    OUT.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "svg"):
        p = OUT / f"figure1_ontology_structure.{ext}"
        fig.savefig(p, dpi=300 if ext == "png" else None,
                    bbox_inches="tight", facecolor="white")
        print(f"저장 -> {p.name}")
    print(f"교차 끝점 {n_cross} · 동일 모듈 끝점 {n_within} (ontology.ttl 실측)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
