#!/usr/bin/env python3
"""學測數學：試卷切圖、逐題切片、題型、答案（含選填格）擷取。

科目代號：m＝數學（107–110）、ma＝數學A、mb＝數學B（111 起）、mj＝數學甲、mi＝數學乙；
ph＝物理（107–110 指考、111 起分科測驗，版面與數甲相同，另存到 xuece-phy）。
用法：python tools/xuece/extract_math.py 115-ma 115-mb 110-m 115-ph ...
輸入：incoming/xuece/<年>-<科>-paper.pdf、-ans.pdf
輸出：assets/xuece-math（物理為 xuece-phy）/pages/<年><科>-<頁>.webp、
      incoming/xuece/extract-math（物理為 extract-phy）-<年>-<科>.json
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

ROOT = Path(__file__).resolve().parents[2]
INC = ROOT / "incoming" / "xuece"
OUT = ROOT / "assets" / "xuece-math" / "pages"
OTHER = {"ph": "phy", "ch": "chem", "bi": "bio", "hi": "hist", "ge": "geo", "ci": "civ"}  # 借用本程式的其他科：科目代號 → 輸出代號

QRE = re.compile(r"^\s*(\d{1,2}|[A-H])\s*[.．]")
SEC = re.compile(r"^\s*(?:[一二三四]、\s*|第[壹貳參]部分[：:、]\s*|[壹貳參]、\s*)(單選題|多選題|選填題|混合題|非選擇題|閱讀題|實驗題|選擇題)")  # 生物另有閱讀題、實驗題
GRE = re.compile(r"^\s*(?:第\s*)?(\d{1,2})\s*(?:至|-|–)\s*(\d{1,2})\s*題?\s*為題組")  # 也接受「6-7為題組」
NSQ = re.compile(r"^\s*([一二三四])\s*[、.．]")  # 指考非選擇題大題（「一、」或「一.」）
PTS = re.compile(r"占\s*(\d[\d\s]*)\s*分")


def parse_answers(path):
    """回傳 {題號或字母: 答案}。選填題的各格數字依序串接（如 13-1、13-2 → "91"）。"""
    toks = [t.strip() for t in pymupdf.open(path)[0].get_text().split("\n") if t.strip()]
    toks = [t for t in toks if t not in ("題號", "答案") and not re.search(r"學年度|考科|答案「", t)]
    ans, cells = {}, {}
    i = 0
    letter = None
    starts = {}
    while i < len(toks):
        t = toks[i]
        if re.fullmatch(r"[A-H]", t):           # 舊制：選填題字母，標示下一格為該題起點
            letter = t
            i += 1
            continue
        if re.fullmatch(r"\d+-\d+", t) and i + 1 < len(toks):   # 新制選填格
            q = t.split("-")[0]
            cells.setdefault(q, []).append(toks[i + 1])
            i += 2
            continue
        if re.fullmatch(r"\d+", t) and i + 1 < len(toks):
            if re.fullmatch(r"\d+-\d+", toks[i + 1]):          # 新制選填題題號列
                i += 1
                continue
            n, v = int(t), toks[i + 1]
            if letter:
                starts[letter] = n
                letter = None
            ans[n] = v
            i += 2
            continue
        i += 1
    out = {}
    if starts:  # 舊制：1–12 為選擇題，其後依字母切分選填格
        for n in sorted(ans):
            if n < min(starts.values()):
                out[str(n)] = ans[n]
        order = sorted(starts, key=lambda k: starts[k])
        for j, L in enumerate(order):
            a = starts[L]
            b = starts[order[j + 1]] if j + 1 < len(order) else max(ans) + 1
            out[L] = " ".join(ans[c] for c in range(a, b))
    else:
        for n, v in ans.items():
            out[str(n)] = v
        for q, vs in cells.items():
            out[q] = " ".join(vs)
    return out


def extract(key):
    year, subj = key.split("-")
    doc = pymupdf.open(INC / f"{key}-paper.pdf")
    out = ROOT / "assets" / f"xuece-{OTHER[subj]}" / "pages" if subj in OTHER else OUT
    out.mkdir(parents=True, exist_ok=True)
    for pn in range(1, len(doc)):
        pix = doc[pn].get_pixmap(matrix=pymupdf.Matrix(SCALE, SCALE))
        Image.frombytes("RGB", (pix.width, pix.height), pix.samples).save(
            out / f"{year}{subj}-{pn}.webp", "WEBP", quality=80, method=6)
    boxes = {pn: content_boxes(doc[pn]) for pn in range(1, len(doc))}
    M = []
    seen = []
    sec_total = {}
    for pn in range(1, len(doc)):
        page_lines = lines(doc[pn])
        if any("參考公式" in t for _, t in page_lines[:6]):   # 參考公式頁
            break
        for (x0, y0, x1, y1), t in page_lines:
            if x0 > 80 or y0 < 75 or y0 > 785:
                continue
            t = re.sub("[-]", lambda c: chr(ord(c[0]) - 0xF000), t)  # Symbol 字型的題號（如 110 物理第 22 題）
            if m := SEC.match(t):
                pts = PTS.search(t)
                M.append(("S", pn, y0, m[1]))
                if pts:
                    sec_total[m[1]] = int(re.sub(r"\s", "", pts[1]))
            elif next((x[3] for x in reversed(M) if x[0] == "S"), None) == "混合題" and NSQ.match(t):
                M.append(("H", pn, y0, None))  # 混合題以「一、」「二、」開頭的共用題幹（歷史卷）
            elif M and any(x[0] == "S" and x[3] == "非選擇題" for x in M) and (m := NSQ.match(t)):
                lab = "非選" + m[1]
                seen.append(lab)
                M.append(("Q", pn, y0, lab))
            elif m := GRE.match(t):
                M.append(("G", pn, y0, (int(m[1]), int(m[2]))))
            elif m := QRE.match(t):
                lab = m[1]
                nums = [x for x in seen if x.isdigit()]
                if lab.isdigit() and nums and int(lab) <= int(nums[-1]):
                    continue  # 題號倒退（附錄或公式），略過
                if lab in seen or any(x.startswith("非選") for x in seen):
                    continue
                seen.append(lab)
                M.append(("Q", pn, y0, lab))
    last = (len(doc) - 1, BOTTOM + 8)
    fstart = next((pn for pn in range(1, len(doc)) if any("參考公式" in t for _, t in lines(doc[pn])[:6])), None)
    if fstart:
        last = (fstart - 1, BOTTOM + 3)

    def nxt(i):
        return (M[i + 1][1], M[i + 1][2]) if i + 1 < len(M) else last

    qs, groups, sec_of = [], [], {}
    cur = None
    mix_mark = None
    for i, (k, p, y, v) in enumerate(M):
        if k == "S":
            cur = v
            if v == "混合題":
                mix_mark = i
        elif k == "H":
            j = next(j for j in range(i + 1, len(M)) if M[j][0] == "Q")
            end = next((e for e in range(i + 1, len(M)) if M[e][0] in ("H", "S")), len(M))
            labs = [M[e][3] for e in range(j, end) if M[e][0] == "Q"]
            s = region(boxes, (p, y), (M[j][1], M[j][2]))
            groups.append({"a": int(labs[0]), "b": int(labs[-1]), "s": s, "t": text_of(doc, s)})
        elif k == "G":
            j = next(j for j in range(i + 1, len(M)) if M[j][0] == "Q")
            s = region(boxes, (p, y), (M[j][1], M[j][2]))
            groups.append({"a": v[0], "b": v[1], "s": s, "t": text_of(doc, s)})
        elif k == "Q":
            s = region(boxes, (p, y), nxt(i))
            qs.append({"lab": v, "s": s, "t": text_of(doc, s)})
            sec_of[v] = cur
    # 混合題若沒有「第 a 至 b 題為題組」，以「混合題」標題到第一小題為共用題幹
    if mix_mark is not None and not groups:
        j = next(j for j in range(mix_mark + 1, len(M)) if M[j][0] == "Q")
        s = region(boxes, (M[mix_mark][1], M[mix_mark][2]), (M[j][1], M[j][2]))
        mixed = [q["lab"] for q in qs if sec_of[q["lab"]] == "混合題"]
        groups.append({"a": int(mixed[0]), "b": int(mixed[-1]), "s": s, "t": text_of(doc, s)})
    ans = parse_answers(INC / f"{key}-ans.pdf")
    for q in qs:
        if sec_of[q["lab"]] == "非選擇題":
            ans.setdefault(q["lab"], "／")
    miss = [q["lab"] for q in qs if q["lab"] not in ans]
    extra = [k for k in ans if k not in {q["lab"] for q in qs}]
    if miss or extra:
        sys.exit(f"[錯誤] {key}：試卷與答案題號不符，缺答案 {miss}，多出 {extra}")
    count = {}
    for q in qs:
        count[sec_of[q["lab"]]] = count.get(sec_of[q["lab"]], 0) + 1
    for q in qs:
        sec = sec_of[q["lab"]]
        q["sec"] = sec
        q["ans"] = ans[q["lab"]]
        flat = re.sub(r"\s", "", q["t"])
        own = [int(x) for x in re.findall(r"[（(](?:[^（）()]*?[，,])?(\d+)分[)）]", flat)]
        if sec == "混合題":      # 每小題一個配分；切片可能多含下一題首行，只取第一個
            q["pts"] = own[0] if own else None
        elif sec == "非選擇題":  # 指考非選擇題含多個子題，配分加總
            q["pts"] = sum(own) if own else None
        elif sec in sec_total:
            q["pts"] = sec_total[sec] // count[sec]
        else:
            q["pts"] = 5
    return {"w": round(doc[1].rect.width, 1), "h": round(doc[1].rect.height, 1), "q": qs, "g": groups}


if __name__ == "__main__":
    for key in sys.argv[1:]:
        d = extract(key)
        (INC / f"extract-{OTHER.get(key.split('-')[1], 'math')}-{key}.json").write_text(json.dumps(d, ensure_ascii=False, indent=1), "utf-8")
        runs = []
        for q in d["q"]:
            if runs and runs[-1][0] == q["sec"]:
                runs[-1][2] = q["lab"]
            else:
                runs.append([q["sec"], q["lab"], q["lab"]])
        print(key, len(d["q"]), "題 |", "、".join(f"{s} {a}–{b}" for s, a, b in runs),
              "| 選填答案", [q["ans"] for q in d["q"] if q["sec"] == "選填題"][:3], "| 題組", len(d["g"]))
