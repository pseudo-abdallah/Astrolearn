"""Explicit one-time setup command; the running application never downloads data."""

import csv
import hashlib
from io import StringIO
import json
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parent.parent
DESTINATION = ROOT / 'astrolearn' / 'data' / 'identification'
REPOSITORY = 'dieghernan/celestial_data'


def fetch(url):
    request = urllib.request.Request(url, headers={'User-Agent': 'AstroLearn-catalog-import/0.1'})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def main():
    # Resolve the revision once, then fetch every file from that immutable commit.
    revision = json.loads(fetch(f'https://api.github.com/repos/{REPOSITORY}/commits/main'))['sha']
    names = ['data/stars.8.min.geojson', 'data/starnames.csv', 'data/messier.min.geojson', 'LICENSE']
    raw = {name: fetch(f'https://raw.githubusercontent.com/{REPOSITORY}/{revision}/{name}') for name in names}
    name_rows = {row['id']: row for row in csv.DictReader(StringIO(raw['data/starnames.csv'].decode('utf-8-sig')))}
    stars = []
    for feature in json.loads(raw['data/stars.8.min.geojson'])['features']:
        props = feature['properties']
        key = str(feature.get('id', props.get('id')))
        row = name_rows.get(key, {})
        proper = next((row.get(field) for field in ('name', 'en') if row.get(field) not in {None, '', 'NA'}), None)
        coords = feature['geometry']['coordinates']
        stars.append({'id': f'HIP {key}', 'name': proper or f'HIP {key}', 'proper_name': bool(proper),
            'kind': 'star', 'ra_deg': coords[0] % 360, 'dec_deg': coords[1],
            'magnitude': props.get('mag'), 'constellation': row.get('c') if row.get('c') not in {'NA', ''} else None,
            'designation': row.get('desig') if row.get('desig') not in {'NA', ''} else None})
    objects = []
    for feature in json.loads(raw['data/messier.min.geojson'])['features']:
        props = feature['properties']
        coords = feature['geometry']['coordinates']
        key = str(feature.get('id', props.get('id')))
        objects.append({'id': key, 'name': props.get('name') or key, 'kind': 'deep-sky object',
                        'ra_deg': coords[0] % 360, 'dec_deg': coords[1], 'magnitude': props.get('mag'),
                        'catalog_type': props.get('type')})
    # Validate key joins rather than silently shipping a position-only catalog.
    if len(stars) < 10000 or not any(s['name'] == 'Betelgeuse' for s in stars):
        raise ValueError('Unexpected star catalog structure or missing name join.')
    if len(objects) < 100:
        raise ValueError('Unexpected Messier catalog structure.')
    DESTINATION.mkdir(parents=True, exist_ok=True)
    payload = {'stars': stars, 'objects': objects}
    encoded = json.dumps(payload, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode('utf-8')
    (DESTINATION / 'catalog.json').write_bytes(encoded)
    (DESTINATION / 'LICENSE-celestial-data.txt').write_bytes(raw['LICENSE'])
    manifest = {'source': f'https://github.com/{REPOSITORY}', 'revision': revision, 'license': 'BSD-3-Clause',
        'reference_frame': 'J2000; static catalog without observation-epoch proper-motion correction',
        'star_count': len(stars), 'named_star_count': sum(s['proper_name'] for s in stars), 'object_count': len(objects),
        'catalog_sha256': hashlib.sha256(encoded).hexdigest(),
        'source_files': {name: hashlib.sha256(value).hexdigest() for name, value in raw.items()},
        'attribution': 'Olaf Frohn and Diego Hernangomez; celestial_data derived from d3-celestial; XHIP star compilation and Messier/SEDS source records.'}
    (DESTINATION / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(json.dumps({key: manifest[key] for key in ('revision', 'star_count', 'named_star_count', 'object_count')}))


if __name__ == '__main__':
    main()
