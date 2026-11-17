"""Build the offline deep-sky name pack from a pinned OpenNGC CSV."""

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

TYPES = {'G', 'GPair', 'GTrpl', 'GGroup', 'OCl', 'GCl', '*Ass', 'Cl+N',
         'PN', 'HII', 'Neb', 'EmN', 'RfN', 'SNR', 'DrkN', 'Nova'}
DEST = Path(__file__).resolve().parents[1] / 'astrolearn/data/identification'


def degrees(value):
    a, b, c = map(float, value.lstrip('+-').split(':'))
    return (-1 if value.startswith('-') else 1) * (a + b/60 + c/3600)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('csv', type=Path)
    parser.add_argument('revision')
    args = parser.parse_args()
    raw = args.csv.read_bytes()
    rows = csv.DictReader(raw.decode('utf-8-sig').splitlines(), delimiter=';')
    objects = []
    for row in rows:
        # Messier positions are already supplied by the base catalog.
        if row['Type'] not in TYPES or row['M'] or not (row['RA'] and row['Dec']):
            continue
        key = row['Name']
        designation = f'{key[:3]} {key[3:].lstrip("0")}' if key.startswith('NGC') else f'IC {key[2:].lstrip("0")}'
        common = row['Common names'].split(',')[0].strip()
        magnitude = float(row['V-Mag'] or row['B-Mag']) if row['V-Mag'] or row['B-Mag'] else None
        objects.append({'id': key, 'name': f'{common} ({designation})' if common else designation,
                        'common_name': common, 'kind': 'deep-sky object', 'catalog_type': row['Type'],
                        'ra_deg': round(15 * degrees(row['RA']), 8), 'dec_deg': round(degrees(row['Dec']), 8),
                        'magnitude': magnitude if magnitude is not None and math.isfinite(magnitude) else None})
    data = json.dumps(objects, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode('utf-8')
    (DEST/'openngc.json').write_bytes(data)
    (DEST/'openngc-manifest.json').write_text(json.dumps({
        'source': 'https://github.com/mattiaverga/OpenNGC', 'revision': args.revision,
        'attribution': 'Mattia Verga and OpenNGC contributors',
        'license': 'CC-BY-SA-4.0', 'license_file': 'OpenNGC-LICENSE.txt',
        'changes': 'Selected extended objects, excluded Messier duplicates, converted coordinates to degrees and formatted names.',
        'object_count': len(objects), 'source_sha256': hashlib.sha256(raw).hexdigest(),
        'catalog_sha256': hashlib.sha256(data).hexdigest()}, indent=2)+'\n', encoding='utf-8')
    print(f'{len(objects):,} OpenNGC objects')


if __name__ == '__main__':
    main()
