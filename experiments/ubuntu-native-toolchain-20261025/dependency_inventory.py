import json,re,subprocess,hashlib
from pathlib import Path
H=Path(__file__).resolve().parent
P=Path('/home/kaicheng/Documents/Codex/2026-10-24/hello/outputs/Heroes3-Toolchain-GCC11-01');R=P/'sysroot';L=R/'usr/lib/x86_64-linux-gnu'
status=Path('/home/kaicheng/Documents/Codex/2026-10-24/hello/outputs/WSL迁出-20261025/环境记录/dpkg-status.txt')
packages={}
for block in status.read_text().split('\n\n'):
 fields={}
 for line in block.splitlines():
  if line and not line[0].isspace() and ': ' in line:
   k,v=line.split(': ',1);fields[k]=v
 if fields.get('Status')=='install ok installed':packages[fields['Package']]=fields
mapping={'libasound.so.2':'libasound2','libpulse.so.0':'libpulse0','libX11.so.6':'libx11-6','libXext.so.6':'libxext6','libXcursor.so.1':'libxcursor1','libXinerama.so.1':'libxinerama1','libXi.so.6':'libxi6','libXfixes.so.3':'libxfixes3','libXrandr.so.2':'libxrandr2','libXss.so.1':'libxss1','libXxf86vm.so.1':'libxxf86vm1','libdrm.so.2':'libdrm2','libgbm.so.1':'libgbm1','libwayland-egl.so.1':'libwayland-egl1','libwayland-client.so.0':'libwayland-client0','libwayland-cursor.so.0':'libwayland-cursor0','libxkbcommon.so.0':'libxkbcommon0','libdecor-0.so.0':'libdecor-0-0','libfreetype.so.6':'libfreetype6','libharfbuzz.so.0':'libharfbuzz0b','libpng16.so.16':'libpng16-16','libjpeg.so.8':'libjpeg-turbo8','libtiff.so.5':'libtiff5','libwebp.so.7':'libwebp7','libmodplug.so.1':'libmodplug1','libfluidsynth.so.3':'libfluidsynth3','libvorbisfile.so.3':'libvorbisfile3','libFLAC.so.8':'libflac8','libmpg123.so.0':'libmpg123-0','libopusfile.so.0':'libopusfile0'}
rows=[];missing={}
for f in sorted(L.iterdir()):
 if f.is_symlink() or not f.is_file() or '.so' not in f.name or f.read_bytes()[:4]!=b'\x7fELF':continue
 x=subprocess.run(['/usr/bin/readelf','-d',str(f)],capture_output=True,text=True,check=True)
 deps=re.findall(r'\(NEEDED\).*?\[(.*?)\]',x.stdout);rows.append(dict(file=str(f),needed=deps))
 for n in deps:
  if not (L/n).exists() and not (R/'usr/lib/gcc/x86_64-linux-gnu/11'/n).exists():missing.setdefault(n,[]).append(f.name)
output=[]
for n,parents in sorted(missing.items()):
 pkg=mapping.get(n);d=packages.get(pkg,{})
 output.append(dict(soname=n,required_by=parents,original_package=pkg,original_version=d.get('Version'),original_arch=d.get('Architecture'),original_depends=d.get('Depends'),mapping_basis='SONAME/known Ubuntu package name, exact version from saved original dpkg status; file ownership not separately certified'))
result=dict(scope='direct missing DT_NEEDED of every extracted old target shared ELF; recursive dependencies of missing libraries still need package closure',original_status=str(status),original_status_sha256=hashlib.sha256(status.read_bytes()).hexdigest(),rows=rows,missing=output)
(H/'MISSING_TARGET_DEPENDENCIES.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(output,indent=2))
