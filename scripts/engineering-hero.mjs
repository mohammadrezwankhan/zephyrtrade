import fs from 'node:fs';
import path from 'node:path';
import { createHash } from 'node:crypto';

const RELEASE_DIRECTORY = 'assets/engineering-hero/v1';
const REQUIRED_FILES = [
  'index.html',
  'hero-1080p60.mp4',
  'poster.png',
  'csp.json',
  'integration/vanilla/host.css',
  'integration/vanilla/khan-grid-hero.js',
  'integration/vanilla/embed.css',
  'src/config.js',
];

function checkedSourceFile(sourceRoot, relativePath) {
  if (typeof relativePath !== 'string' || !relativePath || relativePath.includes('\\') ||
      relativePath.startsWith('/') || /^[a-z]:/i.test(relativePath) ||
      path.posix.normalize(relativePath) !== relativePath ||
      relativePath.split('/').some(part => !part || part === '.' || part === '..')) {
    throw Error(`Unsafe engineering hero manifest path: ${relativePath}`);
  }
  let current = sourceRoot;
  for (const part of relativePath.split('/')) {
    current = path.join(current, part);
    const stat = fs.lstatSync(current);
    if (stat.isSymbolicLink()) throw Error(`Engineering hero symlink rejected: ${relativePath}`);
  }
  if (!fs.statSync(current).isFile()) throw Error(`Engineering hero file is missing: ${relativePath}`);
  return current;
}

function assertNoSymlinkComponents(target) {
  const absolute = path.resolve(target);
  const root = path.parse(absolute).root;
  let current = root;
  for (const part of absolute.slice(root.length).split(path.sep).filter(Boolean)) {
    current = path.join(current, part);
    if (fs.existsSync(current) && fs.lstatSync(current).isSymbolicLink()) throw Error(`Engineering hero symlink rejected: ${current}`);
  }
}

function readVerifiedRelease(sourceRoot) {
  const manifestPath = checkedSourceFile(sourceRoot, 'release-media.json');
  const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
  if (manifest.status !== 'verified') throw Error('Engineering hero release-media.json must have status "verified"');
  if (!Array.isArray(manifest.files) || manifest.files.length === 0) throw Error('Engineering hero release-media.json must list verified files');

  const files = new Map();
  for (const entry of manifest.files) {
    if (!entry || typeof entry !== 'object' || Array.isArray(entry) ||
        !Number.isSafeInteger(entry.bytes) || entry.bytes < 1 ||
        typeof entry.sha256 !== 'string' || !/^[a-f0-9]{64}$/i.test(entry.sha256)) {
      throw Error('Invalid engineering hero release file record');
    }
    if (entry.path === 'release-media.json') throw Error('release-media.json must not list itself');
    if (files.has(entry.path)) throw Error(`Duplicate engineering hero manifest path: ${entry.path}`);
    const file = checkedSourceFile(sourceRoot, entry.path);
    const data = fs.readFileSync(file);
    if (data.length !== entry.bytes || createHash('sha256').update(data).digest('hex') !== entry.sha256.toLowerCase()) {
      throw Error(`Engineering hero release file failed verification: ${entry.path}`);
    }
    files.set(entry.path, file);
  }

  for (const required of REQUIRED_FILES) {
    if (!files.has(required)) throw Error(`Engineering hero release is missing verified media: ${required}`);
  }
  const csp = JSON.parse(fs.readFileSync(files.get('csp.json'), 'utf8'));
  const policy = csp.suggestedContentSecurityPolicy;
  if (typeof policy !== 'string' || !policy.trim() || /[\r\n]/.test(policy) ||
      policy.length > 1900 || !/\bframe-ancestors\b/i.test(policy)) {
    throw Error('Engineering hero csp.json needs a single-line suggestedContentSecurityPolicy with frame-ancestors');
  }
  return { manifestPath, files, policy: policy.trim() };
}

