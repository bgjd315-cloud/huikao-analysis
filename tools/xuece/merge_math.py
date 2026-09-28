#!/usr/bin/env python3
"""學測數學：合併擷取結果與單元分類 → data/xuece-math/<年>.json（一年可含數A、數B兩份試卷）。

用法：python tools/xuece/merge_math.py 115 [116 ...]
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from classify_math import Q  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
INC = ROOT / "incoming" / "xuece"
UNITS = set("NFXQCPDTLVSMKGZ")


def merge(y):
    ex_all, q_all, err = {}, {}, []
    for t in ("m", "ma", "mb", "mj"):
        f = INC / f"extract-math-{y}-{t}.json"
        if not f.exists():
            continue
        d = json.loads(f.read_text("utf-8"))
        cls = Q.get(f"{y}-{t}")
        if not cls or len(cls) != len(d["q"]):
            err.append(f"{t} 分類 {len(cls or [])} 題，試卷 {len(d['q'])} 題")
            continue
        rows = []
        for q, (u, lab) in zip(d["q"], cls):
            if u not in UNITS:
                err.append(f"{t} 第 {q['lab']} 題單元代號錯誤：{u}")
            sec, ans, pts = q["sec"], q["ans"], q.get("pts")
            if sec == "混合題":
                flat = re.sub(r"\s+", "", q["t"])
                m = re.search(r"[（(](單選題|多選題|選填題|非選擇題)[，,]", flat)
                kind = m[1] if m else ("非選擇題" if ans in ("／", "/") else "選填題" if " " in ans else "單選題")
            else:
                kind = sec
            rows.append([sec, kind, u, lab, ans, pts])
        # 題末配分被數學式干擾而抓不到時，以全卷 100 分推回（最多只允許缺一題）
        mixed = [r for r in rows if r[0] == "混合題"]
        missing = [r for r in mixed if r[5] is None]
        if len(missing) == 1:
            missing[0][5] = 100 - sum(r[5] for r in rows if r[5] is not None)
        total = sum(r[5] or 0 for r in rows)
        if total != 100:
            err.append(f"{t} 全卷配分合計 {total}，應為 100")
        for q in d["q"]:
            q.pop("ans", None)
            q.pop("sec", None)
        ex_all[t] = d
        q_all[t] = rows
    if err or not q_all:
        sys.exit(f"[錯誤] {y}：" + "；".join(err or ["找不到擷取結果"]))
    out = {"json:examData": ex_all, "js:Q": q_all}
    p = ROOT / "data" / "xuece-math" / f"{y}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), "utf-8")
    for t, rows in q_all.items():
        u = {}
        for r in rows:
            u[r[2]] = u.get(r[2], 0) + 1
        print(f"{y}-{t}：{len(rows)} 題、100 分，單元 {dict(sorted(u.items(), key=lambda x: -x[1]))}")


if __name__ == "__main__":
    for y in sys.argv[1:]:
        merge(int(y))
