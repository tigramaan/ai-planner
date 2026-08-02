#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";

const root = process.cwd();
const maxLines = Number(process.env.MAX_SOURCE_FILE_LINES || 500);
const excludedDirs = new Set([
  ".git", ".venv", "node_modules", "dist", "build", "coverage", ".next", ".cache", ".artifacts",
  "test-results", "playwright-report", "vendor", "generated",
]);
const excludedFiles = new Set(["package-lock.json", "pnpm-lock.yaml", "yarn.lock"]);
const sourceExtensions = new Set([
  ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".vue", ".py", ".go", ".rs",
  ".java", ".kt", ".swift", ".php", ".css", ".scss", ".html", ".md",
]);
const violations = [];

function walk(dir) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    if (entry.name.startsWith(".") && entry.name !== ".github") {
      if (excludedDirs.has(entry.name)) continue;
    }
    const full = path.join(dir, entry.name);
    const rel = path.relative(root, full).replaceAll(path.sep, "/");
    if (entry.isDirectory()) {
      if (excludedDirs.has(entry.name)) continue;
      walk(full);
      continue;
    }
    if (!entry.isFile()) continue;
    if (excludedFiles.has(entry.name)) continue;
    if (entry.name.endsWith(".min.js")) continue;
    if (!sourceExtensions.has(path.extname(entry.name))) continue;
    const lines = fs.readFileSync(full, "utf8").split(/\r?\n/).length;
    if (lines > maxLines) violations.push({ file: rel, lines });
  }
}

walk(root);
if (violations.length) {
  console.error(`File line guard failed: ${violations.length} file(s) exceed ${maxLines} lines.`);
  for (const item of violations) console.error(`${item.lines}\t${item.file}`);
  process.exit(1);
}
console.log(`File line guard passed: max ${maxLines} lines.`);
