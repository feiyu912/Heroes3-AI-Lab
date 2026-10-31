"""Download exact original packages, authenticating Ubuntu archive metadata first."""
from pathlib import Path
import concurrent.futures,hashlib,json,lzma,re,subprocess,urllib.request
HERE=Path(__file__).resolve().parent
OUT=HERE/'ubuntu-archive'
OUT.mkdir(exist_ok=True)
def sha(b):return hashlib.sha256(b).hexdigest()
def fetch(url,path):
    if path.exists():return path.read_bytes()
    data=urllib.request.urlopen(url,timeout=60).read();tmp=path.with_suffix(path.suffix+'.part');tmp.write_bytes(data);tmp.rename(path);return data
def fields(block):
    result={}
    for line in block.splitlines():
        if line and not line[0].isspace() and ': ' in line:
            k,v=line.split(': ',1);result[k]=v
    return result

def index(suite,component):
    base='https://archive.ubuntu.com/ubuntu/'
    release=OUT/(suite+'.InRelease');raw=fetch(base+'dists/'+suite+'/InRelease',release)
    verify=subprocess.run(['gpgv','--keyring','/usr/share/keyrings/ubuntu-archive-keyring.gpg',str(release)],capture_output=True,text=True)
    (OUT/(suite+'.verify.json')).write_text(json.dumps({'returncode':verify.returncode,'stdout':verify.stdout,'stderr':verify.stderr,'sha256':sha(raw)},indent=2)+'\n')
    assert verify.returncode==0,'Archive signature failed'
    name=component+'/binary-amd64/Packages.xz'
    matches=re.findall(r'^ ([0-9a-f]{64})\s+(\d+) '+re.escape(name)+r'$',raw.decode(),re.M)
    assert len(matches)==1,(suite,component,'SHA256 entry missing')
    digest,size=matches[0];payload=fetch(base+'dists/'+suite+'/'+name,OUT/(suite+'-'+component+'-Packages.xz'))
    assert len(payload)==int(size) and sha(payload)==digest,'Index SHA differs'
    entries={}
    for block in lzma.decompress(payload).decode().split('\n\n'):
        f=fields(block)
        if f.get('Package') and f.get('Architecture') in ('amd64','all'):entries[(f['Package'],f['Version'])]=f
    print('authenticated index',suite,component,len(entries),flush=True)
    return entries

def main():
    wanted=json.loads((HERE.parent/'ubuntu-native-toolchain-20261025/MISSING_TARGET_DEPENDENCIES.json').read_text())
    targets={(v['original_package'],v['original_version']) for v in wanted['missing']}
    catalog={}
    # Suites are sequential because both components share the signed release file.
    for suite in ('jammy-updates','jammy','jammy-security'):
        for component in ('main','universe'):
            if targets <= catalog.keys():break
            catalog.update(index(suite,component))
    plan=[]
    for key in sorted(targets):
        f=catalog.get(key)
        plan.append({'package':key[0],'version':key[1],'found':bool(f),'metadata':f})
    (OUT/'EXACT_PACKAGE_PLAN.json').write_text(json.dumps(plan,indent=2)+'\n')
    def download(row):
        if not row['found']:return row
        f=row['metadata'];filename=Path(f['Filename']).name;dest=OUT/filename
        b=fetch('https://archive.ubuntu.com/ubuntu/'+f['Filename'],dest)
        assert sha(b)==f['SHA256'] and len(b)==int(f['Size']),filename
        actual=subprocess.run(['dpkg-deb','-f',str(dest),'Package','Version','Architecture'],capture_output=True,text=True,check=True).stdout
        assert 'Package: '+row['package'] in actual and 'Version: '+row['version'] in actual,actual
        print('verified deb',filename,len(b),flush=True)
        return dict(row,deb_path=str(dest),deb_sha256=sha(b),control=actual,verified=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:result=list(pool.map(download,plan))
    (OUT/'DOWNLOAD_RESULT.json').write_text(json.dumps({'all_exact_packages_found':all(x['found'] for x in plan),'rows':result,'system_installed':False,'extracted':False},indent=2)+'\n')
    print('complete',sum(x.get('verified',False) for x in result),'/',len(result),flush=True)
if __name__=='__main__':main()
