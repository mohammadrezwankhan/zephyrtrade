/** Bundle the verified local snapshot and browser assets; no data regeneration/network. */
import {readFile,writeFile} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
import {withBrowserPolicy} from './browser-csp.mjs';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const web=path.join(root,'src/zephyrtrade/web');
let html=await readFile(path.join(web,'index.html'),'utf8');
const css=await readFile(path.join(web,'styles.css'),'utf8');
html=html.replace('<link rel="stylesheet" href="styles.css">',()=>'<style>\n'+css+'\n</style>');
for(const name of ['snapshot.js','engine.js','app.js']){
 const script=(await readFile(path.join(web,name),'utf8')).replace(/<\/script/gi,match=>'<\\/'+match.slice(2));
 html=html.replace(`<script src="${name}" defer></script>`,()=>'<script>\n'+script+'\n</script>');
}
await writeFile(path.join(root,'ZephyrTrade-Champion.html'),withBrowserPolicy(html));
console.log('Bundled the local snapshot and browser assets with exact CSP hashes.');
