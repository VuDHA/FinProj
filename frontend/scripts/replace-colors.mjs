import fs from "fs";
import path from "path";

const srcDir = path.resolve(process.cwd(), "src");

const replacements = [
  // primary text
  { from: "text-slate-900", to: "text-theme" },
  { from: "text-slate-800", to: "text-theme" },
  { from: "text-slate-950", to: "text-theme" },
  // muted text
  { from: "text-slate-700", to: "text-theme-muted" },
  { from: "text-slate-600", to: "text-theme-muted" },
  { from: "text-slate-500", to: "text-theme-muted" },
  { from: "text-slate-400", to: "text-theme-muted" },
  { from: "text-slate-300", to: "text-theme-muted" },
  { from: "text-slate-200", to: "text-theme-muted" },
  { from: "text-slate-100", to: "text-theme-muted" },
  // inverse text (light surfaces)
  { from: "text-slate-50", to: "text-theme-inverse" },

  // light backgrounds
  { from: "bg-slate-50", to: "bg-surface-elevated" },
  { from: "bg-slate-100", to: "bg-surface-elevated" },
  { from: "bg-slate-200", to: "bg-surface-elevated" },
  { from: "bg-slate-300", to: "bg-surface-elevated" },
  { from: "bg-slate-400", to: "bg-surface-elevated" },
  { from: "bg-slate-500", to: "bg-surface-elevated" },
  // dark surfaces / overlays (kept neutral; review manually if needed)
  { from: "bg-slate-600", to: "bg-surface" },
  { from: "bg-slate-700", to: "bg-surface" },
  { from: "bg-slate-800", to: "bg-surface" },
  { from: "bg-slate-900", to: "bg-surface" },
  { from: "bg-slate-950", to: "bg-surface" },

  // borders / rings
  { from: "border-slate-200", to: "border-fintech-border" },
  { from: "border-slate-300", to: "border-fintech-border" },
  { from: "ring-slate-200", to: "ring-fintech-border" },
  { from: "ring-slate-300", to: "ring-fintech-border" },
  { from: "placeholder-slate-400", to: "placeholder-theme-muted" },

  // white/black on colored/dark surfaces -> inverse tokens
  { from: "text-white", to: "text-theme-inverse" },
  { from: "text-black", to: "text-theme" },
  // white backgrounds -> surface-elevated
  { from: "bg-white", to: "bg-surface-elevated" },
  { from: "bg-black", to: "bg-surface" },
];

function processFile(filePath) {
  let content = fs.readFileSync(filePath, "utf-8");
  let changed = false;
  for (const { from, to } of replacements) {
    const regex = new RegExp(from.replace(/[-/\\^$*+?.()|[\]{}]/g, "\\$&"), "g");
    const newContent = content.replace(regex, to);
    if (newContent !== content) {
      changed = true;
      content = newContent;
    }
  }
  if (changed) {
    fs.writeFileSync(filePath, content, "utf-8");
    console.log(`Updated: ${filePath}`);
  }
}

function walk(dir) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      walk(fullPath);
    } else if (
      entry.isFile() &&
      (fullPath.endsWith(".tsx") || fullPath.endsWith(".ts"))
    ) {
      processFile(fullPath);
    }
  }
}

walk(srcDir);
