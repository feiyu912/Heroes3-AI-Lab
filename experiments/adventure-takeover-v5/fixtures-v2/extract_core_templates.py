"""Read local licensed H3 object metadata, following isolated ObjectTemplate::readTxt.

Only small template metadata is output; no sprites, sound, or whole archive redistribution.
"""
import hashlib
import json
from pathlib import Path
import struct
import zlib


class Lod:
    def __init__(self, path):
        self.path = path
        self.index = {}
        with path.open('rb') as f:
            header = f.read(92)
            assert header[:3] == b'LOD'
            for _ in range(struct.unpack_from('<I', header, 8)[0]):
                entry = f.read(32)
                name = entry[:16].split(b'\0', 1)[0].decode('ascii').lower()
                self.index[name] = struct.unpack_from('<4I', entry, 16)

    def read(self, name):
        offset, size, unknown, compressed = self.index[name.lower()]
        with self.path.open('rb') as f:
            f.seek(offset)
            data = f.read(compressed or size)
        decoded = zlib.decompress(data) if compressed else data
        assert len(decoded) == size
        return decoded


def main():
    data = Path('/root/heroes3-ai-lab/data/vcmi/Data')
    bitmaps = [Lod(data / name) for name in ('H3ab_bmp.lod', 'H3bitmap.lod')]
    sprites = [Lod(data / name) for name in ('H3ab_spr.lod', 'H3sprite.lod')]

    def read(archives, name):
        for lod in reversed(archives):
            if name.lower() in lod.index:
                return lod.read(name), str(lod.path)
        raise KeyError(name)

    text, archive = read(bitmaps, 'objects.txt')
    wanted = {(53, 0): 'sawmill', (53, 2): 'orePit', (53, 6): 'goldMine',
              (54, 0): 'pikeman', (54, 14): 'centaur'}
    output = {'source_objects_archive': archive,
              'objects_txt_sha256': hashlib.sha256(text).hexdigest(),
              'method': 'ObjectTemplate.cpp readTxt/readMsk/writeJson mask orientation', 'templates': {}}
    for line in text.decode('cp1252').splitlines()[1:]:
        cells = line.strip().strip('"').split()
        if len(cells) != 9:
            continue
        key = int(cells[5]), int(cells[6])
        if key not in wanted or wanted[key] in output['templates']:
            continue
        animation, block, visit = cells[:3]
        try:
            msk, msk_archive = read(sprites, animation.rsplit('.', 1)[0] + '.msk')
            width, height = msk[:2]
        except KeyError:
            width, height = 8, 6
            msk_archive = None
        assert 0 < width <= 8 and 0 < height <= 6
        mask = []
        for y in reversed(range(height)):
            row = ''
            for x in reversed(range(width)):
                index = y * 8 + x
                row += 'A' if visit[index] == '1' else 'B' if block[index] == '0' else 'V'
            mask.append(row)
        directions = ['+++', '+-+', '+++'] if int(cells[7]) in (2, 3, 4, 5) else ['---', '+-+', '+++']
        output['templates'][wanted[key]] = {'object_class': key[0], 'object_subtype_index': key[1],
            'legacy_animation': animation, 'msk_source_archive': msk_archive,
            'template': {'animation': animation, 'editorAnimation': '', 'mask': mask,
                         'visitableFrom': directions, 'zIndex': int(cells[8]) * 100}}
    required = {'sawmill', 'orePit', 'goldMine', 'pikeman'}
    assert required <= output['templates'].keys(), required - output['templates'].keys()
    target = Path(__file__).parent / 'core-template-audit.json'
    target.write_text(json.dumps(output, indent=2))
    print(json.dumps(output, indent=2))


if __name__ == '__main__':
    main()
