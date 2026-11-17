"""Offline target positions from catalog data, Astropy and optional local DE421."""

from datetime import datetime, timezone
import json
from pathlib import Path

from astropy import units as u
from astropy.coordinates import AltAz, EarthLocation, SkyCoord, get_body
from astropy.time import Time
from astropy.utils import iers
from pydantic import BaseModel, ConfigDict, Field, field_validator

# Never silently download Earth-orientation tables during an offline demonstration.
iers.conf.auto_download = False
iers.conf.auto_max_age = None
ROOT = Path(__file__).resolve().parent.parent
CATALOG_PATH = Path(__file__).with_name('catalog.json')


def catalog():
    return json.loads(CATALOG_PATH.read_text(encoding='utf-8'))


class SiteRequest(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)
    target_id: str
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    elevation_m: float = Field(default=0, ge=-500, le=9000)
    utc: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator('utc')
    @classmethod
    def timezone_required(cls, value):
        if value.tzinfo is None:
            raise ValueError('Time must include a UTC offset, for example 2026-11-02T18:00:00Z.')
        return value.astimezone(timezone.utc)


def position(request: SiteRequest):
    item = next((x for x in catalog() if x['id'] == request.target_id), None)
    if item is None:
        raise ValueError('Target not found in the local catalog.')
    site = EarthLocation.from_geodetic(request.longitude * u.deg, request.latitude * u.deg, request.elevation_m * u.m)
    instant = Time(request.utc)
    engine = 'Astropy catalog / bundled Earth-orientation data'
    if item['category'] in {'planet', 'natural satellite'}:
        ephemeris = ROOT / 'resources' / 'de421.bsp'
        if ephemeris.is_file():
            from skyfield.api import load, load_file, wgs84
            eph = load_file(str(ephemeris))
            try:
                ts = load.timescale(builtin=True)
                observer = eph['earth'] + wgs84.latlon(request.latitude, request.longitude, elevation_m=request.elevation_m)
                key = {'jupiter': 'jupiter barycenter', 'saturn': 'saturn barycenter',
                       'uranus': 'uranus barycenter', 'neptune': 'neptune barycenter'}.get(item['id'], item['id'])
                astrometric = observer.at(ts.from_datetime(request.utc)).observe(eph[key])
                apparent = astrometric.apparent()
                # Compare J2000 astrometric axes with ASTAP; apparent coordinates
                # are used only for the observer's altitude and azimuth.
                ra, dec, distance = astrometric.radec()
                coordinate = SkyCoord(ra=ra.hours * 15 * u.deg, dec=dec.degrees * u.deg, frame='icrs')
                altitude, azimuth, _ = apparent.altaz()
                alt, az = altitude.degrees, azimuth.degrees
                engine = 'Skyfield / local JPL DE421; no atmospheric refraction'
            finally:
                eph.close()
        else:
            body = get_body(item['id'], instant, site, ephemeris='builtin')
            coordinate = SkyCoord(ra=body.ra, dec=body.dec, frame='icrs')
            horizontal = body.transform_to(AltAz(obstime=instant, location=site, pressure=0*u.hPa))
            alt, az = horizontal.alt.deg, horizontal.az.deg
            # GCRS directions must not be compared to ICRS plate solutions as if identical.
            engine = 'Astropy built-in ephemeris (approximate fallback); GCRS direction'
    else:
        coordinate = SkyCoord(ra=item['ra_deg'] * u.deg, dec=item['dec_deg'] * u.deg, frame='icrs')
        horizontal = coordinate.transform_to(AltAz(obstime=instant, location=site, pressure=0*u.hPa))
        alt, az = horizontal.alt.deg, horizontal.az.deg
    return {'target': item, 'ra_deg': float(coordinate.ra.deg), 'dec_deg': float(coordinate.dec.deg),
            'altitude_deg': float(alt), 'azimuth_deg': float(az), 'visible': bool(alt > 0),
            'utc': request.utc.isoformat(), 'site': {'latitude': request.latitude, 'longitude': request.longitude, 'elevation_m': request.elevation_m},
            'engine': engine, 'coordinate_frame': 'GCRS' if 'GCRS' in engine else 'ICRS/J2000',
            'warning': 'Geometric horizon check only; buildings, clouds and equipment limits are not modeled. Catalog positions omit proper motion.'}
