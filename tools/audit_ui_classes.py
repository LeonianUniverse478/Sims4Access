"""Read ABC instance tables to distinguish class definitions from references."""
import json
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools' / 'vendor'))
from dbpf_extract import read_index, read_resource_bytes


class ABC:
    def __init__(self, data):
        self.data, self.pos = data, 4

    def byte(self):
        result = self.data[self.pos]
        self.pos += 1
        return result

    def u30(self):
        result = 0
        for shift in range(0, 35, 7):
            value = self.byte()
            result |= (value & 127) << shift
            if not value & 128:
                return result
        raise ValueError('bad u30')

    def traits(self):
        for _ in range(self.u30()):
            self.u30()
            kind = self.byte()
            tag = kind & 15
            if tag in (0, 6):
                self.u30(); self.u30()
                if self.u30(): self.byte()
            elif tag in (1, 2, 3, 4, 5):
                self.u30(); self.u30()
            else: raise ValueError(('trait', tag))
            if kind & 64:
                for _ in range(self.u30()): self.u30()

    def definitions(self):
        for _ in range(2):
            for _ in range(max(0, self.u30() - 1)): self.u30()
        count = self.u30()
        self.pos += max(0, count - 1) * 8
        strings = ['']
        for _ in range(max(0, self.u30() - 1)):
            size = self.u30()
            strings.append(self.data[self.pos:self.pos + size].decode('utf-8'))
            self.pos += size
        namespaces = ['']
        for _ in range(max(0, self.u30() - 1)):
            self.byte()
            namespaces.append(strings[self.u30()])
        for _ in range(max(0, self.u30() - 1)):
            for _ in range(self.u30()): self.u30()
        names = ['']
        for _ in range(max(0, self.u30() - 1)):
            kind = self.byte()
            name = ''
            if kind in (7, 13):
                ns, local = self.u30(), self.u30()
                name = namespaces[ns] + '.' + strings[local]
            elif kind in (15, 16): self.u30()
            elif kind in (17, 18): pass
            elif kind in (9, 14): self.u30(); self.u30()
            elif kind in (27, 28): self.u30()
            elif kind == 29:
                self.u30()
                for _ in range(self.u30()): self.u30()
            else: raise ValueError(('multiname', kind))
            names.append(name)
        for _ in range(self.u30()):
            count = self.u30()
            self.u30()
            for _ in range(count): self.u30()
            self.u30()
            flags = self.byte()
            if flags & 8:
                for _ in range(self.u30()): self.u30(); self.byte()
            if flags & 128:
                for _ in range(count): self.u30()
        for _ in range(self.u30()):
            self.u30()
            for _ in range(self.u30() * 2): self.u30()
        found = []
        for _ in range(self.u30()):
            found.append(names[self.u30()])
            self.u30()
            if self.byte() & 8: self.u30()
            for _ in range(self.u30()): self.u30()
            self.u30()
            self.traits()
        return found


def definitions(raw):
    assert raw[:3] in (b'GFX', b'FWS')
    pos = 8 + (5 + 4 * (raw[8] >> 3) + 7) // 8 + 4
    result = set()
    while pos + 2 <= len(raw):
        header = struct.unpack_from('<H', raw, pos)[0]
        pos += 2
        size = header & 63
        if size == 63:
            size = struct.unpack_from('<I', raw, pos)[0]
            pos += 4
        body = raw[pos:pos + size]
        pos += size
        if header >> 6 == 82:
            start = body.index(b'\0', 4) + 1
            result.update(ABC(body[start:]).definitions())
        if header >> 6 == 0: break
    return result


def main():
    names = {}
    table = ROOT / 'reference/ui-movie-names.tsv'
    for line in (table.read_text(encoding='utf-8').splitlines() if table.is_file() else []):
        parts = line.split('\t')
        if len(parts) == 2:
            try: names[int(parts[0], 16)] = parts[1]
            except ValueError: pass
    targets = ('olympus.core.TooltipManager', 'olympus.dialog.DialogManager',
               'widgets.Gameplay.AgeUpPanel.AgeUpPanelMain', 'widgets.Pickers.PickersMain')
    found = {name: [] for name in targets}
    movies = {}
    sys.path.insert(0, str(ROOT / 'flash'))
    from flash_config import ui_package
    with open(ui_package(), 'rb') as f:
        for entry in list(read_index(f)):
            if entry['type'] != 0x62ECC59A: continue
            raw = read_resource_bytes(f, entry)
            classes = definitions(raw)
            name = names.get(entry['instance'], '%016X' % entry['instance'])
            movies[name] = {'instance': '%016X' % entry['instance'], 'class_count': len(classes)}
            for target in targets:
                if target in classes: found[target].append(name)
    (ROOT / 'build').mkdir(exist_ok=True)
    (ROOT / 'build/ui-class-audit-v6.json').write_text(json.dumps({'definitions': found, 'movies': movies}, indent=2) + '\n')
    for target, hosts in found.items(): print(target, len(hosts), ', '.join(hosts))


if __name__ == '__main__': main()
