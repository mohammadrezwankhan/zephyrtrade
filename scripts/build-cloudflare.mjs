// Reproducible browser-only export. No repository tree, credentials, or server data are published.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { createServer } from 'node:http';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const config = JSON.parse(fs.readFileSync(path.join(root, 'cloudflare.json'), 'utf8'));
const out = path.join(root, '.cloudflare', 'app');
const escape = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const json = value => JSON.stringify(value).replace(/</g, '\\u003c');
const sha = buffer => createHash('sha256').update(buffer).digest('hex');
const canonical = new URL(config.canonical).href;
const siteOrigin = new URL(canonical).origin;
if (!canonical.startsWith('https://') || !canonical.endsWith('/')) throw Error('Canonical must be an HTTPS directory URL');
if (!/^[a-z0-9-]+$/.test(config.slug)) throw Error('Invalid app slug');
function local(relative) {
  const file = path.resolve(root, relative);
  if (!file.startsWith(root + path.sep)) throw Error('Input outside repository');
  let current = file;
  while (current !== root) { if (fs.lstatSync(current).isSymbolicLink()) throw Error('Symlink input rejected'); current = path.dirname(current); }
  return file;
}
if (config.prepareScript) {
  if (!/^scripts\/[a-z0-9-]+\.mjs$/.test(config.prepareScript)) throw Error('Invalid preparation script');
  execFileSync(process.execPath, [local(config.prepareScript)], {cwd:root, stdio:'inherit', windowsHide:true});
}
// Only remove this builder's generated directory, after checking its absolute location.
if (path.relative(root, out) !== path.join('.cloudflare','app')) throw Error('Invalid output');
if (fs.existsSync(path.join(root,'.cloudflare')) && fs.lstatSync(path.join(root,'.cloudflare')).isSymbolicLink()) throw Error('Symlink output rejected');
if (fs.existsSync(out) && fs.lstatSync(out).isSymbolicLink()) throw Error('Symlink output rejected');
fs.rmSync(out, {recursive:true, force:true});
fs.mkdirSync(path.join(out, 'run'), {recursive:true});
const runtimeRoot = config.runtimeDirectory ? local(config.runtimeDirectory) : null;
if (runtimeRoot) {
  const copy = (dir, target) => {
    for (const entry of fs.readdirSync(dir,{withFileTypes:true})) {
      if (entry.isSymbolicLink() || entry.name.startsWith('.') || /(?:\.map|\.sqlite3?|\.env)$/i.test(entry.name)) throw Error('Unsafe runtime export: '+entry.name);
      const source=path.join(dir,entry.name), destination=path.join(target,entry.name);
      if (entry.isDirectory()) { fs.mkdirSync(destination,{recursive:true}); copy(source,destination); }
      else { if (fs.statSync(source).size>25*1024*1024) throw Error('Pages asset exceeds 25 MiB'); fs.copyFileSync(source,destination); }
    }
  };
  copy(runtimeRoot,path.join(out,'run'));
} else {
  fs.copyFileSync(local(config.demoArtifact), path.join(out,'run','index.html'));
}
let runtime = fs.readFileSync(path.join(out,'run','index.html'),'utf8');
if (!/<head[\s>]/i.test(runtime)) throw Error('Runtime needs an HTML head');
for (const patch of config.runtimePatches ?? []) {
  const count=runtime.split(patch.from).length-1;
  if(count!==patch.occurrences)throw Error('Runtime patch anchor changed: '+patch.reason);
  runtime=runtime.split(patch.from).join(patch.to);
}
// Index the factual introduction; do not surface fictional records as real search results.
runtime = runtime.replace(/<meta\b[^>]*\bname\s*=\s*["']robots["'][^>]*>/gi, '')
  .replace(/<link\b[^>]*\brel\s*=\s*["']canonical["'][^>]*>/gi, '')
  .replace(/<head\b[^>]*>/i, match => match + `\n<meta name="robots" content="noindex,follow"><link rel="canonical" href="${escape(canonical)}">\n`);
fs.writeFileSync(path.join(out,'run','index.html'),runtime);
fs.copyFileSync(local('scripts/cloudflare-site.css'),path.join(out,'site.css'));
fs.copyFileSync(local('docs/repository/social-preview.png'),path.join(out,'social-preview.png'));
fs.copyFileSync(local(config.previewArtifact||'docs/repository/demo-desktop.png'),path.join(out,'preview.png'));
fs.writeFileSync(path.join(out,'favicon.svg'),'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="14" fill="#132923"/><path d="M14 49V15h8l10 17 10-17h8v34h-8V30L32 47 22 30v19z" fill="#c9ee8b"/></svg>');
let revision = 'unversioned';
try { revision = execFileSync('git',['rev-parse','HEAD'],{cwd:root,encoding:'utf8',windowsHide:true}).trim(); } catch { /* Exported source still builds without Git. */ }
const copyright = (config.noticeFiles ?? []).map(name => `===== ${name} =====\n\n${fs.readFileSync(local(name),'utf8')}\n`).join('\n');
fs.writeFileSync(path.join(out,'NOTICES.txt'),`Browser release: ${config.title}\n\nBundled third-party notices remain applicable. Public browser access does not grant a new license over private source or third-party material.\n\n${copyright}`);
if(!fs.existsSync(path.join(out,'run','THIRD-PARTY-NOTICES.txt')))fs.copyFileSync(path.join(out,'NOTICES.txt'),path.join(out,'run','THIRD-PARTY-NOTICES.txt'));
const list = items => items.map(text => `<li>${escape(text)}</li>`).join('');
const author = {'@type':'Person',name:'Mohammad Rezwan Khan',url:siteOrigin+'/about/'};
const structured = {'@context':'https://schema.org','@graph':[
  {'@type':'SoftwareApplication','@id':canonical+'#app',name:config.title,description:config.shortDescription,url:canonical,applicationCategory:'EducationalApplication',operatingSystem:'Web browser',isAccessibleForFree:true,author,featureList:config.features,softwareHelp:{'@type':'WebPage',url:canonical+'#how-to-use'}},
  {'@type':'WebPage','@id':canonical+'#page',url:canonical,name:config.title+' — Browser Demo',description:config.shortDescription,inLanguage:'en',dateModified:config.updated,mainEntity:{'@id':canonical+'#app'},author},
  {'@type':'BreadcrumbList',itemListElement:[{'@type':'ListItem',position:1,name:'MKLab browser apps',item:siteOrigin+'/'},{'@type':'ListItem',position:2,name:config.title,item:canonical}]}
]};
const publicSource = config.publicSource ? `<a href="${escape(config.publicSource)}" rel="noopener">Source &amp; methodology ↗</a>` : '';
const head = `<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="theme-color" content="#122824"><title>${escape(config.title)} — Browser Demo | MKLab</title><meta name="description" content="${escape(config.shortDescription)}"><meta name="author" content="Mohammad Rezwan Khan"><meta name="robots" content="index,follow,max-image-preview:large"><link rel="canonical" href="${escape(canonical)}"><link rel="icon" href="./favicon.svg"><link rel="stylesheet" href="./site.css"><meta property="og:type" content="website"><meta property="og:site_name" content="MKLab Browser Apps"><meta property="og:title" content="${escape(config.title)}"><meta property="og:description" content="${escape(config.shortDescription)}"><meta property="og:url" content="${escape(canonical)}"><meta property="og:image" content="${escape(canonical)}social-preview.png"><meta property="og:image:width" content="1280"><meta property="og:image:height" content="640"><meta property="og:image:alt" content="${escape(config.title)} project preview"><meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="${escape(config.title)}"><meta name="twitter:description" content="${escape(config.shortDescription)}"><meta name="twitter:image" content="${escape(canonical)}social-preview.png"><script type="application/ld+json">${json(structured)}</script>`;
const html = `<!doctype html><html lang="en"><head>${head}</head><body><a class="skip" href="#main">Skip to content</a><header class="masthead"><a class="wordmark" href="${siteOrigin}/">M<span>↗</span> MKLab</a><nav aria-label="Main"><a href="${siteOrigin}/">All apps</a><a href="https://khanlab.co.technology/">Datacenter lab</a><a href="${siteOrigin}/about/">About</a></nav></header><main id="main"><section class="app-hero"><div><p class="eyebrow">${escape(config.category)} / BROWSER DEMO</p><h1>${escape(config.title).replace(/([a-z])([A-Z])/g,'$1<wbr>$2')}</h1><p class="lead">${escape(config.summary)}</p><div class="actions"><a class="button primary" href="./run/">Open browser app <span aria-hidden="true">↗</span></a>${publicSource}</div><p class="micro">Free to explore · No sign-in · Demonstration data</p></div><figure class="app-preview"><img src="./preview.png" alt="Actual ${escape(config.title)} demo interface" width="1440" height="1000" fetchpriority="high"><figcaption>Actual demo interface. Sample records are fictional.</figcaption></figure></section><section class="content-grid"><div><p class="eyebrow">EXPLORE</p><h2>What you can try</h2><ul class="feature-list">${list(config.features)}</ul></div><div id="how-to-use"><p class="eyebrow">START HERE</p><h2>Try it in three steps</h2><ol class="steps">${list(config.steps)}</ol></div></section><section class="boundary"><div><p class="eyebrow">CONTEXT &amp; LIMITS</p><h2>Know what the demo shows</h2></div><div><ul>${list(config.limitations)}</ul><p>Use fictional information when trying inputs. The browser edition has no live service, account, payment, dispatch, or external AI integration. Any local saves belong to this browser and device.</p></div></section><section class="faq"><p class="eyebrow">COMMON QUESTIONS</p><h2>Before you explore</h2>${config.faqs.map(item=>`<details><summary>${escape(item.question)}</summary><p>${escape(item.answer)}</p></details>`).join('')}</section><section class="release"><h2>Release information</h2><p>Maintained by <a href="${siteOrigin}/about/">Mohammad Rezwan Khan</a>. Browser release updated <time datetime="${escape(config.updated)}">${escape(config.updated)}</time>. This page describes the shipped browser demo; it is not a claim of professional or production validation.</p><p><a href="./app.json">Machine-readable app facts</a> · <a href="./llms.txt">Plain-text overview</a> · <a href="./NOTICES.txt">Dependency &amp; content notices</a>${publicSource ? ' · '+publicSource : ''}</p><p class="micro">Source revision ${escape(revision.slice(0,12))} · Runtime SHA-256 ${sha(Buffer.from(runtime)).slice(0,16)}</p></section></main><footer><a class="wordmark" href="${siteOrigin}/">MKLab</a><p>Practical experiments, with their assumptions in view.</p><a href="${siteOrigin}/">Explore all browser apps →</a></footer></body></html>`;
fs.writeFileSync(path.join(out,'index.html'),html);
const facts = {title:config.title,url:canonical,applicationUrl:canonical+'run/',description:config.shortDescription,summary:config.summary,features:config.features,steps:config.steps,limitations:config.limitations,faqs:config.faqs,updated:config.updated,author:author.name,sourceRevision:revision,publicSource:config.publicSource||null,runtimeSha256:sha(Buffer.from(runtime)),dataStatus:'synthetic demonstration',access:'public; no sign-in'};
fs.writeFileSync(path.join(out,'app.json'),JSON.stringify(facts,null,2)+'\n');
fs.writeFileSync(path.join(out,'llms.txt'),`# ${config.title}\n\n${config.summary}\n\n- App overview: ${canonical}\n- Browser application: ${canonical}run/\n- Maintainer: Mohammad Rezwan Khan\n- Updated: ${config.updated}\n\n## Features\n${config.features.map(s=>'- '+s).join('\n')}\n\n## Limits\n${config.limitations.map(s=>'- '+s).join('\n')}\n\nThese facts describe a demonstration, not an operational service. This optional text file supplements the visible HTML; it is not a ranking or citation guarantee.\n`);
// A 404 avoids a static host turning missing assets into successful app responses.
fs.writeFileSync(path.join(out,'404.html'),'<!doctype html><html lang="en"><meta charset="utf-8"><meta name="robots" content="noindex"><title>Page not found</title><h1>Page not found</h1><p><a href="'+escape(canonical)+'">Return to the app overview</a></p></html>');
console.log(JSON.stringify({app:config.slug,output:out,canonical,runtimeSha256:facts.runtimeSha256}));
if (process.argv.includes('--serve')) {
  const port=Number(process.env.PORT||4179);
  if(!Number.isInteger(port)||port<1||port>65535)throw Error('Invalid PORT');
  const types={'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8','.mjs':'text/javascript; charset=utf-8','.css':'text/css; charset=utf-8','.json':'application/json','.webmanifest':'application/manifest+json','.svg':'image/svg+xml','.png':'image/png','.webp':'image/webp','.txt':'text/plain; charset=utf-8','.mp3':'audio/mpeg'};
  const server=createServer((req,res)=>{
    if(!['GET','HEAD'].includes(req.method)){res.writeHead(405,{Allow:'GET, HEAD'});res.end();return;}
    try{
      const pathname=decodeURIComponent(new URL(req.url,'http://127.0.0.1').pathname);
      if(pathname.includes('\\')||pathname.includes('\0'))throw Error('Invalid path');
      let file=path.resolve(out,'.'+pathname);
      if(file!==out&&!file.startsWith(out+path.sep))throw Error('Invalid path');
      if(fs.statSync(file).isDirectory())file=path.join(file,'index.html');
      const real=fs.realpathSync(file);
      if(!real.startsWith(out+path.sep))throw Error('Invalid path');
      const data=fs.readFileSync(real);
      res.writeHead(200,{'Content-Type':types[path.extname(real)]||'application/octet-stream','Content-Length':data.length,'Cache-Control':'no-store','X-Content-Type-Options':'nosniff','Referrer-Policy':'no-referrer'});
      res.end(req.method==='HEAD'?undefined:data);
    }catch{res.writeHead(404,{'Content-Type':'text/plain'});res.end(req.method==='HEAD'?undefined:'Not found');}
  });
  server.on('error',error=>{console.error(error.message);process.exitCode=1;});
  server.listen(port,'127.0.0.1',()=>console.log(`Open http://127.0.0.1:${port}/ — browser-only Cloudflare build`));
}
