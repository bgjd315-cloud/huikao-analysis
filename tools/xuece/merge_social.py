#!/usr/bin/env python3
"""學測社會：合併擷取結果、逐題分類與官方非選配分 → data/xuece-soc/<年>.json。

用法：python tools/xuece/merge_social.py 115 [116 ...]
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from classify_social import NS_PTS, Q  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
INC = ROOT / "incoming" / "xuece"
CODES = {"HT", "HC", "HW", "GP", "GH", "GR", "GS", "CP", "CL", "CE", "CS"}


def merge(y):
    d = json.loads((INC / f"extract-soc-{y}.json").read_text("utf-8"))
    cls, err = Q[y], []
    if len(cls) != len(d["q"]):
        sys.exit(f"[錯誤] {y}：分類 {len(cls)} 題，試卷 {len(d['q'])} 題")
    ns = [q["n"] for q in d["q"] if q["ans"] in ("／", "/")]
    official = NS_PTS.get(y, {})
    if sorted(official) != sorted(ns):
        err.append(f"非選題號不符：試卷 {ns}，評分原則 {sorted(official)}")
    rows = []
    for q, (code, lab) in zip(d["q"], cls):
        n = q["n"]
        if code not in CODES:
            err.append(f"第 {n} 題代號錯誤：{code}")
        is_ns = n in ns
        if is_ns != lab.startswith("非選"):
            err.append(f"第 {n} 題{'是' if is_ns else '不是'}非選題，但考點說明{'沒' if is_ns else ''}標「非選」")
        pts = official.get(n) if is_ns else 2
        part = "混合題" if d["mixed_from"] and n >= d["mixed_from"] else "單選題"
        rows.append([code, lab, q["ans"], pts, part])
        q.pop("ans", None)
        q.pop("pts", None)
    total = sum(r[3] or 0 for r in rows)
    if total != 144:
        err.append(f"配分合計 {total}，應為 144")
    if err:
        sys.exit(f"[錯誤] {y}：" + "；".join(err))
    d.pop("mixed_from", None)
    out = {"json:examData": d, "js:Q": rows}
    p = ROOT / "data" / "xuece-soc" / f"{y}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), "utf-8")
    subj = {s: sum(1 for r in rows if r[0][0] == s) for s in "HGC"}
    print(f"{y}：{len(rows)} 題、144 分，歷史 {subj['H']}、地理 {subj['G']}、公民 {subj['C']}")


if __name__ == "__main__":
    for y in sys.argv[1:]:
        merge(int(y))
