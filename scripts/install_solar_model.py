"""One-time local model preparation. Runtime classification never downloads."""

import hashlib
import json
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parent.parent

if __name__ == '__main__':
    manifest = json.loads((ROOT / 'resources/solar-model-manifest.json').read_text())
    folder = ROOT / 'resources/solar-model'
    folder.mkdir(exist_ok=True)
    for name in ('model_quantized.onnx', 'tokenizer.json', 'tokenizer_config.json', 'preprocessor_config.json', 'README.md'):
        remote = 'onnx/' + name if name.endswith('.onnx') else name
        url = f"https://huggingface.co/{manifest['source']}/resolve/{manifest['revision']}/{remote}"
        target = folder / name
        pending = folder / (name + '.partial')
        urllib.request.urlretrieve(url, pending)
        with pending.open('rb') as stream:
            digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        if digest != manifest[name]['sha256']:
            raise ValueError('Downloaded model resource checksum mismatch: ' + name)
        pending.replace(target)
    (folder / 'manifest.json').write_text(json.dumps(manifest, indent=2))
    print('Pinned local visual-model resources installed.')
