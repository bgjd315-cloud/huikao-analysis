#!/usr/bin/env python3
"""學測國寫：試卷切圖＋小題字數、配分、作文題目擷取。

用法：python tools/xuece/extract_writing.py 115 [116 ...]
輸入：incoming/xuece/<年>-w-paper.pdf
輸出：assets/xuece/pages/<年>-w<頁>.webp、incoming/xuece/writing-<年>.json
"""
import json
import re
import sys
from pathlib import Path

import pymupdf
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from extract import BOTTOM, OUT, SCALE, content_boxes, region, text_of  # noqa: E402
from markers import lines  # noqa: E402

INC = Path(__file__).resolve().parents[2] / "incoming" / "xuece"
BIG = re.compile(r"^\s*([一二])、\s*$")


def subs_of(text):
    """解析小題：問題（一）……文長限N字……（占N分）；只有一題時整段為一題。"""
    flat = re.sub(r"\s+", "", text)
    parts = re.split(r"(問題[（(][一二三][)）][：:])", flat)
    chunks = [(parts[i][:-1], parts[i + 1]) for i in range(1, len(parts), 2)] or [("", flat.split("請回答下列問題")[-1])]
    out = []
    for label, body in chunks:
        pts = re.search(r"[（(]占(\d+)分[)）]", body)
        lim = re.search(r"文長限(\d+)字", body)
        title = re.search(r"以「([^」]+)」為題", body)
        body = re.split(r"[（(]占\d+分[)）]", body)[0]
        out.append({
            "label": label.replace("(", "（").replace(")", "）"),
            "pts": int(pts[1]) if pts else None,
            "limit": int(lim[1]) if lim else None,
            "title": title[1] if title else None,
            "ask": body,
        })
    if len(out) == 1 and out[0]["pts"] is None:  # 單一作文題有時只寫「文長不限」，每大題固定 25 分
        out[0]["pts"] = 25
    return out


def extract(year):
    doc = pymupdf.open(INC / f"{year}-w-paper.pdf")
    OUT.mkdir(parents=True, exist_ok=True)
    for pn in range(1, len(doc)):
        pix = doc[pn].get_pixmap(matrix=pymupdf.Matrix(SCALE, SCALE))
        Image.frombytes("RGB", (pix.width, pix.height), pix.samples).save(
            OUT / f"{year}-w{pn}.webp", "WEBP", quality=80, method=6)
    boxes = {pn: content_boxes(doc[pn]) for pn in range(1, len(doc))}
    M = [(pn, bb[1]) for pn in range(1, len(doc)) for bb, t in lines(doc[pn]) if BIG.match(t) and bb[0] < 75]
    if len(M) != 2:
        sys.exit(f"[錯誤] {year} 國寫找到 {len(M)} 個大題標記")
    ends = [M[1], (len(doc) - 1, BOTTOM + 3)]
    tasks = []
    for i, start in enumerate(M):
        s = region(boxes, start, ends[i])
        t = text_of(doc, s)
        tasks.append({"no": i + 1, "s": s, "t": t, "subs": subs_of(t)})
    return {"w": round(doc[1].rect.width, 1), "h": round(doc[1].rect.height, 1), "tasks": tasks}


if __name__ == "__main__":
    for y in sys.argv[1:]:
        d = extract(int(y))
        (INC / f"writing-{y}.json").write_text(json.dumps(d, ensure_ascii=False, indent=1), "utf-8")
        for t in d["tasks"]:
            pts = [s["pts"] for s in t["subs"]]
            print(f"{y} 第{t['no']}大題：{len(t['subs'])} 小題，配分 {pts}（計 {sum(p or 0 for p in pts)}），"
                  f"字數 {[s['limit'] for s in t['subs']]}，題目 {[s['title'] for s in t['subs'] if s['title']]}")
