// docs/**/*.md の ```mermaid ブロックを mermaid 公式 parser に通して
// JSON で結果を返す。
//
// 使い方:
//   NODE_PATH=node_modules node meta/scripts/mermaid_parse.mjs <docs-root>
//
// 必須 npm: mermaid, jsdom, dompurify
//
// check_mermaid_syntax.py から呼ばれる想定。直接 mkdocs ビルドより速く
// レンダリング前に block 単位で構文異常を検出できる。

import { JSDOM } from "jsdom";
import createDOMPurify from "dompurify";
import fs from "fs";
import path from "path";

const dom = new JSDOM("<!DOCTYPE html><html><body></body></html>");
globalThis.window = dom.window;
globalThis.document = dom.window.document;
globalThis.DOMPurify = createDOMPurify(dom.window);

const mermaid = (await import("mermaid")).default;
mermaid.initialize({ startOnLoad: false, securityLevel: "loose" });

const root = process.argv[2];
if (!root) {
  console.error("usage: node mermaid_parse.mjs <docs-root>");
  process.exit(2);
}

const files = [];
function walk(p) {
  for (const e of fs.readdirSync(p, { withFileTypes: true })) {
    const fp = path.join(p, e.name);
    if (e.isDirectory()) walk(fp);
    else if (e.name.endsWith(".md")) files.push(fp);
  }
}
walk(root);

let total = 0;
const errors = [];
for (const f of files) {
  const text = fs.readFileSync(f, "utf8");
  const lines = text.split("\n");
  let i = 0;
  while (i < lines.length) {
    if (/^\s*```mermaid\s*$/.test(lines[i])) {
      const start = i + 1;
      const blk = [];
      let j = i + 1;
      while (j < lines.length && !/^\s*```\s*$/.test(lines[j])) {
        blk.push(lines[j]);
        j++;
      }
      total++;
      const src = blk.join("\n");
      try {
        await mermaid.parse(src);
      } catch (e) {
        errors.push({
          file: f,
          line: start,
          err: String(e).split("\n").slice(0, 5).join(" | "),
        });
      }
      i = j + 1;
      continue;
    }
    i++;
  }
}

process.stdout.write(JSON.stringify({ total, bad: errors.length, errors }, null, 2));
