"""Explicit online preparation of small Jupiter/Saturn ephemeris excerpts."""

from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
PACKS = [('jup365', '501,502,503,504,599'), ('sat441l', '606,699')]

if __name__ == '__main__':
    folder = ROOT / 'resources/ephemerides'
    folder.mkdir(parents=True, exist_ok=True)
    manifests = []
    for name, targets in PACKS:
        url = f'https://ssd.jpl.nasa.gov/ftp/eph/satellites/bsp/{name}.bsp'
        pending = folder / (name + '.partial.bsp')
        subprocess.run([sys.executable, '-m', 'jplephem', 'excerpt', '--targets', targets,
                        '2025/1/1', '2028/1/1', url, str(pending)], check=True, timeout=300)
        from jplephem.spk import SPK
        with SPK.open(str(pending)) as kernel:
            if not {int(t) for t in targets.split(',')} <= {s.target for s in kernel.segments}:
                raise ValueError('Satellite excerpt is missing required targets.')
        destination = folder / f'{name}-2025-2028.bsp'
        pending.replace(destination)
        with destination.open('rb') as stream:
            digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        metadata = {'source': url, 'file': destination.name, 'bytes': destination.stat().st_size,
                    'sha256': digest, 'start_utc': '2025-01-02T00:00:00+00:00',
                    'end_utc': '2027-12-31T00:00:00+00:00',
                    'excerpt_requested': '2025-01-01/2028-01-01; one-day safety margin for light travel time'}
        destination.with_suffix('.json').write_text(json.dumps(metadata, indent=2))
        manifests.append(metadata)
    (ROOT / 'resources/satellite-manifest.json').write_text(json.dumps(manifests, indent=2))
    print('Installed date-bounded local satellite ephemerides.')
