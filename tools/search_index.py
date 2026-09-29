#!/usr/bin/env python3
"""跨科搜尋索引：把各科 data/ 的逐題分類與題目文字整理成一份 JSON，供 search/ 頁使用。

由 build.py 呼叫：build_index(root) 回傳 {"subjects": [...], "items": [...]}。
每一題 item = [科目序號, 年度, 開題參數(list), 顯示題號, 考點, 類別, 題目文字]；
開題參數會交給各科頁面的 openInBank(...)，連結形式為 ../<科目>/#open=參數1,參數2…
"""
import json
import re
from pathlib import Path

# (資料夾, 顯示名稱, 分區, 顏色變數)
SUBJECTS = [
    ("guowen", "會考國文", "會考", "--zh"), ("english", "會考英語", "會考", "--en"),
    ("math", "會考數學", "會考", "--ma"), ("social", "會考社會", "會考", "--so"),
    ("science", "會考自然", "會考", "--sc"),
    ("xuece", "學測國文", "學測", "--zh"), ("xuece-en", "學測英文", "學測", "--en"),
    ("xuece-math", "學測數學・數甲・數乙", "學測", "--ma"), ("xuece-soc", "學測社會", "學測", "--so"),
    ("xuece-sci", "學測自然", "學測", "--sc"), ("xuece-earth", "學測地科", "學測", "--sc"),
    ("xuece-phy", "分科物理", "分科測驗", "--sc"), ("xuece-chem", "分科化學", "分科測驗", "--sc"),
    ("xuece-bio", "分科生物", "分科測驗", "--sc"), ("xuece-hist", "分科歷史", "分科測驗", "--so"),
    ("xuece-geo", "分科地理", "分科測驗", "--so"), ("xuece-civ", "分科公民", "分科測驗", "--so"),
]
MATH_TESTS = {"m": "數學", "ma": "數學A", "mb": "數學B", "mj": "數學甲", "mi": "數學乙"}
MAXLEN = 400


def names(root, subj, const):
    """從模板取出 const 名稱對照表（例如 UNIT = {K:"運動與力",…} 或 MAT = {K:{name:"語文知識"…}}）。"""
    html = (root / "templates" / f"{subj}.html").read_text("utf-8")
    m = re.search(rf"const {const}\s*=\s*\{{(.*?)\}};?\s*\n", html, re.S)
    if not m:
        raise SystemExit(f"[錯誤] {subj} 找不到 {const} 對照表")
    return dict(re.findall(r'"?([\w]+)"?\s*:\s*(?:\{\s*name\s*:\s*)?"([^"]+)"', m.group(1)))


def clean(t):
    t = re.sub(r"\s+", "", t or "")
    return t[:MAXLEN]


def years(root, subj):
    for f in sorted((root / "data" / subj).glob("1[0-9][0-9].json")):
        yield int(f.stem), json.loads(f.read_text("utf-8"))


def build_index(root):
    root = Path(root)
    items = []
    for si, (subj, _, _, _) in enumerate(SUBJECTS):
        add = lambda y, args, n, k, c, t: items.append([si, y, args, str(n), k or "", c or "", clean(t)])  # noqa: E731
        if subj in ("guowen", "xuece"):
            mat = names(root, subj, "MAT")
            for y, d in years(root, subj):
                for q, (code, lab) in zip(d["json:examData"]["q"], d["js:Q"]):
                    add(y, [y, q["n"]], q["n"], lab, mat.get(code, code), q["t"])
        elif subj == "english":
            cat = names(root, subj, "CAT")
            for y, d in years(root, subj):
                for q, (code, lab) in zip(d["json:exR"]["q"], d["json:clsData"]["items"]):
                    add(y, [y, "R", q["n"]], f"閱讀 {q['n']}", lab, cat.get(code, code), q["t"])
                for q in d["json:exL"]["q"]:
                    add(y, [y, "L", q["n"]], f"聽力 {q['n']}", "", "聽力", q["t"])
        elif subj == "math":
            st = names(root, subj, "ST")
            for y, d in years(root, subj):
                for q, (code, lab) in zip(d["json:examData"]["q"], d["json:clsData"]):
                    add(y, [y, q["n"]], q["n"], lab, st.get(code, code), q["t"])
        elif subj == "social":
            area = names(root, subj, "AREA")
            for y, d in years(root, subj):
                for q, (s, a, lab) in zip(d["json:examData"]["q"], d["json:clsData"]):
                    add(y, [y, q["n"]], q["n"], lab, area.get(s + a, s), q["t"])
        elif subj == "science":
            sj = names(root, subj, "SUBJ")
            for y, d in years(root, subj):
                for q, (code, lab) in zip(d["json:examData"]["q"], d["json:clsData"]):
                    add(y, [y, q["n"]], q["n"], lab, sj.get(code, code), q["t"])
        elif subj == "xuece-en":
            for y, d in years(root, subj):
                for q, row in zip(d["json:examData"]["q"], d["js:Q"]):
                    add(y, [y, q["n"]], q["n"], row[1], row[0], q["t"])
        elif subj == "xuece-math":
            units = names(root, subj, "UNITS")
            for y, d in years(root, subj):
                for t, ex in d["json:examData"].items():
                    for i, (q, row) in enumerate(zip(ex["q"], d["js:Q"][t])):
                        add(y, [y, t, i], f"{MATH_TESTS[t]} {q['lab']}", row[3], units.get(row[2], row[2]), q["t"])
        elif subj in ("xuece-soc", "xuece-sci"):
            dom = names(root, subj, "DOM" if subj == "xuece-soc" else "SUBJ")
            for y, d in years(root, subj):
                for q, row in zip(d["json:examData"]["q"], d["js:Q"]):
                    add(y, [y, q["n"]], q["n"], row[1].replace("非選：", ""), dom.get(row[0], row[0]), q["t"])
        else:  # 分科各科與學測地科：row = [區段, 題型, 單元, 考點, 答案, 配分]，題號為 q["lab"]
            unit = names(root, subj, "UNIT")
            for y, d in years(root, subj):
                for q, row in zip(d["json:examData"]["q"], d["js:Q"]):
                    lab = q["lab"]
                    shown = f"非選{lab[2:]}" if lab.startswith("非選") else lab
                    add(y, [y, lab], shown, row[3].replace("非選：", ""), unit.get(row[2], row[2]), q["t"])
    subjects = [{"key": k, "name": n, "group": g, "c": c} for k, n, g, c in SUBJECTS]
    return {"subjects": subjects, "items": items}


if __name__ == "__main__":
    ROOT = Path(__file__).resolve().parents[1]
    idx = build_index(ROOT)
    from collections import Counter
    c = Counter(idx["subjects"][it[0]]["name"] for it in idx["items"])
    print(sum(c.values()), "題", dict(c))
    empty = Counter(idx["subjects"][it[0]]["name"] for it in idx["items"] if not it[5])
    print("缺類別：", dict(empty))
