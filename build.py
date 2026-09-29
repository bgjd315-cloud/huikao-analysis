#!/usr/bin/env python3
"""把 templates/ 與 data/ 組成可上線的靜態網站，輸出到 dist/。

用法：python3 build.py
- 年度清單自動取自 data/<科目>/ 底下的 <年度>.json，新增一年只要放進新檔。
- 模板中的佔位符：
    {{years}}        → 該科所有年度，例如 [111,112,113,114,115]
    {{json:區塊id}}  → 各年度資料檔中 "json:區塊id" 合併成 {"111":…, "112":…}
    {{js:常數名}}    → 各年度資料檔中 "js:常數名" 合併成同樣形式
"""
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist"
SUBJECTS = {  # 資料夾代號 → 顯示名稱
    "guowen": "國文",
    "english": "英語",
    "math": "數學",
    "social": "社會",
    "science": "自然",
    "xuece": "學測國文",
    "xuece-en": "學測英文",
    "xuece-math": "學測數學",
    "xuece-soc": "學測社會",
    "xuece-sci": "學測自然",
    "xuece-phy": "分科物理",
    "xuece-chem": "分科化學",
    "xuece-bio": "分科生物",
}
HEAD_EXTRA = '<meta name="robots" content="noindex,nofollow">'


def load_years(subj):
    files = sorted((ROOT / "data" / subj).glob("1[0-9][0-9].json"))
    return {int(f.stem): json.loads(f.read_text("utf-8")) for f in files}


def merge(years, key, subj):
    out = {}
    for y, d in years.items():
        if key in d:
            out[str(y)] = d[key]
    if not out:
        sys.exit(f"[錯誤] {subj}：沒有任何年度提供 {key}")
    return json.dumps(out, ensure_ascii=False, separators=(",", ":"))


def render(tpl, years, subj):
    def sub(m):
        if m.group(0) == "{{years}}":
            return json.dumps(sorted(years))
        text = merge(years, f"{m.group(1)}:{m.group(2)}", subj)
        # JSON 放進 <script> 內時，避免字串中的 </ 提前結束標籤
        return text.replace("</", "<\\/")

    return re.sub(r"\{\{years\}\}|\{\{(json|js):(\w+)\}\}", sub, tpl)


def finish(html, lang="zh-Hant"):
    html = html.replace("<html>", f'<html lang="{lang}">', 1)
    html = html.replace("<meta charset=utf8>", "<meta charset=utf8>" + HEAD_EXTRA, 1)
    return html


def main():
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir()

    for subj in SUBJECTS:
        years = load_years(subj)
        if not years:
            sys.exit(f"[錯誤] data/{subj}/ 沒有任何年度資料")
        tpl = (ROOT / "templates" / f"{subj}.html").read_text("utf-8")
        html = render(tpl, years, subj)
        left = re.findall(r"\{\{[^}]+\}\}", html)
        if left:
            sys.exit(f"[錯誤] {subj} 還有未替換的佔位符：{sorted(set(left))}")
        out = DIST / subj
        out.mkdir()
        (out / "index.html").write_text(finish(html), "utf-8")
        src = ROOT / "assets" / subj
        if src.exists():
            shutil.copytree(src, out, dirs_exist_ok=True)
        print(f"{SUBJECTS[subj]}：{min(years)}–{max(years)} 年，共 {len(years)} 年")

    index = (ROOT / "templates" / "index.html").read_text("utf-8")
    (DIST / "index.html").write_text(finish(index), "utf-8")
    (DIST / "robots.txt").write_text("User-agent: *\nDisallow: /\n", "utf-8")
    (DIST / ".nojekyll").write_text("", "utf-8")
    print(f"完成：{DIST}")


if __name__ == "__main__":
    main()
