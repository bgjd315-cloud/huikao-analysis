#!/usr/bin/env python3
"""學測地科：從學測自然資料抽出地球科學題，加上細分單元 → data/xuece-earth/<年>.json。

用法：python tools/xuece/merge_earth.py 115 [116 ...]
前置：先完成 merge_science.py（data/xuece-sci/<年>.json）；題目圖片沿用 xuece-sci/pages。
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from classify_earth import UNIT  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]


def merge(y):
    d = json.loads((ROOT / "data" / "xuece-sci" / f"{y}.json").read_text("utf-8"))
    ex, rows = d["json:examData"], d["js:Q"]
    idx = [i for i, r in enumerate(rows) if r[0] == "E"]
    units = UNIT[y]
    if len(units) != len(idx):
        sys.exit(f"[錯誤] {y}：地科 {len(idx)} 題，單元 {len(units)} 個")
    if set(units) - set("SAOGC"):
        sys.exit(f"[錯誤] {y}：單元代號錯誤 {set(units) - set('SAOGC')}")
    qs, out = [], []
    for i, u in zip(idx, units):
        _, lab, ans, pts, part = rows[i]
        q = ex["q"][i]
        ns = ans in ("／", "/")
        kind = "非選擇題" if ns else "多選題" if len(re.sub(r"[^A-E]", "", ans.split("或")[0])) > 1 else "單選題"
        qs.append({"lab": str(q["n"]), "s": q["s"], "t": q["t"]})
        out.append([part, kind, u, lab, ans, pts])
    nums = {int(q["lab"]) for q in qs}
    groups = [g for g in ex["g"] if any(g["a"] <= n <= g["b"] for n in nums)]
    data = {"json:examData": {"w": ex["w"], "h": ex["h"], "q": qs, "g": groups}, "js:Q": out}
    p = ROOT / "data" / "xuece-earth" / f"{y}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), "utf-8")
    c = {k: sum(r[5] for r in out if r[2] == k) for k in "SAOGC"}
    print(f"{y}：地科 {len(out)} 題、{sum(r[5] for r in out)} 分，單元配分 {c}")


if __name__ == "__main__":
    for y in sys.argv[1:]:
        merge(int(y))
