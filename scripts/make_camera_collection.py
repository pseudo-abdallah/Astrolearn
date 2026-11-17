"""Create offline camera-like benchmark frames from one licensed local seed."""

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from astrolearn.camera_benchmark import build_collection

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--output', type=Path, default=Path('data/benchmarks'))
    parser.add_argument('--source-url', required=True)
    parser.add_argument('--group', required=True, help='Original observing session / observer group; keep together in dataset splits.')
    args = parser.parse_args()
    print(build_collection(args.source, args.output, args.source_url, args.group))
