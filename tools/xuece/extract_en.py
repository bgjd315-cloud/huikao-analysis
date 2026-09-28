#!/usr/bin/env python3
"""學測英文：試卷切圖、逐題切片、題型區段、翻譯與作文擷取。

用法：python tools/xuece/extract_en.py 115 [116 ...]
輸入：incoming/xuece/<年>-e-paper.pdf、<年>-e-ans.pdf
輸出：assets/xuece-en/pages/<年>-<頁>.webp、incoming/xuece/extract-en-<年>.json
"""
import json
import re
import sys
from pathlib import Path

import pymupdf
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from extract import BOTTOM, SCALE, content_boxes, region, text_of  # noqa: E402
from markers import lines  # noqa: E402
from parse_ans import parse  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
INC = ROOT / "incoming" / "xuece"
OUT = ROOT / "assets" / "xuece-en" / "pages"

QRE = re.compile(r"^\s*(\d{1,2})\s*[.．]\s*\S")
QRE2 = re.compile(r"^\s*(\d{1,2})\s*[-－–]\s*(\d{1,2})\s+\S")          # 「47-48 下列……」合併小題
GRE = re.compile(r"^\s*第\s*(\d{1,2})\s*至\s*(\d{1,2})\s*題為題組")
SEC = re.compile(r"^\s*[一二三四五六]、\s*(詞彙|綜合測驗|文意選填|篇章結構|閱讀測驗|中譯英|英文作文)")
PART = re.compile(r"^\s*第[壹貳參]部分")
SECNAME = {"詞彙": "詞彙", "綜合測驗": "綜合測驗", "文意選填": "文意選填", "篇章結構": "篇章結構", "閱讀測驗": "閱讀測驗"}


def markers(doc):
    M = []
    for pn in range(1, len(doc)):
        for (x0, y0, x1, y1), t in lines(doc[pn]):
            if x0 > 80 or y0 < 75 or y0 > 782:
                continue
            if m := GRE.match(t):
                M.append(("G", pn, y0, (int(m[1]), int(m[2]))))
            elif m := SEC.match(t):
                M.append(("S", pn, y0, m[1]))
            elif PART.match(t):
                M.append(("P", pn, y0, t.strip()))
            elif m := QRE2.match(t):
                M.append(("Q", pn, y0, (int(m[1]), int(m[2]))))
            elif m := QRE.match(t):
                M.append(("Q", pn, y0, (int(m[1]), int(m[1]))))
    return M


def extract(year):
    doc = pymupdf.open(INC / f"{year}-e-paper.pdf")
    OUT.mkdir(parents=True, exist_ok=True)
    for pn in range(1, len(doc)):
        pix = doc[pn].get_pixmap(matrix=pymupdf.Matrix(SCALE, SCALE))
        Image.frombytes("RGB", (pix.width, pix.height), pix.samples).save(
            OUT / f"{year}-{pn}.webp", "WEBP", quality=80, method=6)
    boxes = {pn: content_boxes(doc[pn]) for pn in range(1, len(doc))}
    M = markers(doc)
    ans = parse(INC / f"{year}-e-ans.pdf")
    n_total = max(ans)
    last = (len(doc) - 1, BOTTOM + 3)

    # 非選擇題部分（中譯英、英文作文）以後的題號是翻譯子題，不算選擇題
    ns_start = next(i for i, m in enumerate(M) if m[0] == "S" and m[3] == "中譯英")
    essay = next(i for i, m in enumerate(M) if m[0] == "S" and m[3] == "英文作文")
    choice = M[:ns_start]

    def nxt(i, arr):
        return (arr[i + 1][1], arr[i + 1][2]) if i + 1 < len(arr) else (M[ns_start][1], M[ns_start][2])

    sec_of, groups, qs = {}, [], {}
    cur = None
    for i, (k, p, y, v) in enumerate(choice):
        if k == "S":
            cur = SECNAME[v]
        elif k == "P" and "混合" in str(v):
            cur = "混合題"
        elif k == "G":
            a, b = v
            j = next((j for j in range(i + 1, len(choice)) if choice[j][0] in "QGSP"), None)
            end = (choice[j][1], choice[j][2]) if j is not None else (M[ns_start][1], M[ns_start][2])
            s = region(boxes, (p, y), end)
            groups.append({"a": a, "b": b, "s": s, "t": text_of(doc, s), "sec": cur})
            for n in range(a, b + 1):
                sec_of[n] = cur
        elif k == "Q":
            a, b = v
            s = region(boxes, (p, y), nxt(i, choice))
            for n in range(a, b + 1):
                qs[n] = {"n": n, "s": s, "t": text_of(doc, s)}
                sec_of.setdefault(n, cur)
    # 混合題若沒有「第 a 至 b 題為題組」標題（如 112 年），以「混合題」部分標題到第一小題為共用選文
    mix = next((i for i, m in enumerate(choice) if m[0] == "P" and "混合" in str(m[3])), None)
    if mix is not None and not any(g["sec"] == "混合題" for g in groups):
        j = next(j for j in range(mix + 1, len(choice)) if choice[j][0] == "Q")
        a = choice[j][3][0]
        s = region(boxes, (choice[mix][1], choice[mix][2]), (choice[j][1], choice[j][2]))
        groups.append({"a": a, "b": n_total, "s": s, "t": text_of(doc, s), "sec": "混合題"})
    # 詞彙題不在題組內
    for n in qs:
        sec_of.setdefault(n, "詞彙")
    # 文意選填、篇章結構沒有個別題號行：以題組選文為題目本身
    for g in groups:
        for n in range(g["a"], g["b"] + 1):
            if n not in qs:
                qs[n] = {"n": n, "s": [], "t": ""}
    missing = [n for n in range(1, n_total + 1) if n not in qs]
    if missing:
        sys.exit(f"[錯誤] {year} 找不到題號：{missing}")

    tr = region(boxes, (M[ns_start][1], M[ns_start][2]), (M[essay][1], M[essay][2]))
    es = region(boxes, (M[essay][1], M[essay][2]), last)
    tr_text = text_of(doc, tr)
    sentences = [re.sub(r"\s+", "", s) for s in re.findall(r"^\s*\d\s*[.．]\s*(.+)$", tr_text, re.M)]
    sentences = [s for s in sentences if not re.search(r"請|每題\d分", s)]  # 排除作答說明
    return {
        "json:examData": {"w": round(doc[1].rect.width, 1), "h": round(doc[1].rect.height, 1),
                          "q": [qs[n] for n in range(1, n_total + 1)], "g": groups},
        "js:ANS": [ans[n] for n in range(1, n_total + 1)],
        "js:SEC": [sec_of[n] for n in range(1, n_total + 1)],
        "writing": {"tr": {"s": tr, "sent": sentences}, "essay": {"s": es, "t": text_of(doc, es)}},
    }


if __name__ == "__main__":
    for y in sys.argv[1:]:
        d = extract(int(y))
        (INC / f"extract-en-{y}.json").write_text(json.dumps(d, ensure_ascii=False, indent=1), "utf-8")
        sec = d["js:SEC"]
        runs = []
        for i, s in enumerate(sec, 1):
            if runs and runs[-1][0] == s:
                runs[-1][2] = i
            else:
                runs.append([s, i, i])
        print(y, len(sec), "題 |", "、".join(f"{s} {a}–{b}" for s, a, b in runs),
              "| 題組", len(d["json:examData"]["g"]), "| 翻譯", len(d["writing"]["tr"]["sent"]), "句")
