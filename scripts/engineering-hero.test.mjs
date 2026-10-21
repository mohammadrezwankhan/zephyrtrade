import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import test from 'node:test';
import { addEngineeringHeroFramePolicy, insertEngineeringHeroSection, prepareEngineeringHero } from './engineering-hero.mjs';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const testRoot = path.join(root, '.cloudflare', 'engineering-hero-tests');
const releaseFiles = {
  'index.html': Buffer.from('<!doctype html><title>Standalone frame</title>'),
  'hero-1080p60.mp4': Buffer.from('verified-video-fixture'),
  'poster.png': Buffer.from('verified-poster-fixture'),
  'csp.json': Buffer.from(JSON.stringify({
    importMapHash: 'sha256-fixture',
    suggestedContentSecurityPolicy: "default-src 'self'; frame-ancestors 'self'",
  })),
  'integration/vanilla/host.css': Buffer.from('khan-grid-hero{display:block;aspect-ratio:16/9}'),
  'integration/vanilla/khan-grid-hero.js': Buffer.from('customElements.define("khan-grid-hero", class extends HTMLElement {});'),
  'integration/vanilla/embed.css': Buffer.from('.frame{aspect-ratio:16/9}'),
  'src/config.js': Buffer.from('export const getSite=()=>({});'),
};

function fixture(name, { status = 'verified', omit = [], omitPayload = [], omitManifest = false, badHash = false } = {}) {
  const sourceRoot = path.join(testRoot, name, 'source');
  fs.mkdirSync(sourceRoot, { recursive: true });
  const files = [];
  for (const [relativePath, data] of Object.entries(releaseFiles)) {
    if (omit.includes(relativePath)) continue;
    const target = path.join(sourceRoot, ...relativePath.split('/'));
    if (!omitPayload.includes(relativePath)) {
      fs.mkdirSync(path.dirname(target), { recursive: true });
      fs.writeFileSync(target, data);
    }
    files.push({
      path: relativePath,
      bytes: data.length,
      sha256: createHash('sha256').update(data).digest('hex'),
    });
  }
  fs.writeFileSync(path.join(sourceRoot, 'unlisted.txt'), 'must not be copied');
  if (badHash) files[0].sha256 = '0'.repeat(64);
  if (!omitManifest) {
    fs.writeFileSync(path.join(sourceRoot, 'release-media.json'), JSON.stringify({
      status, frames: 900, width: 1920, height: 1080, fps: 60, duration: 15,
      site: 'mrkhan', files,
    }));
  }
  return sourceRoot;
}

function prepare(sourceRoot, name, siteId = 'mkgrid') {
  return prepareEngineeringHero({
    enabled: true,
    sourceRoot,
    siteOutput: path.join(testRoot, name, 'output'),
    siteId,
  });
}

test('flag off leaves the overview and output untouched without a release folder', () => {
  const sourceRoot = path.join(testRoot, 'not-present', 'source');
  const siteOutput = path.join(testRoot, 'disabled-output');
  const prepared = prepareEngineeringHero({ enabled: false, sourceRoot, siteOutput, siteId: 'mkgrid' });
  assert.deepEqual(prepared, { enabled: false, section: '', headMarkup: '', contentSecurityPolicy: '' });
  assert.equal(fs.existsSync(siteOutput), false);
  const overview = '<section class="app-hero"><h1>Keep this title</h1></section><section class="content-grid">';
  assert.equal(insertEngineeringHeroSection(overview, prepared.section), overview);
});

