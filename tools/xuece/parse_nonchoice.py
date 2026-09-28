"""解析「非選擇題參考答案與評分原則」PDF → {題號: {"ref": 滿分參考答案, "parts": [[小題, 滿分], ...]}}。"""
import re

import pymupdf


def parse(path):
    text = "".join(p.get_text() for p in pymupdf.open(path))
    text = re.sub(r"\n\s*\d+\s*\n", "\n", text)  # 頁碼
    out = {}
    blocks = re.split(r"\n\s*第\s*(\d+)\s*題\s*\n", text)
    for i in range(1, len(blocks), 2):
        n, body = int(blocks[i]), blocks[i + 1]
        m = re.search(r"滿分參考答案[：:](.*?)二、評分原則", body, re.S)
        ref = m[1] if m else ""
        ref = "\n".join(l.strip() for l in ref.split("\n") if l.strip())
        ref = re.sub(r"\n(?=[^\n(（①②③④⑤或])", "", ref)  # 併回被換行切斷的句子
        parts = []
        for sub in re.split(r"\n\s*第\s*\d+\s*題\s*", body.split("二、評分原則", 1)[-1])[1:]:
            label = re.match(r"\s*([(（]\s*\S+?\s*[)）]\s*[①-⑩]?)?", sub)[1] or ""
            pts = [int(p) for p in re.findall(r"\n\s*(\d+)\s*分", sub)]
            if pts:
                parts.append([re.sub(r"\s", "", label), max(pts)])
        out[n] = {"ref": ref, "parts": parts}
    return out


if __name__ == "__main__":
    import sys
    for y in sys.argv[1:]:
        for n, v in parse(f"incoming/xuece/{y}-nonchoice.pdf").items():
            print(y, n, sum(p for _, p in v["parts"]), "分", v["parts"], "|", v["ref"][:60].replace("\n", " / "))
