"""解析大考中心「選擇題答案」PDF → {題號: 答案}；「／」為非選擇題。"""
import re, sys, json, pymupdf
def parse(path):
    toks=[t.strip() for t in pymupdf.open(path)[0].get_text().split("\n") if t.strip()]
    ans={}
    i=0
    while i < len(toks)-1:
        if re.fullmatch(r"\d{1,2}", toks[i]) and re.fullmatch(r"[A-E]+|／|/|[A-E]或[A-E]+|.{1,12}", toks[i+1]) and not re.fullmatch(r"\d{1,2}",toks[i+1]):
            n=int(toks[i]); 
            if n not in ans: ans[n]=toks[i+1]
            i+=2
        else: i+=1
    return dict(sorted(ans.items()))
if __name__=="__main__":
    out={}
    for y in range(107,116):
        a=parse(f"incoming/xuece/{y}-ans.pdf"); out[y]=a
        multi=[n for n,v in a.items() if re.fullmatch(r"[A-E]{2,}",v)]
        non=[n for n,v in a.items() if v in("／","/")]
        odd={n:v for n,v in a.items() if not re.fullmatch(r"[A-E]+|／|/",v)}
        print(y, "題數",len(a),"最大題號",max(a),"多選",f"{min(multi)}–{max(multi)}" if multi else "-", "非選",non, "特殊",odd)
    json.dump(out,open("incoming/xuece/answers.json","w",encoding="utf-8"),ensure_ascii=False,indent=0)
