#!/usr/bin/env node
/*
 * build_deck.js — スライドプラン(JSON) から「クリーン学術系」テーマの .pptx を生成する。
 *
 *   node build_deck.js plan.json out.pptx
 *
 * plan.json の構造は SKILL.md と references/plan_schema.md を参照。
 * 図は path で参照し、実寸をヘッダから取得してボックス内に中央寄せ・アスペクト比維持で配置する。
 *
 * 設計方針:
 *   - レイアウトは type と中身から自動決定（figure の有無・数、bullet 数）。plan 側で layout を明示すれば上書き。
 *   - 箇条書きは数に応じてフォントサイズを自動調整し、はみ出しを避ける。
 *   - 全ページ共通の細い上部アクセントバー + フッター(通し番号)で「流れ」を一定に保つ。
 */

// ---- module resolution (global npm packages) ---------------------------------
function loadModule(name) {
  try { return require(name); } catch (e) {
    const Module = require('module');
    const cands = [];
    try { cands.push(require('child_process').execSync('npm root -g', { encoding: 'utf8' }).trim()); } catch (_) {}
    cands.push('/usr/local/lib/node_modules_global/lib/node_modules',
               '/usr/local/lib/node_modules', '/usr/lib/node_modules');
    process.env.NODE_PATH = [process.env.NODE_PATH, ...cands].filter(Boolean).join(':');
    Module._initPaths();
    return require(name);
  }
}
const pptxgen = loadModule('pptxgenjs');

const path = require('path');
const fs = require('fs');

// ---- theme -------------------------------------------------------------------
const THEMES = {
  academic: {
    bg: 'FFFFFF', ink: '1A1A2E', navy: '1F4E79', accent: '2E6DA4',
    band: 'EAF0F6', rule: 'C7D2DE', muted: '5A6B7B', white: 'FFFFFF',
    font: 'Noto Sans CJK JP', fontHead: 'Noto Sans CJK JP',
  },
};

// ---- geometry (LAYOUT_WIDE = 13.333 x 7.5 in) --------------------------------
const PW = 13.333, PH = 7.5;
const MX = 0.62;                 // 左右マージン
const CONTENT_W = PW - MX * 2;

const argv = process.argv.slice(2);
if (argv.length < 2) { console.error('usage: node build_deck.js plan.json out.pptx'); process.exit(1); }
const planPath = argv[0], outPath = argv[1];
const plan = JSON.parse(fs.readFileSync(planPath, 'utf8'));
const baseDir = path.dirname(path.resolve(planPath));
const T = Object.assign({}, THEMES[plan.theme] || THEMES.academic);
// フォントは plan で上書きできる（例: "Yu Gothic", "BIZ UDPGothic"）。
// 注意: 指定フォントが変換環境(LibreOffice)に無い場合は自動代替されるため、
// 見た目を確実にしたいなら実在するフォント名を使うこと。
if (plan.font) { T.font = plan.font; T.fontHead = plan.fontHead || plan.font; }
if (plan.fontHead) { T.fontHead = plan.fontHead; }

const pptx = new pptxgen();
pptx.defineLayout({ name: 'W', width: PW, height: PH });
pptx.layout = 'W';
pptx.theme = { headFontFace: T.fontHead, bodyFontFace: T.font };

// ---- helpers -----------------------------------------------------------------
// PNG/JPEG のヘッダから実寸を同期取得（外部依存なし）。
function readImageSizeSync(file) {
  const b = fs.readFileSync(file);
  if (b.length > 24 && b[0] === 0x89 && b[1] === 0x50) {          // PNG
    return { w: b.readUInt32BE(16), h: b.readUInt32BE(20) };
  }
  if (b[0] === 0xff && b[1] === 0xd8) {                            // JPEG
    let i = 2;
    while (i < b.length) {
      if (b[i] !== 0xff) { i++; continue; }
      const marker = b[i + 1];
      if (marker >= 0xc0 && marker <= 0xcf && marker !== 0xc4 && marker !== 0xc8 && marker !== 0xcc) {
        return { h: b.readUInt16BE(i + 5), w: b.readUInt16BE(i + 7) };
      }
      i += 2 + b.readUInt16BE(i + 2);
    }
  }
  return { w: 4, h: 3 };
}

