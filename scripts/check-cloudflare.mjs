// Check the distributable, not just the build source.
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import assert from 'node:assert/strict';
import {runtimeSecurity, runtimeHeaderBlock} from './runtime-security.mjs';
import {hasAnchorUnder} from './html-document.mjs';
/** @param {unknown} value @returns {value is Record<string,unknown>} */
function isRecord(value){return value!==null&&typeof value==='object'&&!Array.isArray(value);}
/** @param {unknown} value @param {string} label @returns {Record<string,unknown>} */
function record(value,label){
 assert.ok(isRecord(value),label+' must be an object');
 return value;
}
/** @param {unknown} value @param {string} label @returns {string[]} */
function strings(value,label){
 assert.ok(Array.isArray(value)&&value.every(item=>typeof item==='string'),label+' must contain text');
 return value;
}
/** @param {RegExpMatchArray|null} match @param {string} label */
function capture(match,label){
 const text=match?.[1];
 assert.ok(typeof text==='string','Missing '+label);
 return text;
}
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const config=record(JSON.parse(fs.readFileSync(path.join(root,'cloudflare.json'),'utf8')),'App configuration');
assert.ok(typeof config.canonical==='string'&&typeof config.title==='string'&&typeof config.slug==='string');
const outputRoot=process.env.CLOUDFLARE_OUTPUT_ROOT===undefined?path.join(root,'.cloudflare'):path.resolve(root,process.env.CLOUDFLARE_OUTPUT_ROOT);
const output=path.join(outputRoot,'app');
/** @param {string} file */
const read=file=>fs.readFileSync(path.join(output,file),'utf8');
const html=read('index.html'),runtime=read('run/index.html'),facts=record(JSON.parse(read('app.json')),'App facts');
assert.ok(read('_headers').includes(runtimeHeaderBlock(runtime)));
assert.deepEqual(JSON.parse(fs.readFileSync(path.join(outputRoot,'app-security-headers.json'),'utf8')),runtimeSecurity(runtime));
assert.equal(facts.url,config.canonical);
assert.equal(new URL(config.canonical).origin,'https://mklab.co.technology');
assert.ok(html.includes('MKLab Browser Apps'));
assert.equal(hasAnchorUnder(html,'https://khanlab.co.technology/apps/',config.canonical),false);
assert.equal(facts.access,'public; no sign-in');
assert.equal(facts.runtimeSha256,createHash('sha256').update(runtime).digest('hex'));
assert.match(html,/<h1>(?:[^<]|<wbr>)+<\/h1>/);assert.match(html,/name="robots" content="index,follow/);
assert.match(runtime,/name="robots" content="noindex,follow"/);
assert.equal((html.match(/rel="canonical"/g)||[]).length,1);
assert.match(html,/href="\.\/run\/"/);
const schemas=[...html.matchAll(/<script type="application\/ld\+json">(.*?)<\/script>/gs)].map(m=>record(JSON.parse(capture(m,'structured data')),'Structured data'));
assert.equal(schemas.length,1);
const graph=schemas[0]?.['@graph'];
assert.ok(Array.isArray(graph),'Structured data graph must be an array');
const application=record(graph[0],'Structured application');
assert.equal(application.url,config.canonical);
assert.equal(application.name,config.title);
assert.equal(strings(facts.features,'Features').length,3);assert.equal(strings(facts.steps,'Steps').length,3);
assert.ok(strings(facts.limitations,'Limitations').length>=2);assert.ok(read('llms.txt').includes(config.canonical));
assert.ok(fs.statSync(path.join(output,'social-preview.png')).size>100);
assert.ok(fs.statSync(path.join(output,'preview.png')).size>100);
/** @type {string[]} */
const paths=[];
/** @param {string} dir */
function scan(dir){for(const entry of fs.readdirSync(dir,{withFileTypes:true})){assert.equal(entry.isSymbolicLink(),false);const file=path.join(dir,entry.name);if(entry.isDirectory())scan(file);else{const relative=path.relative(output,file).split(path.sep).join('/');assert.ok(!/(^|\/)(\.git|\.env|node_modules|server\.mjs|package(?:-lock)?\.json)(\/|$)/.test(relative),'Private/server file in export: '+relative);assert.ok(!/\.(sqlite3?|db|map)$/.test(relative),'Runtime-only export contains '+relative);assert.ok(fs.statSync(file).size<=25*1024*1024);paths.push(relative);}}}scan(output);
assert.ok(paths.length<1000);
console.log(JSON.stringify({app:config.slug,status:'passed',checks:['static HTML','canonical','structured data','runtime hash','public facts','runtime noindex','assets','no source/config/database files'],files:paths.length}));
