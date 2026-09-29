import subprocess,sys,time,json,datetime,pathlib,os
label,cwd,*command=sys.argv[1:]
out=pathlib.Path('/mnt/data/work/evidence'); start=time.perf_counter()
env=os.environ.copy(); env['PYTHONPATH']=str(pathlib.Path(cwd)/'src'); env.update({'MPLBACKEND':'Agg','OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1'})
p=subprocess.run(command,cwd=cwd,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
(out/f'{label}.log').write_text(p.stdout)
record={'id':label,'cwd':cwd,'command':command,'timestamp_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'exit_code':p.returncode,'duration_seconds':round(time.perf_counter()-start,3),'log':f'{label}.log'}
with (out/'commands.jsonl').open('a') as f: f.write(json.dumps(record)+'\n')
print(json.dumps(record)); print(p.stdout[-15000:]); sys.exit(p.returncode)