function fitBox(imgWpx, imgHpx, boxX, boxY, boxW, boxH) {
  // ボックス内にアスペクト比維持で最大内接、中央寄せした {x,y,w,h}(inch) を返す。
  const ar = imgWpx / imgHpx, bar = boxW / boxH;
  let w, h;
  if (ar > bar) { w = boxW; h = boxW / ar; } else { h = boxH; w = boxH * ar; }
  return { x: boxX + (boxW - w) / 2, y: boxY + (boxH - h) / 2, w, h };
}

function resolveImg(p) {
  if (!p) return null;
  const abs = path.isAbsolute(p) ? p : path.join(baseDir, p);
  return fs.existsSync(abs) ? abs : (fs.existsSync(p) ? p : null);
}

let pageNo = 0;
function chrome(slide, opts = {}) {
  slide.background = { color: T.bg };
  slide.addShape(pptx.ShapeType.rect, { x: 0, y: 0, w: PW, h: 0.14, fill: { color: T.navy }, line: { type: 'none' } });
  if (opts.footer !== false) {
    pageNo += 1;
    if (plan.footer) slide.addText(plan.footer, { x: MX, y: PH - 0.42, w: CONTENT_W - 1, h: 0.3, fontFace: T.font, fontSize: 9, color: T.muted, align: 'left', valign: 'middle', margin: 0 });
    slide.addText(String(pageNo), { x: PW - MX - 1, y: PH - 0.42, w: 1, h: 0.3, fontFace: T.font, fontSize: 9, color: T.muted, align: 'right', valign: 'middle', margin: 0 });
  }
}

function addTitleBlock(slide, title, kicker) {
  let y = 0.5;
  if (kicker) {
    slide.addText(String(kicker), { x: MX, y: y, w: CONTENT_W, h: 0.3, fontFace: T.font, fontSize: 12, bold: true, color: T.accent, charSpacing: 1, margin: 0, valign: 'bottom' });
    y += 0.34;
  }
  slide.addText(title || '', { x: MX, y: y, w: CONTENT_W, h: 0.72, fontFace: T.fontHead, fontSize: 26, bold: true, color: T.navy, margin: 0, valign: 'top' });
  slide.addShape(pptx.ShapeType.line, { x: MX, y: y + 0.82, w: CONTENT_W, h: 0, line: { color: T.rule, width: 1 } });
  return y + 1.02; // 本文開始 y
}

function bulletObjs(bullets, fontSize) {
  return bullets.map((b, i) => {
    const level = b.level || 0;
    const isHead = b.head === true;
    return {
      text: b.text,
      options: {
        fontFace: T.font,
        fontSize: isHead ? fontSize + 1 : fontSize - level * 1,
        bold: !!(isHead || b.bold),
        color: isHead ? T.navy : T.ink,
        bullet: level === 0 ? { code: '2022', indent: 16 } : { code: '2013', indent: 16 },
        indentLevel: level,
        paraSpaceAfter: isHead ? 4 : (level === 0 ? 8 : 4),
        paraSpaceBefore: isHead && i > 0 ? 6 : 0,
        breakLine: true,
        align: 'left',
        lineSpacingMultiple: 1.06,
      },
    };
  });
}

function autoFont(bullets, height, widthIn) {
  // bullet 数と使える高さからおおよそのフォントサイズを決める。
  const wrapChars = widthIn > 6 ? 34 : 20;
  const n = bullets.reduce((s, b) => s + 1 + Math.floor((b.text || '').length / wrapChars), 0);
  const cap = height / Math.max(1, n) * 46;   // 経験則
  return Math.max(12, Math.min(18, Math.round(cap)));
}

function addBullets(slide, bullets, x, y, w, h) {
  if (!bullets || !bullets.length) return;
  const fs_ = autoFont(bullets, h, w);
  slide.addText(bulletObjs(bullets, fs_), { x, y, w, h, valign: 'top', margin: 0 });
}