function copyVerifiedFiles({ sourceRoot, siteOutput, manifestPath, files }) {
  const destinationRoot = path.resolve(siteOutput, RELEASE_DIRECTORY);
  const rel = path.relative(path.resolve(siteOutput), destinationRoot);
  if (rel !== path.join('assets', 'engineering-hero', 'v1')) throw Error('Invalid engineering hero output path');
  assertNoSymlinkComponents(destinationRoot);
  if (fs.existsSync(destinationRoot) && fs.lstatSync(destinationRoot).isSymbolicLink()) {
    throw Error('Engineering hero output symlink rejected');
  }
  fs.mkdirSync(destinationRoot, { recursive: true });
  for (const [relativePath, source] of files) {
    const destination = path.resolve(destinationRoot, ...relativePath.split('/'));
    if (!destination.startsWith(destinationRoot + path.sep)) throw Error(`Engineering hero output escaped: ${relativePath}`);
    fs.mkdirSync(path.dirname(destination), { recursive: true });
    if (fs.existsSync(destination) && fs.lstatSync(destination).isSymbolicLink()) throw Error(`Engineering hero output symlink rejected: ${relativePath}`);
    fs.copyFileSync(source, destination);
  }
  fs.copyFileSync(manifestPath, path.join(destinationRoot, 'release-media.json'));
}

export function engineeringHeroSection(siteId) {
  if (!['mkgrid', 'mktrade'].includes(siteId)) throw Error('engineeringHeroSite must be "mkgrid" or "mktrade"');
  const base = '/assets/engineering-hero/v1';
  return `<section class="engineering-hero" aria-labelledby="engineering-hero-heading"><div><p class="eyebrow">ENGINEERING / FIELD NOTES</p><h2 id="engineering-hero-heading">See the system behind the study</h2><p class="lead">A short visual introduction to the engineering context sits alongside this overview. The hosted preview remains synthetic and the film does not validate a design or model.</p></div><khan-grid-hero site="${siteId}" mode="video" video-src="${base}/hero-1080p60.mp4" poster-src="${base}/poster.png" hide-cta><img slot="poster" src="${base}/poster.png" alt="Poster for the engineering film introducing system context" width="1920" height="1080" loading="lazy" decoding="async"></khan-grid-hero></section>`;
}

export function insertEngineeringHeroSection(overviewHtml, section) {
  if (!section) return overviewHtml;
  const opening = '<section class="app-hero">';
  if (overviewHtml.split(opening).length - 1 !== 1) throw Error('Expected one overview .app-hero section');
  const start = overviewHtml.indexOf(opening);
  const end = overviewHtml.indexOf('</section>', start);
  if (end < 0) throw Error('Overview .app-hero section is not closed');
  const after = end + '</section>'.length;
  return overviewHtml.slice(0, after) + section + overviewHtml.slice(after);
}

export function prepareEngineeringHero({ enabled, sourceRoot, siteOutput, siteId }) {
  if (enabled !== true) return { enabled: false, section: '', headMarkup: '', contentSecurityPolicy: '' };
  assertNoSymlinkComponents(sourceRoot);
  if (!fs.statSync(sourceRoot).isDirectory()) {
    throw Error('Engineering hero release directory is missing or unsafe');
  }
  const section = engineeringHeroSection(siteId);
  const verified = readVerifiedRelease(sourceRoot);
  copyVerifiedFiles({ sourceRoot, siteOutput, ...verified });
  return {
    enabled: true,
    section,
    headMarkup: '<link rel="stylesheet" href="/assets/engineering-hero/v1/integration/vanilla/host.css"><script type="module" src="/assets/engineering-hero/v1/integration/vanilla/khan-grid-hero.js"></script>',
    contentSecurityPolicy: verified.policy,
  };
}

export function addEngineeringHeroFramePolicy(headers, contentSecurityPolicy) {
  if (!contentSecurityPolicy) return headers;
  return headers.trimEnd()+'\n'+['/assets/engineering-hero/v1/index.html','/assets/engineering-hero/v1/'].map(url=>`${url}\n  ! Content-Security-Policy\n  Content-Security-Policy: ${contentSecurityPolicy}\n  ! X-Frame-Options\n`).join('\n');
}
