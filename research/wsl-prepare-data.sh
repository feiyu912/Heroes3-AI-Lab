#!/usr/bin/env bash
set -euo pipefail
lab_root=/root/heroes3-ai-lab
lab_gym=$lab_root/src/gym
lab_data=$lab_root/data/vcmi
mkdir -p "$lab_data/Data" "$lab_data/Maps" "$lab_data/Mods" "$lab_root/config" "$lab_root/cache"
for lab_archive in H3ab_bmp.lod H3ab_spr.lod H3bitmap.lod H3sprite.lod H3ab_ahd.snd Heroes3.snd; do
    cp -n "/mnt/f/heroes3/Data/$lab_archive" "$lab_data/Data/$lab_archive"
done
cp -a "$lab_gym/vcmi/Mods/vcmi" "$lab_data/Mods/"
cp -a "$lab_gym/vcmi/Mods/ML" "$lab_data/Mods/"
ln -sfn "$lab_gym/maps/gym" "$lab_data/Maps/gym"
mkdir -p "$lab_gym/vcmi/data"
ln -sfn "$lab_data/Data" "$lab_gym/vcmi/data/Data"
ln -sfn "$lab_data/Maps" "$lab_gym/vcmi/data/Maps"
ln -sfn "$lab_data/Mods" "$lab_gym/vcmi/data/Mods"
printf 'Prepared independent game data: %s\n' "$lab_data"
du -sh "$lab_data"