function addFigure(slide, fig, boxX, boxY, boxW, boxH) {
  const p = resolveImg(fig.path);
  const capH = fig.caption ? 0.42 : 0;
  const imgBoxH = boxH - capH;
  if (!p) {
    slide.addText('[図が見つかりません: ' + fig.path + ']', { x: boxX, y: boxY, w: boxW, h: imgBoxH, align: 'center', valign: 'middle', fontFace: T.font, fontSize: 12, color: 'B00020' });
  } else {
    const sz = readImageSizeSync(p);
    const f = fitBox(sz.w, sz.h, boxX + 0.05, boxY + 0.05, boxW - 0.1, imgBoxH - 0.1);
    slide.addShape(pptx.ShapeType.rect, { x: f.x - 0.04, y: f.y - 0.04, w: f.w + 0.08, h: f.h + 0.08, fill: { color: 'FFFFFF' }, line: { color: T.rule, width: 0.75 } });
    slide.addImage({ path: p, x: f.x, y: f.y, w: f.w, h: f.h });
  }
  if (fig.caption) {
    slide.addText(fig.caption, { x: boxX, y: boxY + imgBoxH, w: boxW, h: capH, align: 'center', valign: 'top', fontFace: T.font, fontSize: 11, italic: true, color: T.muted, margin: 0 });
  }
}

function normFigures(s) {
  if (s.figures && s.figures.length) return s.figures;
  if (s.figure) return [s.figure];
  return [];
}

// ---- slide builders ----------------------------------------------------------
function slideTitle(s) {
  const sl = pptx.addSlide();
  chrome(sl, { footer: false });
  sl.addShape(pptx.ShapeType.rect, { x: 0, y: 2.5, w: PW, h: 2.5, fill: { color: T.band }, line: { type: 'none' } });
  sl.addShape(pptx.ShapeType.rect, { x: MX, y: 2.62, w: 0.09, h: 2.26, fill: { color: T.navy }, line: { type: 'none' } });
  sl.addText(s.title || '', { x: MX + 0.28, y: 2.7, w: CONTENT_W - 0.3, h: 1.5, fontFace: T.fontHead, fontSize: 34, bold: true, color: T.navy, valign: 'middle', margin: 0 });
  if (s.subtitle) sl.addText(s.subtitle, { x: MX + 0.28, y: 4.18, w: CONTENT_W - 0.3, h: 0.7, fontFace: T.font, fontSize: 18, color: T.ink, valign: 'middle', margin: 0 });
  if (s.meta) sl.addText(s.meta, { x: MX + 0.28, y: 5.25, w: CONTENT_W - 0.3, h: 0.4, fontFace: T.font, fontSize: 12, color: T.muted, valign: 'middle', margin: 0 });
}

function slideAgenda(s) {
  const sl = pptx.addSlide();
  chrome(sl);
  const y0 = addTitleBlock(sl, s.title || '目次', s.kicker);
  const items = s.items || [];
  const objs = [];
  items.forEach((it, i) => {
    objs.push({ text: String(i + 1).padStart(2, '0') + '   ', options: { fontFace: T.fontHead, fontSize: 18, bold: true, color: T.accent, breakLine: false } });
    objs.push({ text: it, options: { fontFace: T.font, fontSize: 18, color: T.ink, breakLine: true, paraSpaceAfter: 14 } });
  });
  sl.addText(objs, { x: MX + 0.1, y: y0 + 0.1, w: CONTENT_W - 0.2, h: PH - y0 - 0.9, valign: 'top', margin: 0 });
}

function slideSection(s) {
  const sl = pptx.addSlide();
  sl.background = { color: T.navy };
  sl.addShape(pptx.ShapeType.rect, { x: 0, y: 0, w: PW, h: 0.14, fill: { color: T.accent }, line: { type: 'none' } });
  if (s.number != null) sl.addText(String(s.number).padStart(2, '0'), { x: MX, y: 2.2, w: 3, h: 1.6, fontFace: T.fontHead, fontSize: 96, bold: true, color: '3E6EA0', margin: 0, valign: 'middle' });
  sl.addShape(pptx.ShapeType.line, { x: MX + 0.05, y: 3.95, w: 4.2, h: 0, line: { color: '5C86B0', width: 1.5 } });
  sl.addText(s.title || '', { x: MX, y: 4.1, w: PW - MX * 2, h: 1.4, fontFace: T.fontHead, fontSize: 34, bold: true, color: 'FFFFFF', margin: 0, valign: 'top' });
  pageNo += 1;
  if (plan.footer) sl.addText(plan.footer, { x: MX, y: PH - 0.42, w: 8, h: 0.3, fontFace: T.font, fontSize: 9, color: 'A9C0D8', valign: 'middle', margin: 0 });
  sl.addText(String(pageNo), { x: PW - MX - 1, y: PH - 0.42, w: 1, h: 0.3, fontFace: T.font, fontSize: 9, color: 'A9C0D8', align: 'right', valign: 'middle', margin: 0 });
}

