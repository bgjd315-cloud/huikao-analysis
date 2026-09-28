#!/usr/bin/env python3
"""學測社會：試卷切圖、逐題切片、題組、答案與配分擷取。

用法：python tools/xuece/extract_social.py 115 [116 ...]
輸入：incoming/xuece/<年>-s-paper.pdf、<年>-s-ans.pdf
輸出：assets/xuece-soc/pages/<年>-<頁>.webp、incoming/xuece/extract-soc-<年>.json
"""
import json
import re
import sys
from pathlib import Path

import pymupdf
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from extract import BOTTOM, SCALE, content_boxes, region, text_of  # noqa: E402
from markers import GRE, QRE, lines  # noqa: E402
from parse_ans import parse  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
INC = ROOT / "incoming" / "xuece"
OUT = ROOT / "assets" / "xuece-soc" / "pages"
PART2 = re.compile(r"^\s*第貳部分")


CN = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6}


def ns_points(text):
    """非選題配分：加總題中所有「（N分…）」「（一項N分，共M項…）」標註。"""
    flat = re.sub(r"\s", "", text)
    total = 0
    for m in re.finditer(r"[（(](?:[一每]項)?(\d+)分(?:[，,]共([一二三四五六\d])項)?", flat):
        k = m[2]
        total += int(m[1]) * (int(k) if k and k.isdigit() else CN.get(k, 1))
    return total or None


def extract(year):
    doc = pymupdf.open(INC / f"{year}-s-paper.pdf")
    OUT.mkdir(parents=True, exist_ok=True)
    for pn in range(1, len(doc)):
        pix = doc[pn].get_pixmap(matrix=pymupdf.Matrix(SCALE, SCALE))
        Image.frombytes("RGB", (pix.width, pix.height), pix.samples).save(
            OUT / f"{year}-{pn}.webp", "WEBP", quality=80, method=6)
    boxes = {pn: content_boxes(doc[pn]) for pn in range(1, len(doc))}
    M, last_q = [], 0
    for pn in range(1, len(doc)):
        for (x0, y0, x1, y1), t in lines(doc[pn]):
            if x0 > 80 or y0 < 75 or y0 > 785:
                continue
            if PART2.match(t):
                M.append(("P", pn, y0, None))
            elif m := GRE.match(t):
                M.append(("G", pn, y0, (int(m[1]), int(m[2]))))
            elif m := QRE.match(t):
                n = int(m[1])
                if n != last_q + 1:      # 只接受連續題號，避免選項或圖中的數字
                    continue
                last_q = n
                M.append(("Q", pn, y0, n))
    end = (len(doc) - 1, BOTTOM + 3)

    def nxt(i):
        return (M[i + 1][1], M[i + 1][2]) if i + 1 < len(M) else end

    qs, gs, mixed_from = [], [], None
    for i, (k, p, y, v) in enumerate(M):
        if k == "P":
            mixed_from = next(m[3] for m in M[i:] if m[0] == "Q")
        elif k == "G":
            j = next(j for j in range(i + 1, len(M)) if M[j][0] == "Q")
            s = region(boxes, (p, y), (M[j][1], M[j][2]))
            gs.append({"a": v[0], "b": v[1], "s": s, "t": text_of(doc, s)})
        elif k == "Q":
            s = region(boxes, (p, y), nxt(i))
            qs.append({"n": v, "s": s, "t": text_of(doc, s)})
    ans = parse(INC / f"{year}-s-ans.pdf")
    if [q["n"] for q in qs] != list(range(1, max(ans) + 1)):
        got = [q["n"] for q in qs]
        sys.exit(f"[錯誤] {year}：試卷題號 {len(got)} 題（最後 {got[-1]}），答案 {max(ans)} 題")
    for q in qs:
        q["ans"] = ans[q["n"]]
        if q["ans"] in ("／", "/"):
            q["pts"] = ns_points(q["t"])
        else:
            q["pts"] = 2
    return {"w": round(doc[1].rect.width, 1), "h": round(doc[1].rect.height, 1),
            "q": qs, "g": gs, "mixed_from": mixed_from}


if __name__ == "__main__":
    for y in sys.argv[1:]:
        d = extract(int(y))
        (INC / f"extract-soc-{y}.json").write_text(json.dumps(d, ensure_ascii=False, indent=1), "utf-8")
        ns = [q for q in d["q"] if q["ans"] in ("／", "/")]
        tot = sum(q["pts"] or 0 for q in d["q"])
        print(f"{y}：{len(d['q'])} 題、{len(d['g'])} 組題組、混合題自第 {d['mixed_from']} 題起、"
              f"非選 {len(ns)} 題、配分合計 {tot}" + (f"，缺配分 {[q['n'] for q in ns if q['pts'] is None]}" if any(q['pts'] is None for q in ns) else ""))
