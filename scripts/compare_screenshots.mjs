#!/usr/bin/env node
/** Capture matching live/local screenshots with Playwright when it is installed.
 *
 * Usage:
 *   npm install --no-save playwright
 *   node scripts/compare_screenshots.mjs http://127.0.0.1:8000
 */
import { mkdir } from 'node:fs/promises';
import path from 'node:path';
import { chromium } from 'playwright';

const localOrigin = process.argv[2] || 'http://127.0.0.1:8000';
const pages = ['home', 'my-science', 'my-skills', 'my-cv', 'news', 'contact-me'];
const widths = [1440, 1024, 768, 390];
const output = path.resolve('migration/screenshots');
await mkdir(output, { recursive: true });

const browser = await chromium.launch();
for (const width of widths) {
  const context = await browser.newContext({ viewport: { width, height: width === 390 ? 844 : 900 } });
  const page = await context.newPage();
  for (const slug of pages) {
    for (const [kind, origin] of [['live', 'https://www.drtuff.com'], ['local', localOrigin]]) {
      await page.goto(`${origin}/${slug}`, { waitUntil: 'networkidle' });
      await page.screenshot({ path: path.join(output, `${slug}-${width}-${kind}.png`), fullPage: true });
    }
  }
  await context.close();
}
await browser.close();
console.log(`Screenshots written to ${output}`);
