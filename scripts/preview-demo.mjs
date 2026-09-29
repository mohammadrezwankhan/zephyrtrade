// Serve only the reviewed standalone demo; never expose the repository tree.
import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
const artifact = new URL("../ZephyrTrade-Champion.html", import.meta.url);
const page = await readFile(artifact);
const port = Number(process.env.PORT ?? 4173);
if (!Number.isInteger(port) || port < 0 || port > 65535) throw new Error('PORT must be an integer from 0 to 65535');
const server = createServer((req, res) => {
  if (!['GET','HEAD'].includes(req.method)) { res.writeHead(405, {Allow:'GET, HEAD'}); res.end(); return; }
  if (!['/','/index.html'].includes((req.url ?? '/').split('?')[0])) { res.writeHead(404); res.end(); return; }
  res.writeHead(200, {'Content-Type':'text/html; charset=utf-8','Content-Length':page.length,'Cache-Control':'no-store','X-Content-Type-Options':'nosniff','Referrer-Policy':'no-referrer'});
  res.end(req.method === 'HEAD' ? undefined : page);
});
server.on('error', error => { console.error(`Preview failed: ${error.code ?? error.message}`); process.exitCode=1; });
server.listen(port,'127.0.0.1',()=>console.log(`ZephyrTrade: http://127.0.0.1:${server.address().port} — synthetic local demo`));
