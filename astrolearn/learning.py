"""Local sky exploration, offline light curves and explicit SIMBAD enrichment."""

import csv
from datetime import datetime, timezone
import hashlib
from io import StringIO
import json
import math
import urllib.parse
import urllib.request

import numpy as np
from astropy import units as u
from astropy.coordinates import AltAz, EarthLocation, SkyCoord
from astropy.time import Time
from fastapi import APIRouter, HTTPException, Query, Request

from astrolearn.astronomy import SiteRequest
from astrolearn.identification import DATA, load_catalog


def sky_points(site: SiteRequest):
    catalog, _ = load_catalog(DATA)
    stars = [s for s in catalog['stars'] if s.get('magnitude') is not None and s['magnitude'] <= 5]
    coords = SkyCoord([s['ra_deg'] for s in stars] * u.deg, [s['dec_deg'] for s in stars] * u.deg)
    observer = EarthLocation.from_geodetic(site.longitude * u.deg, site.latitude * u.deg, site.elevation_m * u.m)
    horizontal = coords.transform_to(AltAz(obstime=Time(site.utc), location=observer, pressure=0 * u.hPa))
    return {'offline': True, 'utc': site.utc.isoformat(), 'frame': 'geometric AltAz; no atmospheric refraction',
            'stars': [{**star, 'altitude_deg': float(alt), 'azimuth_deg': float(az)}
                      for star, alt, az in zip(stars, horizontal.alt.deg, horizontal.az.deg) if alt >= 0],
            'message': 'Predicted sky from catalog positions, not an identification of your photograph.'}


def parse_lightcurve(raw: bytes):
    if len(raw) > 1_000_000:
        raise ValueError('Choose a CSV smaller than 1 MB.')
    try:
        reader = csv.DictReader(StringIO(raw.decode('utf-8-sig')))
        if not {'time', 'flux'} <= set(reader.fieldnames or []):
            raise ValueError('CSV requires time and flux column headers.')
        points = []
        for row in reader:
            if len(points) >= 10000:
                raise ValueError('At most 10,000 measurements are supported.')
            time, flux = float(row['time']), float(row['flux'])
            if not math.isfinite(time) or not math.isfinite(flux):
                raise ValueError('Time and flux must be finite numbers.')
            points.append([time, flux])
    except (UnicodeError, TypeError, KeyError, csv.Error) as exc:
        raise ValueError('Invalid light-curve CSV.') from exc
    if len(points) < 3:
        raise ValueError('Supply at least three measurements.')
    points.sort(key=lambda p: p[0])
    median = float(np.median([p[1] for p in points]))
    if median <= 0:
        raise ValueError('Median flux must be positive for normalization.')
    return {'points': [[t, f / median] for t, f in points], 'count': len(points),
            'median_flux': median, 'offline': True,
            'warning': 'Relative brightness only. Dips alone do not establish an exoplanet. Time units are those of your input file.'}


def fetch_simbad(identifier):
    # Only an existing catalog identifier reaches this function; escape literals
    # nonetheless. The remote URL is fixed and cannot be supplied by the client.
    escaped = identifier.replace("'", "''")
    query = ("SELECT TOP 1 b.main_id,b.otype,b.sp_type,b.ra,b.dec,b.plx_value "
             "FROM basic AS b JOIN ident AS i ON b.oid=i.oidref "
             f"WHERE i.id='{escaped}'")
    body = urllib.parse.urlencode({'request': 'doQuery', 'lang': 'adql', 'format': 'json', 'query': query}).encode()
    req = urllib.request.Request('https://simbad.cds.unistra.fr/simbad/sim-tap/sync', data=body,
                                 headers={'User-Agent': 'AstroLearn educational prototype'})
    with urllib.request.urlopen(req, timeout=8) as response:
        raw = response.read(262145)
    if len(raw) > 262144:
        raise ValueError('SIMBAD response exceeded the size limit.')
    result = json.loads(raw)
    if not result.get('data'):
        raise ValueError('No SIMBAD record found for this catalog identifier.')
    values = dict(zip([column['name'] for column in result['metadata']], result['data'][0]))
    # Return a small fixed schema, not arbitrary remote HTML or executable content.
    return {key: values.get(key) for key in ('main_id', 'otype', 'sp_type', 'ra', 'dec', 'plx_value')}


def learning_router(prototype):
    router = APIRouter(prefix='/api/v1')

    @router.post('/sky-map')
    def sky(site: SiteRequest):
        return sky_points(site)

    def catalog_object(solve_id, object_id):
        job = prototype.require('solve', solve_id)
        if job['status'] != 'solved':
            raise HTTPException(409, 'Solve the field before requesting object details.')
        result = job.get('identification') or {}
        records = sum([result.get(k, []) for k in ('matched_stars', 'expected_stars', 'expected_objects')], [])
        item = next((item for item in records if item['id'] == object_id), None)
        if not item:
            raise HTTPException(404, 'Object is not in this solved field.')
        return item

    def details(solve_id, object_id, refresh=False):
        item = catalog_object(solve_id, object_id)
        key = hashlib.sha256(object_id.encode()).hexdigest()
        cached = prototype.store.get('object-details', key)
        error = None
        if refresh:
            try:
                record = fetch_simbad(object_id)
                cached = prototype.store.save('object-details', {'id': key, 'object_id': object_id,
                    'retrieved_at': datetime.now(timezone.utc).isoformat(),
                    'source': 'SIMBAD / CDS', 'source_url': 'https://simbad.cds.unistra.fr/simbad/', 'record': record})
            except (OSError, ValueError, KeyError, TypeError) as exc:
                error = 'Online enrichment unavailable. Local identification is unchanged.'
        return {'object': item, 'enrichment': cached, 'online_error': error,
                'message': 'Supplemental database information does not change the image-match evidence.'}

    @router.get('/solves/{solve_id}/object-details')
    def offline_details(solve_id: str, object_id: str = Query(max_length=100)):
        return details(solve_id, object_id)

    @router.post('/solves/{solve_id}/object-details')
    def refresh_details(solve_id: str, object_id: str = Query(max_length=100)):
        # The only runtime network request is an explicit user refresh.
        return details(solve_id, object_id, True)

    @router.post('/lightcurves', status_code=201)
    async def lightcurve(request: Request):
        data = bytearray()
        async for chunk in request.stream():
            data.extend(chunk)
            if len(data) > 1_000_000:
                raise HTTPException(413, 'CSV exceeds 1 MB.')
        try:
            record = parse_lightcurve(bytes(data))
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        return prototype.store.new('lightcurve', **record)

    @router.get('/lightcurves')
    def lightcurves():
        return prototype.store.list('lightcurve', limit=20)

    return router
