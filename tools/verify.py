#!/usr/bin/env python3
"""用無頭瀏覽器打開 dist/ 每一頁，檢查：JS 錯誤、載入失敗的檔案、主要區塊是否有內容。
可選擇與舊版頁面比對畫面文字：python3 tools/verify.py --compare 舊版資料夾對照.json
用法：python3 build.py && python3 tools/verify.py
"""
import functools
import http.server
import json
import sys
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
PAGES = ["", "guowen/", "english/", "math/", "social/", "science/", "xuece/", "xuece-en/", "xuece-math/", "xuece-soc/", "xuece-sci/", "xuece-earth/", "xuece-phy/", "xuece-chem/", "xuece-bio/", "xuece-hist/", "xuece-geo/"]


def serve(directory, port):
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass

    h = functools.partial(Quiet, directory=str(directory))
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", port), h)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def page_text(browser, url):
    errs, bad = [], []
    pg = browser.new_page()
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("response", lambda r: r.status >= 400 and bad.append(f"{r.status} {r.url}"))
    pg.goto(url, wait_until="networkidle")
    # 打開試題庫前幾題，讓題目圖片實際載入
    pg.evaluate("document.querySelectorAll('details.qitem').forEach((d,i)=>{if(i<5)d.open=true})")
    pg.wait_for_timeout(800)
    text = pg.evaluate("document.body.innerText")
    pg.close()
    return text, errs, bad


def main():
    compare = None
    if "--compare" in sys.argv:
        compare = json.loads(Path(sys.argv[sys.argv.index("--compare") + 1]).read_text())
    serve(ROOT / "dist", 8765)
    ok = True
    with sync_playwright() as p:
        b = p.chromium.launch()
        for i, path in enumerate(PAGES):
            text, errs, bad = page_text(b, f"http://127.0.0.1:8765/{path}")
            bad = [x for x in bad if "fonts.g" not in x]
            status = "OK" if not errs and not bad and len(text) > 500 else "有問題"
            print(f"[{status}] /{path}  文字 {len(text)} 字  JS錯誤 {len(errs)}  載入失敗 {len(bad)}")
            for e in errs[:5] + bad[:5]:
                print("    ", e)
            if compare and path in compare:
                old_dir = Path(compare[path])
                serve(old_dir, 8800 + i)
                old, *_ = page_text(b, f"http://127.0.0.1:{8800 + i}/")
                same = old.strip() == text.strip()
                print(f"     與舊版畫面文字{'完全一致' if same else '不一致'}")
                if not same:
                    ok = False
                    import difflib
                    for line in list(difflib.unified_diff(old.splitlines(), text.splitlines(), lineterm="", n=0))[:20]:
                        print("       ", line)
            ok = ok and status == "OK"
        b.close()
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
