// Run: NODE_PATH=$(npm root -g) node tests/dashboard.spec.mjs   (needs playwright)
// Copies the fixture to site/data/repos.json, serves site/, checks both widths, then removes the copy.
import { createRequire } from 'node:module';
import { spawn, execSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const require = createRequire(import.meta.url);
let chromium;
try { ({ chromium } = require('playwright')); }
catch { ({ chromium } = require(path.join(execSync('npm root -g').toString().trim(), 'playwright'))); }

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const shots = process.env.SHOT_DIR || '/tmp';
const dataFile = path.join(root, 'site/data/repos.json');
fs.mkdirSync(path.dirname(dataFile), { recursive: true });
fs.copyFileSync(path.join(root, 'tests/sample-repos.json'), dataFile);
const port = 8700 + Math.floor(Math.random() * 200);
const server = spawn('python3', ['-m', 'http.server', String(port), '-d', path.join(root, 'site')], { stdio: 'ignore' });
await new Promise(r => setTimeout(r, 1000));

let fails = 0;
const check = (label, ok) => { console.log((ok ? 'PASS ' : 'FAIL ') + label); if (!ok) fails++; };
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' });
try {
  for (const [w, h] of [[390, 844], [1280, 800]]) {
    const page = await browser.newPage({ viewport: { width: w, height: h } });
    const errors = [];
    page.on('console', m => { if (m.type() === 'error' && !/fonts\.g|ERR_|404/.test(m.text())) errors.push(m.text()); });
    page.on('pageerror', e => errors.push(String(e)));
    await page.goto(`http://localhost:${port}/`);
    await page.waitForSelector('#main:not([hidden])');
    const t = s => `[${w}] ${s}`;
    check(t('header shows counts'), (await page.textContent('#counts')).includes('10 repos'));
    check(t('Updated line'), /^Updated .+\(\d{1,2} \w{3} \d{2}\)$/.test(await page.textContent('#updated')));
    for (const id of ['s-attn', 's-ent', 's-fam', 's-ideas'])
      check(t(`section ${id} visible`), await page.isVisible('#' + id));
    check(t('health section hidden (no file)'), !(await page.isVisible('#s-health')));
    check(t('5 entertainment tiles'), (await page.locator('#tiles .tile').count()) === 5);
    check(t('3 live tiles are links'), (await page.locator('#tiles a.tile').count()) === 3);
    const attn = await page.textContent('#attn');
    for (const [label, needle] of [['no main', 'No main branch'], ['default branch', 'Default branch is master'],
      ['failed run', 'Last run on main failed'], ['no charter', 'No charter yet'], ['quiet', 'Quiet for 45 days'], ['dormant', 'Dormant']])
      check(t(`attention: ${label}`), attn.includes(needle));
    const heads = await page.locator('.fam h3').allTextContents();
    check(t('family order'), heads.join('|') === 'Entertainment|Home|Finance|Hobby|No charter yet');
    check(t('10 cards'), (await page.locator('.card').count()) === 10);
    check(t('3 ideas listed'), (await page.locator('#ideas li').count()) === 3);
    const noScroll = await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth);
    check(t('no sideways scroll'), noScroll);
    if (w === 1280) {
      const cols = await page.evaluate(() => getComputedStyle(document.querySelector('.cards')).gridTemplateColumns.split(' ').length);
      check(t('cards in a grid (3+ columns)'), cols >= 3);
    }
    const tileH = await page.evaluate(() => Math.min(...[...document.querySelectorAll('#tiles .tile')].map(e => e.getBoundingClientRect().height)));
    check(t('tiles are big tap targets'), tileH >= 100);
    check(t('no console errors'), errors.length === 0);
    if (errors.length) console.log(errors);
    await page.screenshot({ path: path.join(shots, `control-room-${w}.png`), fullPage: true });
    await page.close();
  }
  // collector reported an error (e.g. no repos found)
  fs.writeFileSync(dataFile, JSON.stringify({ generated_at: '2026-10-19T03:02:13Z', owner: 'jcm-book-library', owner_type: 'user',
    repos: [], ideas: [], error: 'No repos found for jcm-book-library (checked as a user account).' }));
  {
    const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
    await page.goto(`http://localhost:${port}/`);
    await page.waitForSelector('#error:not([hidden])');
    check('collector error shown', (await page.textContent('#error')).includes('No repos found for jcm-book-library'));
    check('main hidden on collector error', !(await page.isVisible('#main')));
    await page.close();
  }
  // error state
  fs.unlinkSync(dataFile);
  const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
  await page.goto(`http://localhost:${port}/`);
  await page.waitForSelector('#error:not([hidden])');
  check('error message when data missing', (await page.textContent('#error')).includes("Couldn't load"));
  await page.screenshot({ path: path.join(shots, 'control-room-error.png') });
} finally {
  await browser.close();
  server.kill();
  fs.rmSync(dataFile, { force: true });
}
console.log(fails ? `${fails} FAILED` : 'ALL PASSED');
process.exit(fails ? 1 : 0);
