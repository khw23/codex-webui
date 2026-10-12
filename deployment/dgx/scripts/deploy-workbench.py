#!/usr/bin/env python3
"""Switch this DGX deployment to a validated, fixed workbench build; no API calls to models."""
import datetime, hashlib, http.cookiejar, json, os, re, shutil, subprocess, tarfile, urllib.request
from pathlib import Path
root=Path('/home/khw/projects/web-ui');unit=Path.home()/'.config/systemd/user/codex-webui.service'
run=lambda *args:subprocess.run(args,check=True,capture_output=True,text=True)
def auth_get_sessions():
    jar=http.cookiejar.CookieJar();opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    credentials=json.loads((root/'runtime/credentials.json').read_text())
    opener.open(urllib.request.Request('http://127.0.0.1:4173/api/auth/login',data=json.dumps({'password':credentials['owner']}).encode(),headers={'Origin':'http://127.0.0.1:4173','Content-Type':'application/json'}),timeout=10).close()
    data=json.load(opener.open('http://127.0.0.1:4173/api/sessions?limit=200',timeout=20))
    assert not data.get('nextCursor'), 'Reconcile remaining sessions before deploying'
    busy=[s['id'] for s in data['sessions'] if s.get('status') in ('running','active','starting','inProgress','waitingForApproval','waitingForInput') or s.get('queueCount',0)]
    assert not busy, 'Active or queued tasks: deployment deferred'
    return len(data['sessions'])
def main():
    count=auth_get_sessions()
    timestamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    release=root/'releases'/('workbench-'+timestamp);release.mkdir(parents=True)
    for source,dest in [(root/'workbench/build/static',release/'build/static'),(root/'workbench/dist',release/'dist')]:
        dest.parent.mkdir(parents=True,exist_ok=True);shutil.copytree(source,dest)
    commit=run('git','-C',str(root/'workbench'),'rev-parse','HEAD').stdout.strip()
    (release/'release.json').write_text(json.dumps({'commit':commit,'built_from':'workbench/projects','created_at':timestamp},indent=2)+'\n')
    backup=root/'backups'/('before-workbench-'+timestamp);backup.mkdir(mode=0o700,parents=True)
    shutil.copy2(unit,backup/'codex-webui.service');shutil.copy2(root/'runtime/webui.env',backup/'webui.env')
    current=root/'current';prior=os.readlink(current) if current.is_symlink() else None
    run('systemctl','--user','stop','codex-webui')
    try:
        with tarfile.open(backup/'runtime.tar.gz','w:gz') as archive:
            archive.add(root/'runtime',arcname='runtime',filter=lambda entry: None if entry.name.startswith('runtime/workbench-test') else entry)
        envpath=root/'runtime/webui.env';environment=envpath.read_text()
        for key in ['CODEX_WEBUI_ALLOWED_ROOTS','CODEX_WEBUI_PROJECTS_ROOT']:
            line=f"{key}='/home/khw/projects/web-ui-projects'"
            if re.search('^'+key+'=',environment,re.M):environment=re.sub('^'+key+'=.*$',lambda _:line,environment,flags=re.M)
            else:environment+='\n'+line+'\n'
        tmp=envpath.with_suffix('.next');tmp.write_text(environment);tmp.chmod(0o600);tmp.replace(envpath)
        nextlink=root/'.current-next';nextlink.symlink_to(release);nextlink.replace(current)
        service=(backup/'codex-webui.service').read_text().replace(str(root/'upstream'),str(root/'current'))
        unit.write_text(service);(root/'config/codex-webui.service').write_text(service)
        run('systemctl','--user','daemon-reload');run('systemctl','--user','start','codex-webui')
    except BaseException:
        shutil.copy2(backup/'webui.env',root/'runtime/webui.env');shutil.copy2(backup/'codex-webui.service',unit)
        if current.is_symlink():current.unlink()
        if prior:current.symlink_to(prior)
        run('systemctl','--user','daemon-reload');run('systemctl','--user','start','codex-webui')
        raise
    evidence={'release':str(release),'source_commit':commit,'backup':str(backup),'predeployment_idle_sessions':count,'previous_release':prior,'projects_root':'/home/khw/projects/web-ui-projects','service':'codex-webui.service','time':timestamp}
    (root/'evidence/workbench-deployment.json').write_text(json.dumps(evidence,indent=2)+'\n');print(json.dumps(evidence))
if __name__=='__main__':main()
