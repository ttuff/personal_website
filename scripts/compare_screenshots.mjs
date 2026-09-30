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
const viewports = [
  { width: 1440, height: 1000 },
  { width: 1280, height: 900 },
  { width: 768, height: 1024 },
  { width: 390, height: 844 },
];
const output = path.resolve('migration/screenshots/final');
await mkdir(output, { recursive: true });

const browser = await chromium.launch();
for (const viewport of viewports) {
  const context = await browser.newContext({ viewport });
  const livePage = await context.newPage();
  const localPage = await context.newPage();
  for (const slug of pages) {
    for (const [kind, origin, page] of [
      ['live', 'https://www.drtuff.com', livePage],
      ['local', localOrigin, localPage],
    ]) {
      const suffix = kind === 'local' ? '/' : '';
      await page.goto(`${origin}/${slug}${suffix}`, { waitUntil: 'load' });
      await page.evaluate(() => document.fonts?.ready || Promise.resolve());
      await page.evaluate(() => window.scrollTo(0, document.documentElement.scrollHeight));
      await page.waitForTimeout(300);
      await page.evaluate(() => window.scrollTo(0, 0));
      await page.waitForTimeout(300);
      const stem = `${slug}-${viewport.width}x${viewport.height}-${kind}`;
      await page.screenshot({ path: path.join(output, `${stem}-viewport.png`) });
      await page.screenshot({ path: path.join(output, `${stem}-full.png`), fullPage: true });
    }
  }
  await context.close();
}
await browser.close();
console.log(`Screenshots written to ${output}`);
