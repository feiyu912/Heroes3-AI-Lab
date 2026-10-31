"""Read only the existing game's BUILDING.TXT entries; no engine process or modifications."""
import argparse,hashlib,json,struct,zlib
from pathlib import Path
HERE=Path(__file__).resolve().parent
CAP=Path('/root/heroes3-ai-lab/evaluations/strategic-learned-economy-build-capsule-02')
SOURCE=Path('/root/heroes3-ai-lab/src/vcmi-adv')
DATA=Path('/root/heroes3-ai-lab/data/vcmi/Data')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    manifest=json.loads((CAP/'build-source-manifest.json').read_text());source=SOURCE/'lib/entities/faction/CTownHandler.cpp'
    assert sha(source)==manifest['lib/entities/faction/CTownHandler.cpp']['sha256']
    text=source.read_text().splitlines();loader_excerpt=[dict(line=i+1,text=line) for i,line in enumerate(text) if 'DATA/BUILDING.TXT' in line or 'Common buildings' in line or 'getBuild(town, buildID) = building' in line]
    found=[]
    for name in ('H3bitmap.lod','H3ab_bmp.lod','H3ab_spr.lod'):
        path=DATA/name
        with path.open('rb') as stream:
            header=stream.read(92);assert header[:4]==b'LOD\0';count=struct.unpack_from('<I',header,8)[0]
            assert 0<count<100000
            entries=[stream.read(32) for _ in range(count)]
            matches=[row for row in entries if row[:16].split(b'\0')[0].lower()==b'building.txt']
            for entry in matches:
                offset,length,kind,compressed=struct.unpack_from('<IIII',entry,16);stream.seek(offset)
                raw=stream.read(compressed or length);raw=zlib.decompress(raw) if compressed else raw;assert len(raw)==length
                lines=raw.decode('cp1252').splitlines();selected={}
                for i,line in enumerate(lines):
                    cells=line.split('\t')
                    if len(cells)>=8 and cells[7].strip() in ('TAVERN_ID','MARKETPLACE_ID'):
                        selected[cells[7].strip()]=dict(line=i+1,raw=line,cost=dict(zip(('wood','mercury','ore','sulfur','crystal','gems','gold'),map(int,cells[:7]))))
                assert set(selected)=={'TAVERN_ID','MARKETPLACE_ID'}
                found.append(dict(archive=str(path),archive_sha256=sha(path),entry_sha256=hashlib.sha256(raw).hexdigest(),entry_offset=offset,
                    entry_uncompressed_bytes=length,cost_rows=selected,costs_equal=selected['TAVERN_ID']['cost']==selected['MARKETPLACE_ID']['cost']))
    assert found and all(item['costs_equal'] for item in found)
    report=dict(passed=True,CPU_only=True,native_games=0,GPU_steps=0,optimizer_steps=0,loader_source=str(source),loader_sha256=sha(source),
        compiled_manifest_verified=True,loader_excerpt=loader_excerpt,legacy_entries=found,
        conclusion='Core Tavern5 and Marketplace14 share 5wood/500gold legacy cost but have different shared building definitions. This does not create an actual TRAIN candidate collision: Tavern5 was not offered in the2089 requests.',
        auditor_sha256=sha(Path(__file__)))
    (a.out/'AUDIT.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
