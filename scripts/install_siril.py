"""One-time online setup; normal AstroLearn operation uses no downloader.

Run from the project root: .venv\Scripts\python.exe scripts\install_siril.py
The full Gaia catalog needs about 1.1 GB download plus 1.5 GB extracted storage.
"""

import bz2
import hashlib
import json
from pathlib import Path
import shutil
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parent.parent
DOWNLOAD = ROOT / 'downloads'
DOWNLOAD.mkdir(exist_ok=True)
URL = 'https://free-astro.org/download/siril-1.4.5-ucrt64_win.zip'
GAIA = 'https://zenodo.org/records/14692304/files/siril_cat_healpix8_astro.dat.bz2?download=1'
EXPECTED = '846ad4b12c50865df0cb8c5b23453f22eec78bbe9969e17d669ae19eb49d421f'


def sha(path):
    with path.open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


if __name__ == '__main__':
    archive = DOWNLOAD / 'siril-1.4.5.zip'
    if not archive.is_file() or not zipfile.is_zipfile(archive):
        urllib.request.urlretrieve(URL, archive)
    target = (ROOT / 'tools/siril').resolve()
    target.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as bundle:
        for item in bundle.infolist():
            if not (target / item.filename).resolve().is_relative_to(target):
                raise ValueError('Unsafe archive path')
        bundle.extractall(target)
    compressed = DOWNLOAD / 'siril-gaia.dat.bz2'
    if not compressed.is_file() or sha(compressed) != EXPECTED:
        urllib.request.urlretrieve(GAIA, compressed)
    if sha(compressed) != EXPECTED:
        raise ValueError('Gaia checksum mismatch; refusing to install.')
    catalog = ROOT / 'resources/siril/gaia_astrometric.dat'
    catalog.parent.mkdir(parents=True, exist_ok=True)
    pending = catalog.with_suffix('.partial')
    with bz2.open(compressed, 'rb') as source, pending.open('wb') as output:
        shutil.copyfileobj(source, output)
    pending.replace(catalog)
    metadata = {'source': GAIA, 'compressed_sha256': EXPECTED, 'sha256': sha(catalog),
                'bytes': catalog.stat().st_size, 'siril_url': URL, 'siril_zip_sha256': sha(archive)}
    catalog.with_suffix('.dat.json').write_text(json.dumps(metadata, indent=2))
    print('Siril and verified local Gaia catalog installed. Restart AstroLearn.')
