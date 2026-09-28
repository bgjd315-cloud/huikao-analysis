// 一次性搬遷工具：把 Artifact 版的單頁 HTML 拆成「模板＋逐年資料檔」。
// 用法：node migrate.js <原始 index.html> <科目代號> <專案根目錄>
// 產出：templates/<科目>.html、data/<科目>/<年度>.json
// 規則：
//   1. <script type="application/json"> 區塊若以年度為鍵 → 拆到逐年資料檔，模板留 {{json:區塊id}}
//   2. 頂層 const 若是「以年度為鍵的純資料物件」→ 拆到逐年資料檔（鍵名 js:常數名），模板留 {{js:常數名}}
//   3. const YEARS = [...] → 模板留 {{years}}
const fs = require("fs"), path = require("path");
let acorn;
try { acorn = require("acorn"); } catch (e) { acorn = require("/opt/node-tools/node_modules/acorn"); }

const [src, subj, root] = process.argv.slice(2);
let html = fs.readFileSync(src, "utf8");
const isYear = k => /^1\d\d$/.test(String(k));
const perYear = {};           // year -> {key: value}
const put = (y, k, v) => ((perYear[y] ??= {})[k] = v);

// 1. JSON 區塊
html = html.replace(/<script id="(\w+)" type="application\/json">([\s\S]*?)<\/script>/g, (m, id, body) => {
  const o = JSON.parse(body);
  if (o && typeof o === "object" && !Array.isArray(o) && Object.keys(o).length && Object.keys(o).every(isYear)) {
    for (const [y, v] of Object.entries(o)) put(y, "json:" + id, v);
    return `<script id="${id}" type="application/json">{{json:${id}}}</script>`;
  }
  return m;
});

// 2 & 3. 最後一個一般 <script> 內的頂層 const
const sIdx = html.lastIndexOf("<script>");
const eIdx = html.indexOf("</script>", sIdx);
const code = html.slice(sIdx + 8, eIdx);
const ast = acorn.parse(code, { ecmaVersion: "latest", sourceType: "script" });
const PURE = new Set(["Literal", "ArrayExpression", "ObjectExpression", "Property", "TemplateLiteral", "TemplateElement", "UnaryExpression", "Identifier"]);
function pure(n, parentIsKey) {
  if (!n || typeof n.type !== "string") return true;
  if (!PURE.has(n.type)) return false;
  if (n.type === "Identifier" && !parentIsKey) return false;
  if (n.type === "TemplateLiteral" && n.expressions.length) return false;
  if (n.type === "Property") return !n.computed && pure(n.value);
  for (const k of Object.keys(n)) {
    if (k === "type" || k === "start" || k === "end") continue;
    const v = n[k];
    if (Array.isArray(v)) { if (!v.every(x => pure(x))) return false; }
    else if (v && typeof v.type === "string") { if (!pure(v, k === "key")) return false; }
  }
  return true;
}
const edits = [];
for (const st of ast.body) {
  if (st.type !== "VariableDeclaration") continue;
  for (const d of st.declarations) {
    if (!d.init || d.id.type !== "Identifier") continue;
    const name = d.id.name, init = d.init;
    if (name === "YEARS" && init.type === "ArrayExpression") { edits.push([init.start, init.end, "{{years}}"]); continue; }
    if (init.type !== "ObjectExpression" || !init.properties.length || !pure(init)) continue;
    const keys = init.properties.map(p => p.key.type === "Literal" ? p.key.value : p.key.name);
    if (!keys.every(isYear)) continue;
    const val = Function('"use strict";return (' + code.slice(init.start, init.end) + ")")();
    for (const [y, v] of Object.entries(val)) put(y, "js:" + name, v);
    edits.push([init.start, init.end, `{{js:${name}}}`]);
  }
}
let newCode = code;
for (const [a, b, r] of edits.sort((x, y) => y[0] - x[0])) newCode = newCode.slice(0, a) + r + newCode.slice(b);
html = html.slice(0, sIdx + 8) + newCode + html.slice(eIdx);

fs.mkdirSync(path.join(root, "templates"), { recursive: true });
fs.writeFileSync(path.join(root, "templates", subj + ".html"), html);
for (const [y, obj] of Object.entries(perYear)) {
  const dir = path.join(root, "data", subj);
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(path.join(dir, y + ".json"), JSON.stringify(obj, null, 1) + "\n");
}
console.log(subj, "years:", Object.keys(perYear).join(","), "keys:", Object.keys(perYear[Object.keys(perYear)[0]] || {}).join(", "));
