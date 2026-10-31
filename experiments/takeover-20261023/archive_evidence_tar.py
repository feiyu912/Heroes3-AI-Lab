"""Stream immutable evidence into one archive and independently verify every member."""
import argparse,hashlib,io,json,os,resource,tarfile,time
from pathlib import Path
def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()
class HashReader:
    def __init__(self,stream):self.stream=stream;self.hash=hashlib.sha256();self.count=0
    def read(self,size=-1):
        data=self.stream.read(size);self.hash.update(data);self.count+=len(data);return data
def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--review',type=Path,required=True);p.add_argument('--package',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    assert json.loads((a.source/'RESULT.json').read_text())['passed']
    assert json.loads((a.review/'AUDIT.json').read_text())['passed']
    freeze=json.loads((a.package/'SOURCE_FREEZE.json').read_text())['files'];assert all(digest(path)==h for path,h in freeze.items())
    a.out.mkdir(parents=True,exist_ok=False);archive=a.out/'evidence.tar.gz';entries={};links={};seen=set();start=time.monotonic()
    with tarfile.open(archive,'w:gz',compresslevel=1,dereference=False) as tar:
        def add(path,name):
            key=str(name).replace('\\','/');assert not key.startswith('/') and '..' not in Path(key).parts
            if key in seen:return
            seen.add(key)
            info=tar.gettarinfo(str(path),arcname=key)
            if path.is_symlink():links[key]=os.readlink(path);tar.addfile(info);return
            if path.is_dir():tar.addfile(info);return
            assert path.is_file() and info.isfile()
            with path.open('rb') as stream:
                reader=HashReader(stream);tar.addfile(info,reader)
            assert reader.count==info.size
            entries[key]=dict(source=str(path),sha256=reader.hash.hexdigest(),bytes=info.size)
            if len(entries)%2000==0:(a.out/'PROGRESS.json').write_text(json.dumps(dict(phase='write',files=len(entries))))
        for root,prefix in ((a.source,Path('run')),(a.review,Path('independent-review')),(a.package,Path('package'))):
            for directory,dirs,files in os.walk(root,followlinks=False):
                for name in dirs+files:
                    path=Path(directory)/name;add(path,prefix/path.relative_to(root))
        for path in freeze:add(Path(path),Path('frozen-inputs')/Path(path).relative_to('/'))
        payload=json.dumps(dict(files=entries,external_symlinks=links),sort_keys=True).encode()
        info=tarfile.TarInfo('__evidence_manifest__.json');info.size=len(payload);tar.addfile(info,io.BytesIO(payload))
    verified=set();verified_links={}
    with tarfile.open(archive,'r:gz') as tar:
        for member in tar:
            if member.isdir():continue
            if member.issym():verified_links[member.name]=member.linkname;continue
            assert member.isfile()
            if member.name=='__evidence_manifest__.json':
                assert json.load(tar.extractfile(member))==dict(files=entries,external_symlinks=links);continue
            assert member.name in entries and member.name not in verified
            expected=entries[member.name];h=hashlib.sha256();size=0
            with tar.extractfile(member) as stream:
                for block in iter(lambda:stream.read(1024*1024),b''):h.update(block);size+=len(block)
            assert h.hexdigest()==expected['sha256'] and size==expected['bytes']
            assert digest(expected['source'])==expected['sha256'],'Source changed while archiving'
            verified.add(member.name)
    assert verified==set(entries) and verified_links==links
    report=dict(passed=True,ordinary_files=len(entries),ordinary_bytes=sum(e['bytes'] for e in entries.values()),archive_bytes=archive.stat().st_size,archive_sha256=digest(archive),all_archive_members_and_source_SHA_equal=True,symlink_targets_recorded_not_traversed=links,seconds=time.monotonic()-start,max_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,source=str(a.source),review=str(a.review),package=str(a.package),new_native_games=0,optimizer_steps=0)
    (a.out/'ARCHIVE.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k!='symlink_targets_recorded_not_traversed'},indent=2))
if __name__=='__main__':main()
