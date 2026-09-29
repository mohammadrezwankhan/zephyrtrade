"""Check installed package isolation, static assets and real loopback HTTP."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import tempfile
import zipfile

root=Path('/mnt/data/ZephyrTrade_Champion')
wheel=root/'dist/zephyrtrade-1.1.0-py3-none-any.whl'
with zipfile.ZipFile(wheel) as z:
    assert z.testzip() is None
    paths=['zephyrtrade/'+p.relative_to(root/'src/zephyrtrade').as_posix() for p in (root/'src/zephyrtrade').rglob('*') if p.is_file() and p.suffix in {'.py','.html','.css','.js'}]
    for rel in paths:
        assert z.read(rel)==(root/'src'/rel).read_bytes(),rel
print(f'Wheel matches all {len(paths)} final Python/web source files.')
with tempfile.TemporaryDirectory(prefix='zephyr-wheel-check-') as td:
    subprocess.run([sys.executable,'-m','pip','install','--no-index','--no-deps','--target',td,str(wheel)],check=True)
    program=r'''
import sys, json, threading, http.client
from pathlib import Path
sys.path.insert(0,sys.argv[1])
import zephyrtrade
from zephyrtrade.app import LocalServer, WEB_ROOT
assert zephyrtrade.__version__=='1.1.0'
assert Path(zephyrtrade.__file__).is_relative_to(Path(sys.argv[1]))
for name in ('index.html','styles.css','engine.js','app.js','snapshot.js'):
    assert (WEB_ROOT/name).is_file(),name
server=LocalServer(0)
thread=threading.Thread(target=server.serve_forever,daemon=True)
thread.start()
port=server.server_address[1]
try:
    conn=http.client.HTTPConnection('127.0.0.1',port,timeout=10)
    conn.request('GET','/api/health');response=conn.getresponse();data=json.loads(response.read());assert response.status==200 and data['version']=='1.1.0',data
    for endpoint in ('/','/styles.css','/engine.js','/app.js','/snapshot.js'):
        conn.request('GET',endpoint);response=conn.getresponse();body=response.read();assert response.status==200 and body,endpoint
    inputs=dict(capacity=30,da=400,up=600,down=200,hours=1,scenarios=[2,8,20],probabilities=[.2,.5,.3])
    conn.request('POST','/api/optimize',body=json.dumps(inputs),headers={'Content-Type':'application/json','Origin':f'http://127.0.0.1:{port}'})
    response=conn.getresponse();result=json.loads(response.read());assert response.status==200,result
    assert abs(result['offer_mw']-8)<1e-7,result
    assert abs(result['expected_revenue_dkk']-3200)<1e-7,result
    conn.close()
    print(json.dumps({'status':'PASS','installed_import':str(zephyrtrade.__file__),'version':zephyrtrade.__version__,'verified':'five static assets, health and real loopback SciPy solve','solution':result,'limitations':'Existing system scientific dependencies reused; not a clean dependency-resolution environment, normal browser session, Windows execution or deployment.'},indent=2))
finally:
    server.shutdown();server.server_close();thread.join(5)
'''
    subprocess.run([sys.executable,'-c',program,td],check=True,cwd=td)
print('Wheel ZIP integrity, exact-source parity and installed-package HTTP smoke: PASS.')
