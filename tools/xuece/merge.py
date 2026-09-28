#!/usr/bin/env python3
"""把 extract.py 的結果、非選擇題參考答案、逐題分類合併成 data/xuece/<年>.json，並做一致性檢查。

用法：python tools/xuece/merge.py 115 [116 ...]
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from classify import GROUPS, Q  # noqa: E402
from parse_nonchoice import parse as parse_ns  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
INC = ROOT / "incoming" / "xuece"
MATS = set("KLBIPNWC")


def merge(y):
    d = json.loads((INC / f"extract-{y}.json").read_text("utf-8"))
    ex, ans, st = d["json:examData"], d["js:ANS"], d["js:STRUCT"]
    q, groups = Q[y], GROUPS[y]
    err = []
    if len(q) != len(ans):
        err.append(f"分類 {len(q)} 題，答案 {len(ans)} 題")
    err += [f"第 {i+1} 題取材代號錯誤：{m}" for i, (m, _) in enumerate(q) if m not in MATS]
    got = [f"{g['a']}–{g['b']}" for g in ex["g"]]
    want = [g[0] for g in groups]
    if got != want:
        err.append(f"題組範圍不符：試卷 {got}，分類表 {want}")
    ns = {}
    nsf = INC / f"{y}-nonchoice.pdf"
    if nsf.exists():
        ns = parse_ns(nsf)
        slash = [i + 1 for i, a in enumerate(ans) if a in ("／", "/")]
        if sorted(ns) != slash:
            err.append(f"非選題號不符：答案表 {slash}，評分原則 {sorted(ns)}")
        for n in ns:
            if not q[n - 1][1].startswith("非選"):
                err.append(f"第 {n} 題是非選題，但分類說明沒標「非選」")
    if err:
        sys.exit(f"[錯誤] {y}：" + "；".join(err))
    out = {
        "json:examData": ex,
        "js:ANS": ans,
        "js:STRUCT": st,
        "js:Q": [list(x) for x in q],
        "js:GROUPS": groups,
        "js:NS": {str(k): v for k, v in ns.items()},
    }
    p = ROOT / "data" / "xuece" / f"{y}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), "utf-8")
    cnt = {m: sum(1 for x, _ in q if x == m) for m in "KLBIPNWC"}
    print(f"{y}：{len(q)} 題 → {p.relative_to(ROOT)}  {cnt}")


if __name__ == "__main__":
    for y in sys.argv[1:]:
        merge(int(y))
