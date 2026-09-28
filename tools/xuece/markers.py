"""找出試卷中的題號、題組標題、區段標題與其位置。"""
import re, pymupdf
QRE=re.compile(r"^\s*(\d{1,2})\s*[.．]\s*\S")
GRE=re.compile(r"^\s*(\d{1,2})\s*[-－–~～]\s*(\d{1,2})\s*為題組")
SRE=re.compile(r"^\s*(第[壹貳參肆]部分|[一二三四]、\s*(單選|多選|混合|非選|綜合)|說明：)")
def lines(page):
    out=[]
    for b in page.get_text("dict")["blocks"]:
        for l in b.get("lines",[]):
            t="".join(s["text"] for s in l["spans"])
            if t.strip(): out.append((l["bbox"],t))
    out.sort(key=lambda z:(round(z[0][1]),z[0][0]))
    return out
def markers(path):
    d=pymupdf.open(path); M=[]
    for pn in range(1,len(d)):
        for (x0,y0,x1,y1),t in lines(d[pn]):
            if x0>75 or y0<75 or y0>780: continue
            if m:=GRE.match(t): M.append(("G",pn,y0,(int(m[1]),int(m[2])),t.strip()))
            elif m:=QRE.match(t): M.append(("Q",pn,y0,int(m[1]),t.strip()))
            elif SRE.match(t): M.append(("S",pn,y0,None,t.strip()))
    return M
if __name__=="__main__":
    import json
    ans=json.load(open("incoming/xuece/answers.json",encoding="utf-8"))
    for y in range(107,116):
        M=markers(f"incoming/xuece/{y}-paper.pdf")
        qs=[m[3] for m in M if m[0]=="Q"]
        exp=list(range(1,len(ans[str(y)])+1))
        seq_ok = qs==exp
        print(y,"Q",len(qs),"預期",len(exp),"順序正確" if seq_ok else f"不符 {qs}", "| 題組",[m[3] for m in M if m[0]=="G"])
