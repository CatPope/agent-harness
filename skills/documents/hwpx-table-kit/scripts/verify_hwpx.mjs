// Roundtrip verification: parse a generated .hwpx back with kordoc and
// print the tables it recovers. Confirms the file is a valid HWPX whose
// tables/data survived generation.
//
//   node verify_hwpx.mjs <file.hwpx>
import { parse } from "kordoc";
import { readFileSync } from "fs";

const file = process.argv[2];
if (!file) { console.error("usage: node verify_hwpx.mjs <file.hwpx>"); process.exit(2); }

const r = await parse(readFileSync(file).buffer);
if (!r.success) { console.error("PARSE FAIL:", r.code, r.error); process.exit(1); }

const tables = r.blocks.filter(b => b.type === "table");
console.log("OK parsed. tables:", tables.length);
console.log("\n===== MARKDOWN =====\n");
console.log(r.markdown);
