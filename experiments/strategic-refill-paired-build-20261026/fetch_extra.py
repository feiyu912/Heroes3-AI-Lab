"""Fetch named extra packages at their saved original versions; never install."""
import concurrent.futures,hashlib,json,sys,subprocess
from pathlib import Path
import fetch_packages as f

def main(names):
    source=Path('/home/kaicheng/Documents/Codex/2026-10-24/hello/outputs/WSL迁出-20261025/环境记录/dpkg-status.txt')
    assert hashlib.sha256(source.read_bytes()).hexdigest()=='3732f6ced064135e8b3579c509b333e7e8353a3ddebce3758d25822ebf676d39'
    original={}
    for b in source.read_text().split('\n\n'):
        row=f.fields(b)
        if row.get('Package') in names:original[row['Package']]=row
    assert set(original)==set(names),set(names)-set(original)
    targets={(n,v['Version']) for n,v in original.items()};catalog={}
    for suite in ('jammy-updates','jammy','jammy-security'):
        for component in ('main','universe'):
            if targets<=catalog.keys():break
            catalog.update(f.index(suite,component))
    run=f.OUT/('extra-'+hashlib.sha256('\n'.join(sorted(names)).encode()).hexdigest()[:12]+'.json')
    assert not run.exists(),'Never overwrite old download result'
    def one(key):
        entry=catalog.get(key)
        if not entry:return {'package':key[0],'version':key[1],'found':False}
        dest=f.OUT/Path(entry['Filename']).name;data=f.fetch('https://archive.ubuntu.com/ubuntu/'+entry['Filename'],dest)
        assert f.sha(data)==entry['SHA256'] and len(data)==int(entry['Size'])
        actual=subprocess.run(['dpkg-deb','-f',str(dest),'Package','Version','Architecture'],capture_output=True,text=True,check=True).stdout
        assert 'Package: '+key[0] in actual and 'Version: '+key[1] in actual
        print('verified extra',key,flush=True)
        return {'package':key[0],'version':key[1],'found':True,'verified':True,'metadata':entry,'deb_path':str(dest),'deb_sha256':f.sha(data),'control':actual}
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:rows=list(pool.map(one,sorted(targets)))
    run.write_text(json.dumps({'rows':rows,'system_installed':False,'extracted':False},indent=2)+'\n');print(run,flush=True)
if __name__=='__main__':main(sys.argv[1:])
