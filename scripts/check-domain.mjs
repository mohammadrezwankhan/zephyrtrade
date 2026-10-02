import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..'),out=path.join(root,'.cloudflare/site');
const site=JSON.parse(fs.readFileSync(path.join(root,'cloudflare-domain.json'),'utf8'));
const origin=new URL(site.canonical).origin,read=p=>fs.readFileSync(path.join(out,p),'utf8');
const maintainerUrl='https://mrkhan.co.technology/',maintainerId=maintainerUrl+'#person';
function findAll(value,predicate,found=[]){if(Array.isArray(value)){for(const item of value)findAll(item,predicate,found);}else if(value&&typeof value==='object'){if(predicate(value))found.push(value);for(const item of Object.values(value))findAll(item,predicate,found);}return found;}
const files=[];function scan(dir){for(const ent of fs.readdirSync(dir,{withFileTypes:true})){assert.equal(ent.isSymbolicLink(),false);const file=path.join(dir,ent.name);if(ent.isDirectory())scan(file);else{const rel=path.relative(out,file).replaceAll('\\','/');assert.ok(!/(^|\/)(\.git|\.env|node_modules|server|package(?:-lock)?\.json)(\/|$)/.test(rel),rel);assert.ok(!/\.(?:map|sqlite|db)$/.test(rel),rel);assert.ok(fs.statSync(file).size<=25*1024*1024);files.push(rel);}}}scan(out);
for(const [file,url] of [['index.html',site.canonical],['methodology/index.html',origin+'/methodology/'],['about/index.html',origin+'/about/']]){
 const html=read(file);assert.equal((html.match(/<h1>/g)||[]).length,1);assert.equal((html.match(/rel="canonical"/g)||[]).length,1);assert.ok(html.includes(`rel="canonical" href="${url}"`));assert.ok(html.includes('name="robots" content="index,follow'));assert.ok(html.includes('property="og:url" content="'+url+'"'));
 const description=html.match(/name="description" content="([^"]+)"/)[1];assert.ok(description.length>=70&&description.length<=170);
 const graph=JSON.parse(html.match(/<script type="application\/ld\+json">(.*?)<\/script>/s)[1])['@graph'];assert.ok(graph.some(x=>x['@type']==='WebPage'&&x.url===url));
 const persons=findAll(graph,item=>item['@type']==='Person');assert.ok(persons.length>0);for(const person of persons){assert.equal(person['@id'],maintainerId);assert.equal(person.url,maintainerUrl);}
 const types=findAll(graph,item=>typeof item['@type']==='string').map(item=>item['@type']);assert.ok(!types.includes('Dataset'));assert.ok(!types.includes('FinancialProduct'));
 if(file==='about/index.html')assert.ok(html.includes(`href="${maintainerUrl}"`));
 if(file==='methodology/index.html'){assert.ok(html.includes('https://mkgrid.co.technology/'));assert.ok(html.includes('separate hybrid model'));}
 for(const m of html.matchAll(/(?:href|src)="(\/[^"#?]*)"/g)){const ref=m[1].endsWith('/')?m[1]+'index.html':m[1];assert.ok(fs.existsSync(path.join(out,ref)),`${file}: missing ${ref}`);}
}
const googleVerification='xZhKdS0U-QfuZ7T0-Rz75ERIZu732Mh0sa85UiwUcgs',home=read('index.html');assert.equal((home.match(/<meta name="google-site-verification"/g)||[]).length,1);assert.ok(home.includes(`<meta name="google-site-verification" content="${googleVerification}">`));
const facts=JSON.parse(read('app.json')),runtime=read('run/index.html');assert.equal(facts.url,site.canonical);assert.equal(facts.applicationUrl,origin+'/run/');assert.equal(facts.authorUrl,maintainerUrl);assert.equal(facts.runtimeSha256,createHash('sha256').update(runtime).digest('hex'));assert.match(runtime,/name="robots" content="noindex,follow"/);assert.ok(runtime.includes(`rel="canonical" href="${site.canonical}"`));assert.ok(!runtime.includes("location.protocol==='http:'&&['127.0.0.1','localhost'].includes(location.hostname)"));
assert.equal((read('sitemap.xml').match(/<loc>/g)||[]).length,3);assert.ok(!read('sitemap.xml').includes('/run/'));assert.ok(read('robots.txt').includes(origin+'/sitemap.xml'));for(const bot of ['*','Googlebot','Bingbot','OAI-SearchBot','GPTBot','PerplexityBot','Claude-SearchBot'])assert.ok(read('robots.txt').includes(`User-agent: ${bot}\nAllow: /`));
assert.ok(read('llms.txt').includes('3,888'));assert.ok(read('llms.txt').includes(maintainerId));assert.ok(read('llms.txt').includes('Separate MKGrid hybrid-energy research preview'));
const fullText=read('llms-full.txt');for(const value of ['3,888 retained hourly','nine strategies','30 MW','53 absent hours','319 negative-price hours','Mohammad Rezwan Khan','separate hybrid model'])assert.ok(fullText.includes(value),`llms-full.txt missing ${value}`);assert.ok(fullText.includes('Source: '+site.canonical));assert.ok(fullText.includes('Source: '+origin+'/about/'));assert.ok(fullText.includes('Source: '+origin+'/methodology/'));
const indexNowKey='242a5dcf79d9b1321ecc7abbcc603171';assert.equal(read(indexNowKey+'.txt').trim(),indexNowKey);
assert.ok(read('_headers').includes(site.project+'.pages.dev/*'));
console.log(JSON.stringify({status:'passed',project:site.project,pages:3,files:files.length,runtimeSha256:facts.runtimeSha256}));
