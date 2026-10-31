"""Recover the exact original liblzma from signed Ubuntu snapshot metadata."""
from pathlib import Path
import hashlib,json,lzma,re,subprocess,urllib.request
import fetch_packages as f
out=f.OUT/'snapshot-20261001';out.mkdir(exist_ok=True)
base='https://snapshot.ubuntu.com/ubuntu/20261001T000000Z/'
raw=f.fetch(base+'dists/jammy-updates/InRelease',out/'InRelease')
p=subprocess.run(['gpgv','--keyring','/usr/share/keyrings/ubuntu-archive-keyring.gpg',str(out/'InRelease')],capture_output=True,text=True)
(out/'SIGNATURE.json').write_text(json.dumps({'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr,'sha256':f.sha(raw),'base':base,'historical_snapshot_intentionally_used':True},indent=2)+'\n');assert p.returncode==0
name='main/binary-amd64/Packages.xz';match=re.findall(r'^ ([0-9a-f]{64})\s+(\d+) '+re.escape(name)+r'$',raw.decode(),re.M);assert len(match)==1
data=f.fetch(base+'dists/jammy-updates/'+name,out/'Packages.xz');assert f.sha(data)==match[0][0] and len(data)==int(match[0][1])
entries=[f.fields(b) for b in lzma.decompress(data).decode().split('\n\n')];entry=next(x for x in entries if x.get('Package')=='liblzma5' and x.get('Version')=='5.2.5-2ubuntu1.1')
dest=out/Path(entry['Filename']).name;payload=f.fetch(base+entry['Filename'],dest);assert f.sha(payload)==entry['SHA256'] and len(payload)==int(entry['Size'])
control=subprocess.run(['dpkg-deb','-f',str(dest),'Package','Version','Architecture'],capture_output=True,text=True,check=True).stdout
assert 'Package: liblzma5\n' in control and 'Version: 5.2.5-2ubuntu1.1\n' in control
(out/'DOWNLOAD_RESULT.json').write_text(json.dumps({'verified':True,'metadata':entry,'deb_path':str(dest),'deb_sha256':f.sha(payload),'control':control,'base':base,'system_installed':False},indent=2)+'\n');print('exact liblzma verified',len(payload),flush=True)