function slideContent(s) {
  const sl = pptx.addSlide();
  chrome(sl);
  const y0 = addTitleBlock(sl, s.title, s.kicker);
  const figs = normFigures(s);
  const bullets = s.bullets || [];
  const bottom = PH - 0.6;
  const areaH = bottom - y0;
  let layout = s.layout && s.layout !== 'auto' ? s.layout
    : figs.length >= 2 ? 'figures'
    : figs.length === 1 && bullets.length ? 'text-figure'
    : figs.length === 1 ? 'figure'
    : bullets.length > 7 ? 'two-col' : 'text';

  if (layout === 'text') {
    addBullets(sl, bullets, MX, y0, CONTENT_W, areaH);
  } else if (layout === 'two-col') {
    const mid = Math.ceil(bullets.length / 2);
    const gap = 0.5, colW = (CONTENT_W - gap) / 2;
    addBullets(sl, bullets.slice(0, mid), MX, y0, colW, areaH);
    addBullets(sl, bullets.slice(mid), MX + colW + gap, y0, colW, areaH);
  } else if (layout === 'figure') {
    addFigure(sl, figs[0], MX, y0, CONTENT_W, areaH);
  } else if (layout === 'text-figure') {
    const gap = 0.45;
    const textW = CONTENT_W * 0.46, figW = CONTENT_W - textW - gap;
    addBullets(sl, bullets, MX, y0, textW, areaH);
    addFigure(sl, figs[0], MX + textW + gap, y0, figW, areaH);
  } else if (layout === 'figures') {
    const gap = 0.4;
    const topH = bullets.length ? Math.min(areaH * 0.32, 1.6) : 0;
    if (bullets.length) addBullets(sl, bullets, MX, y0, CONTENT_W, topH);
    const fy = y0 + topH + (topH ? 0.15 : 0);
    const fh = bottom - fy;
    const n = Math.min(figs.length, 3);
    const fw = (CONTENT_W - gap * (n - 1)) / n;
    for (let i = 0; i < n; i++) addFigure(sl, figs[i], MX + i * (fw + gap), fy, fw, fh);
  }
}

function slideSummary(s) {
  const sl = pptx.addSlide();
  chrome(sl);
  const y0 = addTitleBlock(sl, s.title || 'まとめ', s.kicker);
  const bullets = (s.bullets || []).map(b => (typeof b === 'string' ? { text: b } : b));
  const objs = bullets.map((b) => ({
    text: b.text,
    options: { fontFace: T.font, fontSize: 18, bold: !!b.bold, color: T.ink, bullet: { code: '2022', indent: 18 }, paraSpaceAfter: 12, breakLine: true, lineSpacingMultiple: 1.1 },
  }));
  sl.addText(objs, { x: MX + 0.1, y: y0 + 0.1, w: CONTENT_W - 0.2, h: PH - y0 - 0.9, valign: 'top', margin: 0 });
}

// ---- drive -------------------------------------------------------------------
const builders = { title: slideTitle, agenda: slideAgenda, toc: slideAgenda, section: slideSection, content: slideContent, summary: slideSummary, closing: slideSummary };
for (const s of plan.slides || []) {
  const fn = builders[s.type] || slideContent;
  try { fn(s); } catch (e) { console.error('slide error (' + s.type + '): ' + e.message); throw e; }
}

pptx.writeFile({ fileName: outPath }).then(() => {
  console.log('OK ' + outPath + '  slides=' + (plan.slides || []).length);
}).catch(e => { console.error('write failed: ' + e.message); process.exit(1); });
