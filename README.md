# 會考五科命題分析網站

國中教育會考國文、英語、數學、社會、自然五科的逐題命題分析與原題試題庫，目前收錄 111 年到 115 年。
另有延伸頁「學測國文」（`xuece/`，含國寫）、「學測英文」（`xuece-en/`）與「學測數學」（`xuece-math/`），收錄大學學科能力測驗 107 年到 115 年。
網站由 `build.py` 用「模板＋逐年資料」組合產生，推上 GitHub 的 `main` 分支後會自動發布到 GitHub Pages。

## 資料夾結構

```
templates/          各頁的版面、說明文字與跨年度統整（五年結論、重複考點表等）
  index.html        五科總覽
  guowen.html  english.html  math.html  social.html  science.html
data/<科目>/<年度>.json   每科每年一份：題目文字、切圖座標、分類、答案、官方統計
assets/<科目>/      題本頁面圖片（webp）、英語聽力音檔（mp3）
build.py            產生網站到 dist/
tools/verify.py     用無頭瀏覽器檢查每一頁：JS 錯誤、檔案缺漏
tools/migrate/      當初從 Artifact 搬過來用的一次性工具（留存紀錄）
tools/xuece/        學測國文、英文、數學：試卷切圖、答案與非選參考答案解析、逐題分類
docs/年度更新流程.md  每年新增一個年度的步驟（會考與學測）
```

## 在自己電腦上預覽

需要 Python 3（不需安裝其他套件）：

```
python3 build.py
cd dist && python3 -m http.server 8000
```

再用瀏覽器開 http://localhost:8000 。

## 發布

`.github/workflows/deploy.yml` 會在每次推送到 `main` 時執行 `build.py`，並把 `dist/` 發布到 GitHub Pages。
第一次使用時，要到 repo 的 Settings → Pages，把 Source 設成「GitHub Actions」。

## 可見範圍

網站加了 `noindex` 與 `robots.txt`，搜尋引擎不會收錄；但知道網址的人都能打開，repo 本身也是公開的。
題本圖片與聽力音檔取自心測中心公開的歷屆試題，僅供教學參考。
