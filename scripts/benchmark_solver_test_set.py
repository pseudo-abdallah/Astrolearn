"""Run fresh upload -> real local solve -> WCS checks in a new empty database."""
from pathlib import Path
import argparse
import json
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from fastapi.testclient import TestClient
from astropy.coordinates import SkyCoord
from astropy import units as u
from astrolearn.main import create_app


def benchmark(include_blind=False):
    folder = ROOT/'samples/plate-solving-test-set'
    manifest = json.loads((folder/'manifest.json').read_text())
    cases = list(manifest['cases'])
    if include_blind:
        cases += [dict(file='synthetic-orion-wide.png', type='synthetic integration control',
            expected='solved', expected_ra_deg=88.7929, expected_dec_deg=7.4071,
            tolerance_deg=.1, options={})]
    results = []
    with tempfile.TemporaryDirectory(prefix='astrolearn-fresh-benchmark-') as tmp:
        with TestClient(create_app(Path(tmp)/'empty.sqlite')) as client:
            for case in cases:
                started = time.monotonic()
                image = client.post('/api/v1/images', content=(folder/case['file']).read_bytes())
                image.raise_for_status()
                job = client.post(f"/api/v1/images/{image.json()['id']}/analyze", json={
                    'reuse_solution': False, 'options': case['options']})
                job.raise_for_status()
                deadline = time.monotonic()+260
                while True:
                    response = client.get('/api/v1/analyses/'+job.json()['id'])
                    response.raise_for_status()
                    analysis = response.json()
                    if analysis['status'] not in ('queued','running'):
                        break
                    if time.monotonic() > deadline:
                        raise TimeoutError(case['file'])
                    time.sleep(.2)
                plate = analysis.get('plate') or {}
                solved = plate.get('status') == 'solved'
                error = None
                if solved and case['expected']=='solved':
                    solution = plate['solution']
                    error = float(SkyCoord(solution['ra_deg']*u.deg, solution['dec_deg']*u.deg).separation(
                        SkyCoord(case['expected_ra_deg']*u.deg,case['expected_dec_deg']*u.deg)).deg)
                passed = (not solved if case['expected']=='unsolved' else
                    solved and error <= case['tolerance_deg']) and not plate.get('reused_from_solve_id')
                identification = plate.get('identification') or {}
                result = dict(file=case['file'], type=case['type'], passed=passed,
                    expected=case['expected'], solved=solved, error_deg=error,
                    solver=(plate.get('solution') or {}).get('solver'),
                    source_count=image.json()['analysis']['count'],
                    matched_stars=len(identification.get('matched_stars',[])),
                    named_stars=[s['name'] for s in identification.get('matched_stars',[]) if s.get('proper_name')],
                    expected_objects=[s['name'] for s in identification.get('expected_objects',[])],
                    solved_region=(plate.get('solution') or {}).get('solved_region'),
                    seconds=round(time.monotonic()-started,2),
                    message=analysis['message'], reused=False)
                results.append(result)
                print(json.dumps(result), flush=True)
                # Retain failures and native diagnostics for debugging too.
                (folder/'last-analysis.json').write_text(json.dumps(analysis, indent=2))
                (folder/'diagnostics').mkdir(exist_ok=True)
                (folder/'diagnostics'/(Path(case['file']).stem+'.json')).write_text(json.dumps(analysis,indent=2))
    report = dict(independent_survey_fields=manifest['independent_survey_fields'],
        fresh_database=True, reuse_solution=False, results=results,
        passed=sum(r['passed'] for r in results), total=len(results))
    (folder/'results.json').write_text(json.dumps(report, indent=2))
    print(f"{report['passed']}/{report['total']} checks passed", flush=True)
    return report['passed'] == report['total']


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--include-blind',action='store_true')
    sys.exit(0 if benchmark(parser.parse_args().include_blind) else 1)
