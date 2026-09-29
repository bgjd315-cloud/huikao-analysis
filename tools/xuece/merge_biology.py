#!/usr/bin/env python3
"""分科生物：合併擷取結果、單元分類與官方非選配分 → data/xuece-bio/<年>.json。

用法：python tools/xuece/merge_biology.py 115 [116 ...]
擷取：python tools/xuece/extract_math.py 115-bi（與數甲、物理、化學共用程式）
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from classify_biology import NS_PTS, Q  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
INC = ROOT / "incoming" / "xuece"
UNITS = set("CGAIPE")


def merge(y):
    d = json.loads((INC / f"extract-bio-{y}-bi.json").read_text("utf-8"))
    cls, err = Q[y], []
    if len(cls) != len(d["q"]):
        sys.exit(f"[錯誤] {y}：分類 {len(cls)} 題，試卷 {len(d['q'])} 題")
    ns = [q["lab"] for q in d["q"] if q["ans"] in ("／", "/")]
    if sorted(ns) != sorted(NS_PTS[y]):
        err.append(f"非選題號不符：試卷 {ns}，評分原則 {sorted(NS_PTS[y])}")
    rows = []
    for q, (u, lab) in zip(d["q"], cls):
        n, sec, ans = q["lab"], q["sec"], q["ans"]
        if u not in UNITS:
            err.append(f"第 {n} 題單元代號錯誤：{u}")
        is_ns = ans in ("／", "/")
        if is_ns != lab.startswith("非選"):
            err.append(f"第 {n} 題{'是' if is_ns else '不是'}非選題，但考點說明{'沒' if is_ns else ''}標「非選」")
        if is_ns:
            pts = NS_PTS[y].get(n)
        else:  # 選擇題：107–110 年單選每題 1 分，其餘每題 2 分
            pts = 1 if y < 111 and sec == "單選題" else 2
        kind = "非選擇題" if is_ns else "多選題" if len(re.sub(r"[^A-E]", "", ans.split("或")[0])) > 1 else "單選題"
        rows.append([sec, kind, u, lab, ans, pts])
        for k in ("ans", "sec", "pts"):
            q.pop(k, None)
    total = sum(r[5] or 0 for r in rows)
    if total != 100:
        err.append(f"配分合計 {total}，應為 100")
    if err:
        sys.exit(f"[錯誤] {y}：" + "；".join(err))
    out = {"json:examData": d, "js:Q": rows}
    p = ROOT / "data" / "xuece-bio" / f"{y}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), "utf-8")
    c = {k: sum(r[5] for r in rows if r[2] == k) for k in "CGAIPE"}
    print(f"{y}：{len(rows)} 題、100 分，單元配分 {c}")


if __name__ == "__main__":
    for y in sys.argv[1:]:
        merge(int(y))
