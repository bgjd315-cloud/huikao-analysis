#!/usr/bin/env python3
"""學測國文：把大考中心試卷 PDF 轉成題本頁圖與逐題切圖資料。

用法：python tools/xuece/extract.py 115 [116 ...]
輸入：incoming/xuece/<年>-paper.pdf、<年>-ans.pdf
輸出：assets/xuece/pages/<年>-<頁>.webp（頁碼＝試卷印的頁碼，封面不轉）
      incoming/xuece/extract-<年>.json（examData、ANS、題型結構），再由 merge.py 併入 data/xuece/<年>.json
"""
import json
import re
import sys
from pathlib import Path

import pymupdf

sys.path.insert(0, str(Path(__file__).parent))
from markers import lines, markers  # noqa: E402
from parse_ans import parse  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
INC = ROOT / "incoming" / "xuece"
OUT = ROOT / "assets" / "xuece" / "pages"
SCALE = 1.6
TOP, BOTTOM = 76, 782  # 頁首、頁尾之間的內容區


def content_boxes(page):
    """頁面上所有內容（文字行、圖片、線條）的 y 範圍，排除頁首頁尾。"""
    boxes = [bb for bb, t in lines(page) if not re.fullmatch(r"\s*-\s*\d+\s*-\s*", t)]  # 排除頁碼
    boxes += [tuple(i["bbox"]) for i in page.get_image_info()]
    boxes += [tuple(d["rect"]) for d in page.get_drawings()]
    return [b for b in boxes if b[1] >= TOP - 2 and b[3] <= BOTTOM + 2 and b[3] - b[1] < 700]


def region(boxes_by_page, start, end):
    """從 start=(頁, y) 到 end=(頁, y) 的切片清單 [[頁, y0, y1], ...]，只保留有內容的片段並收緊下緣。"""
    (p0, y0), (p1, y1) = start, end
    out = []
    for p in range(p0, p1 + 1):
        a = y0 - 4 if p == p0 else TOP
        b = y1 - 3 if p == p1 else BOTTOM
        inside = [bx for bx in boxes_by_page[p] if bx[1] >= a - 1 and bx[1] < b and bx[3] - bx[1] > 0.5]
        if not inside:
            continue
        b = min(b, max(bx[3] for bx in inside) + 4)
        if b - a > 6:
            out.append([p, round(a, 1), round(b, 1)])
    return out


def text_of(doc, slices):
    parts = []
    for p, a, b in slices:
        ls = [(bb, t) for bb, t in lines(doc[p])
              if bb[1] >= a - 1 and bb[1] < b and not re.fullmatch(r"\s*-\s*\d+\s*-\s*", t)]
        parts += [t.rstrip() for _, t in ls]
    return "\n".join(parts).strip()


def structure(M, n_total):
    """從「說明：第a題至第b題」讀出單選、多選範圍；其餘為混合題（第貳部分）。"""
    single = multi = None
    for kind, p, y, v, t in M:
        if kind != "S":
            continue
        m = re.search(r"第\s*(\d+)\s*題至第\s*(\d+)\s*題", t)
        if not m:
            continue
        rng = [int(m[1]), int(m[2])]
        if single is None:
            single = rng
        elif multi is None:
            multi = rng
    mixed = [multi[1] + 1, n_total] if multi and multi[1] < n_total else None
    return {"single": single, "multi": multi, "mixed": mixed}


def extract(year):
    doc = pymupdf.open(INC / f"{year}-paper.pdf")
    OUT.mkdir(parents=True, exist_ok=True)
    for pn in range(1, len(doc)):
        pix = doc[pn].get_pixmap(matrix=pymupdf.Matrix(SCALE, SCALE))
        from PIL import Image
        im = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        im.save(OUT / f"{year}-{pn}.webp", "WEBP", quality=80, method=6)

    boxes = {pn: content_boxes(doc[pn]) for pn in range(1, len(doc))}
    M = markers(INC / f"{year}-paper.pdf")
    ans = parse(INC / f"{year}-ans.pdf")
    n_total = max(ans)
    last = (len(doc) - 1, BOTTOM + 3)

    def next_after(i):
        return (M[i + 1][1], M[i + 1][2]) if i + 1 < len(M) else last

    qs, gs = [], []
    for i, (kind, p, y, v, t) in enumerate(M):
        if kind == "Q":
            s = region(boxes, (p, y), next_after(i))
            qs.append({"n": v, "s": s, "t": text_of(doc, s)})
        elif kind == "G":
            a, b = v
            # 選文：題組標題到該組第一題
            j = next(k for k in range(i + 1, len(M)) if M[k][0] == "Q" and M[k][3] == a)
            s = region(boxes, (p, y), (M[j][1], M[j][2]))
            gs.append({"a": a, "b": b, "s": s, "t": text_of(doc, s)})
    w, h = doc[1].rect.width, doc[1].rect.height
    return {
        "json:examData": {"w": round(w, 1), "h": round(h, 1), "q": qs, "g": gs},
        "js:ANS": [ans[n] for n in range(1, n_total + 1)],
        "js:STRUCT": structure(M, n_total),
        "pages": len(doc) - 1,
    }


if __name__ == "__main__":
    for y in sys.argv[1:]:
        d = extract(int(y))
        (INC / f"extract-{y}.json").write_text(json.dumps(d, ensure_ascii=False, indent=1), "utf-8")
        ex = d["json:examData"]
        empty = [q["n"] for q in ex["q"] if not q["s"]]
        print(f"{y}：{len(ex['q'])} 題、{len(ex['g'])} 組題組、{d['pages']} 頁，結構 {d['js:STRUCT']}"
              + (f"，沒切到內容：{empty}" if empty else ""))