test('enabled output preserves the overview CTA and screenshot, inserts the hero section, and copies only verified assets', () => {
  const sourceRoot = fixture('enabled');
  const prepared = prepare(sourceRoot, 'enabled', 'mktrade');
  const overview = '<section class="app-hero"><h1>Keep this title</h1><a href="/run/">Open preview</a><img src="/preview.png" alt="Actual screenshot"></section><section class="content-grid">';
  const integrated = insertEngineeringHeroSection(overview, prepared.section);
  const appHeroEnd = integrated.indexOf('</section>') + '</section>'.length;
  assert.equal(integrated.slice(appHeroEnd).startsWith('<section class="engineering-hero"'), true);
  assert.ok(integrated.includes('<h1>Keep this title</h1>'));
  assert.ok(integrated.includes('href="/run/">Open preview</a>'));
  assert.ok(integrated.includes('src="/preview.png" alt="Actual screenshot"'));
  assert.ok(integrated.includes('A short visual introduction to the engineering context sits alongside'));
  assert.ok(integrated.includes('synthetic'));
  assert.ok(integrated.includes('<khan-grid-hero site="mktrade" mode="video"'));
  assert.ok(integrated.includes('video-src="/assets/engineering-hero/v1/hero-1080p60.mp4"'));
  assert.ok(integrated.includes('poster-src="/assets/engineering-hero/v1/poster.png" hide-cta'));
  assert.ok(!/\b(?:autoplay|loop)\b/.test(integrated));
  assert.ok(prepared.headMarkup.includes('href="/assets/engineering-hero/v1/integration/vanilla/host.css"'));
  assert.ok(prepared.headMarkup.includes('src="/assets/engineering-hero/v1/integration/vanilla/khan-grid-hero.js"'));
  assert.ok(prepared.headMarkup.includes('type="module"'));

  const outputRoot = path.join(testRoot, 'enabled', 'output', 'assets', 'engineering-hero', 'v1');
  for (const relativePath of [...Object.keys(releaseFiles), 'release-media.json']) {
    assert.equal(fs.existsSync(path.join(outputRoot, ...relativePath.split('/'))), true, relativePath);
  }
  assert.equal(fs.existsSync(path.join(outputRoot, 'unlisted.txt')), false);
  const baseHeaders = '/*\n  X-Frame-Options: DENY\n';
  const headers = addEngineeringHeroFramePolicy(baseHeaders, prepared.contentSecurityPolicy);
  assert.ok(headers.includes('/*\n  X-Frame-Options: DENY'));
  for (const url of ['/assets/engineering-hero/v1/index.html','/assets/engineering-hero/v1/']) assert.ok(headers.includes(url+'\n  ! Content-Security-Policy\n  Content-Security-Policy: default-src \'self\'; frame-ancestors \'self\'\n  ! X-Frame-Options'));
  assert.equal(headers.split('! X-Frame-Options').length - 1, 2);
});

test('missing, unverified, incomplete, or tampered media releases fail before copying', () => {
  const invalid = [
    ['missing-config', fixture('missing-config', { omit: ['src/config.js'] }), /missing verified media: src\/config\.js/],
    ['missing-css', fixture('missing-css', { omit: ['integration/vanilla/embed.css'] }), /missing verified media: integration\/vanilla\/embed\.css/],
    ['missing-manifest', fixture('missing-manifest', { omitManifest: true }), /release-media\.json/],
    ['unverified', fixture('unverified', { status: 'staged' }), /status "verified"/],
    ['missing-video', fixture('missing-video', { omit: ['hero-1080p60.mp4'] }), /missing verified media: hero-1080p60\.mp4/],
    ['missing-poster', fixture('missing-poster', { omit: ['poster.png'] }), /missing verified media: poster\.png/],
    ['missing-listed-video', fixture('missing-listed-video', { omitPayload: ['hero-1080p60.mp4'] }), /hero-1080p60\.mp4/],
    ['missing-listed-poster', fixture('missing-listed-poster', { omitPayload: ['poster.png'] }), /poster\.png/],
    ['bad-hash', fixture('bad-hash', { badHash: true }), /failed verification/],
  ];
  for (const [name, sourceRoot, pattern] of invalid) {
    assert.throws(() => prepare(sourceRoot, name), pattern, name);
    assert.equal(fs.existsSync(path.join(testRoot, name, 'output', 'assets', 'engineering-hero', 'v1')), false, `${name} should not partially copy`);
  }
});
