"""Copy completed strategy evidence; retain symlinks explicitly, verify all bytes."""
import hashlib,json,os,shutil
from pathlib import Path
HERE=Path(__file__).resolve().parent
LAB=Path('/root/heroes3-ai-lab');EXP=HERE.parent
OUT=HERE/'strategic-delivery-01'/'archive'
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        while block:=f.read(1024*1024):h.update(block)
    return h.hexdigest()
def mapped(p):
    p=Path(p)
    if str(p).startswith('/root/heroes3-ai-lab/'):
        return OUT/'linux'/p.relative_to('/root/heroes3-ai-lab')
    if str(p).startswith('/mnt/g/Heroes3-AI-Lab/'):
        return OUT/'workspace'/p.relative_to('/mnt/g/Heroes3-AI-Lab')
    raise ValueError('Unregistered source root: '+str(p))
def main():
    OUT.mkdir(parents=True,exist_ok=False)
    roots=[LAB/'evaluations'/name for name in ['strategic-learned-recruitment-train-20261023-01','strategic-learned-recruitment-dev-20261023-01','strategic-learned-recruitment-mechanism-20261023-01','strategic-learned-recruitment-capsule-02']]
    roots += [EXP/'strategic-learned-recruitment-policy-v2',EXP/'strategic-learned-recruitment-run-v1',EXP/'strategic-learned-recruitment-native-v3']
    for p in roots:
        shutil.copytree(p,mapped(p),symlinks=True,ignore=shutil.ignore_patterns('__pycache__'))
    plans=[LAB/'evaluations/strategic-learned-recruitment-train-20261023-01/PLAN.json']
    plans+=list((LAB/'evaluations/strategic-learned-recruitment-dev-20261023-01').glob('pair-*/*/native/PLAN.json'))
    plans+=list((LAB/'evaluations/strategic-learned-recruitment-train-20261023-01').glob('cell-*/native/PLAN.json'))
    closure={}
    for p in plans:
        d=json.loads(p.read_text());closure.update(d.get('hashes',d.get('input_sha256',{})))
    for path,h in closure.items():
        src=Path(path);assert sha(src)==h,'Source changed: '+path
        dest=mapped(src)
        if not dest.exists():dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dest)
        assert not dest.is_symlink() and sha(dest)==h
    ordinary=[];links=[];total=0
    for base,dirs,names in os.walk(OUT,followlinks=False):
        for name in sorted(dirs+names):
            p=Path(base)/name
            if p.is_symlink():links.append(dict(path=str(p.relative_to(OUT)),target=os.readlink(p)))
            elif p.is_file():
                # Map back to the exact original source and verify a second full pass.
                rel=p.relative_to(OUT);prefix=LAB if rel.parts[0]=='linux' else Path('/mnt/g/Heroes3-AI-Lab')
                src=prefix/Path(*rel.parts[1:]);digest=sha(p)
                assert digest==sha(src),str(src)
                size=p.stat().st_size;total+=size
                ordinary.append(dict(path=str(rel),sha256=digest,bytes=size))
    manifest=dict(passed=True,ordinary_files=len(ordinary),symlinks=len(links),ordinary_bytes=total,files=ordinary,links=links,
        external_runtime_assets='Data/Mods symlinks are retained targets; their trees are not claimed copied. Original absolute paths require relocation mapping on another machine.',
        exact_original_source_and_copy_byte_verification=True)
    output=OUT.parent/'ARCHIVE_MANIFEST.json';output.write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(dict(passed=True,ordinary_files=len(ordinary),symlinks=len(links),ordinary_bytes=total,manifest=str(output),manifest_sha256=sha(output))))
if __name__=='__main__':main()
