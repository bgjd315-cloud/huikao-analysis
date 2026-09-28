#!/usr/bin/env python3
"""學測英文：合併擷取結果、短文主題、自動考點與非選參考答案 → data/xuece-en/<年>.json。

用法：python tools/xuece/merge_en.py 115 [116 ...]
"""
import json
import re
import sys
from pathlib import Path

import pymupdf

sys.path.insert(0, str(Path(__file__).parent))
from classify_en import ESSAY, TOPIC  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
INC = ROOT / "incoming" / "xuece"

# 閱讀題型：依序比對題幹，第一個符合者為準
RTYPES = [
    ("圖表判讀", r"\b(pictures?|charts?|graphs?|maps?|tables?|routes?|diagrams?|figures?|illustrations?)\b(?! out)"),
    ("字義", r"closest in meaning|meaning of|\bdefines?\b|author mean by|“[^”]+” in the \w+ paragraph (imply|mean)"),
    ("指涉", r"refers? to|referred to"),
    ("主旨", r"main(ly)? (idea|about|purpose|point)|best title|title .* best|mainly (discuss|about)|purpose of (this|the) passage|primarily"),
    ("態度語氣", r"attitude|\btone\b|feel about"),
    ("組織與手法", r"\border\b|sequence|organized|structure|why does the author|how does the author|author (use|mention|quote)|to support|example of"),
    ("推論", r"infer|imply|implied|most likely|probably|conclude|suggest|can be learned|we can learn|opinion"),
    ("細節", r"."),
]


def opts(t):
    t = re.sub(r"\s+", " ", t)
    parts = re.split(r"\(\s*([A-L])\s*\)", t)
    return {parts[i]: parts[i + 1].strip(" .") for i in range(1, len(parts) - 1, 2)}


def stem(t):
    t = re.sub(r"\s+", " ", t)
    return re.sub(r"^\d{1,2}\s*[-–]?\s*\d*\s*[.．]?\s*", "", re.split(r"\(\s*A\s*\)", t)[0]).strip()


def mixed_refs(path):
    """混合題非選參考答案：{題號(含 47A 這類子題): 答案}。"""
    text = "".join(p.get_text() for p in pymupdf.open(path))
    m = re.search(r"混合題.*?滿分參考答案[：:]?(.*?)二、\s*評分原則", text, re.S)
    if not m:
        return {}
    out, cur = {}, None
    for line in (l.strip() for l in m[1].split("\n")):
        if not line or line in ("題號", "參考答案"):
            continue
        if re.fullmatch(r"\d{2}[A-Z]?", line):
            cur = line
            out[cur] = []
        elif cur:
            out[cur].append(line)
    clean = {}
    for k, v in out.items():
        v = [re.sub(r"[-{}]", "", x).strip() for x in v]  # PDF 的大括號圖形字元
        v = [x for x in v if x and not re.fullmatch(r"\d+", x)]        # 頁碼
        clean[k] = " / ".join(v)
    return clean


def merge(y):
    d = json.loads((INC / f"extract-en-{y}.json").read_text("utf-8"))
    ex, ans, sec = d["json:examData"], d["js:ANS"], d["js:SEC"]
    groups, topics = ex["g"], TOPIC[y]
    err = []
    if len(groups) != len(topics):
        err.append(f"題組 {len(groups)} 組，主題表 {len(topics)} 組")
    refs = mixed_refs(INC / f"{y}-e-rubric.pdf")
    Q, MIX = [], {}
    for q in ex["q"]:
        n, a, s = q["n"], ans[q["n"] - 1], sec[q["n"] - 1]
        g = next((i for i, g in enumerate(groups) if g["a"] <= n <= g["b"]), None)
        if s in ("詞彙", "綜合測驗"):
            o = opts(q["t"])
            lab = o.get(a, "")
        elif s == "文意選填":
            o = opts(groups[g]["t"])
            lab = o.get(a, "")
        elif s == "篇章結構":
            lab = "句子插入"
        elif s == "閱讀測驗":
            st = stem(q["t"])
            lab = next(k for k, r in RTYPES if re.search(r, st, re.I))
        else:  # 混合題
            pts = re.search(r"(\d+)\s*分\s*[)）]", re.sub(r"\s+", "", q["t"]))
            if a in ("／", "/"):
                kind = "填充" if re.search(r"填", q["t"]) else "簡答"
                ref = " ｜ ".join(f"{k}：{v}" if len(k) > 2 else v for k, v in refs.items() if k.startswith(str(n)))
                if not ref:
                    err.append(f"混合題第 {n} 題找不到參考答案")
                share = sum(1 for x in ex["q"] if x["s"] == q["s"])  # 「47-48」合併題的配分是兩格合計
                MIX[str(n)] = {"ref": ref, "pts": int(pts[1]) // share if pts else None, "kind": kind}
                lab = kind
            else:
                lab = "多選" if len(a) > 1 else "單選"
        if s in ("詞彙", "綜合測驗", "文意選填") and not lab:
            err.append(f"第 {n} 題抓不到答案字")
        Q.append([s, lab, topics[g][0] if g is not None else None])
    if err:
        sys.exit(f"[錯誤] {y}：" + "；".join(err))
    G = [[f"{g['a']}–{g['b']}", g["sec"], c, title] for g, (c, title) in zip(groups, topics)]
    et, etopic, ereq = ESSAY[y]
    w = d["writing"]
    out = {
        "json:examData": ex,
        "json:writeData": {"w": ex["w"], "h": ex["h"], "tr": w["tr"],
                           "essay": {"s": w["essay"]["s"], "type": et, "topic": etopic, "req": ereq}},
        "js:ANS": ans,
        "js:Q": Q,
        "js:GROUPS": G,
        "js:MIX": MIX,
    }
    p = ROOT / "data" / "xuece-en" / f"{y}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), "utf-8")
    rt = {}
    for s, lab, _ in Q:
        if s == "閱讀測驗":
            rt[lab] = rt.get(lab, 0) + 1
    print(f"{y}：{len(Q)} 題，閱讀題型 {rt}，混合非選 {MIX and {k: (v['kind'], v['pts'], v['ref'][:30]) for k, v in MIX.items()}}")


if __name__ == "__main__":
    for y in sys.argv[1:]:
        merge(int(y))
