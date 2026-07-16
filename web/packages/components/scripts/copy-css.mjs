// Mirrors every *.css file from src/ into dist/, preserving relative paths,
// since tsc only emits .ts/.tsx -> .js and leaves other assets untouched.
import { cp, mkdir, readdir } from 'node:fs/promises';
import { dirname, join, relative } from 'node:path';
import { fileURLToPath } from 'node:url';

const rootDir = dirname(fileURLToPath(import.meta.url));
const srcDir = join(rootDir, '..', 'src');
const distDir = join(rootDir, '..', 'dist');

async function walk(dir) {
  const entries = await readdir(dir, { withFileTypes: true });
  const files = [];
  for (const entry of entries) {
    const full = join(dir, entry.name);
    if (entry.isDirectory()) {
      files.push(...(await walk(full)));
    } else if (entry.name.endsWith('.css')) {
      files.push(full);
    }
  }
  return files;
}

const cssFiles = await walk(srcDir);
for (const file of cssFiles) {
  const rel = relative(srcDir, file);
  const dest = join(distDir, rel);
  await mkdir(dirname(dest), { recursive: true });
  await cp(file, dest);
}

console.log(`Copied ${cssFiles.length} CSS file(s) into dist/`);
