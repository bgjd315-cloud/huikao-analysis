#!/usr/bin/env python3
"""學測自然：合併擷取結果、逐題分類與官方非選配分 → data/xuece-sci/<年>.json。

用法：python tools/xuece/merge_science.py 115 [116 ...]
107–110 年：第壹部分 80 分＋第貳部分（選答，上限 48 分）＝128 分；
111 年起：選擇題 72 分＋混合題 56 分＝128 分。
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from classify_science import NS_PTS, Q  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
INC = ROOT / "incoming" / "xuece"
CODES = {"P", "C", "B", "E"}


def merge(y):
    d = json.loads((INC / f"extract-sci-{y}.json").read_text("utf-8"))
    cls, err = Q[y], []
    if len(cls) != len(d["q"]):
        sys.exit(f"[錯誤] {y}：分類 {len(cls)} 題，試卷 {len(d['q'])} 題")
    ns = [q["n"] for q in d["q"] if q["ans"] in ("／", "/")]
    official = NS_PTS.get(y, {})
    if sorted(official) != sorted(ns):
        err.append(f"非選題號不符：試卷 {ns}，評分原則 {sorted(official)}")
    old = y < 111
    rows = []
    for q, (code, lab) in zip(d["q"], cls):
        n = q["n"]
        if code not in CODES:
            err.append(f"第 {n} 題代號錯誤：{code}")
        is_ns = n in ns
        if is_ns != lab.startswith("非選"):
            err.append(f"第 {n} 題{'是' if is_ns else '不是'}非選題，但考點說明{'沒' if is_ns else ''}標「非選」")
        pts = official.get(n) if is_ns else 2
        second = d["mixed_from"] and n >= d["mixed_from"]
        part = ("第貳部分" if second else "第壹部分") if old else ("混合題" if second else "選擇題")
        rows.append([code, lab, q["ans"], pts, part])
        q.pop("ans", None)
        q.pop("pts", None)
    first = sum(r[3] for r in rows if r[4] in ("第壹部分", "選擇題"))
    second = sum(r[3] or 0 for r in rows) - first
    want = (80, 56) if old else (72, 56)
    if (first, second) != want:
        err.append(f"配分 {first}＋{second}，應為 {want[0]}＋{want[1]}")
    if err:
        sys.exit(f"[錯誤] {y}：" + "；".join(err))
    d.pop("mixed_from", None)
    out = {"json:examData": d, "js:Q": rows}
    p = ROOT / "data" / "xuece-sci" / f"{y}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), "utf-8")
    c = {s: sum(1 for r in rows if r[0] == s) for s in "PCBE"}
    print(f"{y}：{len(rows)} 題，物理 {c['P']}、化學 {c['C']}、生物 {c['B']}、地科 {c['E']}")


if __name__ == "__main__":
    for y in sys.argv[1:]:
        merge(int(y))
