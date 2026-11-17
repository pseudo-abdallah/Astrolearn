"""Record checksums for the exact offline resources installed in this workspace."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
paths = [ROOT / 'tools/astap/astap.exe', ROOT / 'tools/astap/astap_cli.exe', ROOT / 'resources/de421.bsp']
paths += sorted((ROOT / 'tools/astap').glob('*.001'))
paths += sorted((ROOT / 'tools/astap').glob('*.290'))
paths += sorted((ROOT / 'tools/astap').glob('*.1476'))
records = []
for path in paths:
    if path.is_file():
        with path.open('rb') as stream:
            checksum = hashlib.file_digest(stream, 'sha256').hexdigest()
        records.append({'path': path.relative_to(ROOT).as_posix(), 'bytes': path.stat().st_size,
                        'sha256': checksum})
destination = ROOT / 'resources/manifest.json'
destination.parent.mkdir(exist_ok=True)
destination.write_text(json.dumps({'resources': records, 'sources': {
    'ASTAP and catalogs': 'https://www.hnsky.org/astap.htm',
    'DE421': 'https://ssd.jpl.nasa.gov/ftp/eph/planets/bsp/de421.bsp',
    'catalog_revision': 'AstroLearn educational sample 2026-11-02; approximate J2000; no proper motion',
}}, indent=2), encoding='utf-8')
print(f'Recorded {len(records)} resource checksums in {destination}')
