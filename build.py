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
    "xuece-earth": "學測地科",
    "xuece-phy": "分科物理",
    "xuece-chem": "分科化學",
    "xuece-bio": "分科生物",
    "xuece-hist": "分科歷史",
    "xuece-geo": "分科地理",
    "xuece-civ": "分科公民",
}
HEAD_EXTRA = '<meta name="robots" content="noindex,nofollow">'
# 跨科搜尋的直達連結：網址帶 #open=年,題號（或其他參數）時，載入後自動在試題庫打開該題
OPEN_HASH = r"""<script>(function(){var m=location.hash.match(/^#open=(.+)$/);if(!m)return;
var a=m[1].split(",").map(function(v){v=decodeURIComponent(v);return /^\d+$/.test(v)?+v:v;});
function go(){if(typeof openInBank!=="function")return;openInBank.apply(null,a);
setTimeout(function(){var d=document.querySelector("details.qitem[open]");if(d)d.scrollIntoView({block:"start"});},450);}
if(document.readyState==="complete")setTimeout(go,60);else addEventListener("load",function(){setTimeout(go,60);});})();</script>
"""


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


# 著作權與來源說明：自動加在每一頁最下方
COPY_NOTE = (
    '<footer class="copy-note" style="max-width:1040px;margin:48px auto 0;padding-top:14px;'
    'border-top:1px solid var(--rule,#E3E1DB);font-size:12.5px;line-height:1.75;color:var(--ink-3,#7A818A)">'
    '<p style="margin:0 0 6px"><b>著作權與來源說明</b>　本網站收錄的國中教育會考、大學學測、分科測驗（含 110 年以前指考）試題，'
    '依著作權法第 9 條第 1 項第 5 款，屬依法令舉行之考試試題，不得為著作權之標的；但試題中引用的文章、詩文、圖片、照片、漫畫與地圖等，'
    '著作權仍屬原作者所有。本網站僅供非營利之教學與研究使用，請勿作商業用途。題目圖片裁切自官方公布的試卷，'
    '答案、配分與評分原則以官方公布為準；單元與考點分類為本站逐題判讀，並非官方分類。</p>'
    '<p style="margin:0">官方來源：'
    '<a href="https://cap.rcpet.edu.tw/examination.html" target="_blank" rel="noopener" style="color:inherit">國中教育會考・歷屆試題</a>｜'
    '<a href="https://www.ceec.edu.tw/xmfile?xsmsid=0J052424829869345634" target="_blank" rel="noopener" style="color:inherit">大考中心・學測歷年試題</a>｜'
    '<a href="https://www.ceec.edu.tw/xmfile?xsmsid=0J052427633128416650" target="_blank" rel="noopener" style="color:inherit">大考中心・分科測驗（110 前指考）歷年試題</a>'
    '。如權利人認為有不當使用，請透過 <a href="https://github.com/bgjd315-cloud/huikao-analysis/issues" target="_blank" rel="noopener" style="color:inherit">GitHub 專案頁</a>告知，將儘速處理。</p>'
    '</footer>\n'
)


def finish(html, lang="zh-Hant"):
    html = html.replace("<html>", f'<html lang="{lang}">', 1)
    html = html.replace("<meta charset=utf8>", "<meta charset=utf8>" + HEAD_EXTRA, 1)
    assert html.count("</body></html>") == 1, "頁面結尾必須是唯一的 </body></html>"
    html = html.replace("</body></html>", COPY_NOTE + "</body></html>", 1)
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
        html = html.replace("</body></html>", OPEN_HASH + "</body></html>", 1)
        (out / "index.html").write_text(finish(html), "utf-8")
        src = ROOT / "assets" / subj
        if src.exists():
            shutil.copytree(src, out, dirs_exist_ok=True)
        print(f"{SUBJECTS[subj]}：{min(years)}–{max(years)} 年，共 {len(years)} 年")

    index = (ROOT / "templates" / "index.html").read_text("utf-8")
    (DIST / "index.html").write_text(finish(index), "utf-8")

    # 跨科搜尋頁：索引由 tools/search_index.py 從各科 data/ 產生
    sys.path.insert(0, str(ROOT / "tools"))
    from search_index import build_index
    idx = build_index(ROOT)
    (DIST / "search").mkdir()
    (DIST / "search" / "data.json").write_text(json.dumps(idx, ensure_ascii=False, separators=(",", ":")), "utf-8")
    (DIST / "search" / "index.html").write_text(finish((ROOT / "templates" / "search.html").read_text("utf-8")), "utf-8")
    print(f"跨科搜尋：{len(idx['items'])} 題")
    (DIST / "robots.txt").write_text("User-agent: *\nDisallow: /\n", "utf-8")
    (DIST / ".nojekyll").write_text("", "utf-8")
    print(f"完成：{DIST}")


if __name__ == "__main__":
    main()
