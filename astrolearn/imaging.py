"""File-based camera provider and OpenCV source detection for the bench prototype."""

from io import BytesIO
import warnings

import cv2
import numpy as np
from astropy.io import fits
from PIL import Image, ImageOps, UnidentifiedImageError

MAX_BYTES = 20 * 1024 * 1024
MAX_PIXELS = 24_000_000


def decode_image(data: bytes) -> tuple[np.ndarray, bytes, str]:
    """Return RGB preview, normalized PNG bytes, and safe original extension.

    FITS originals are preserved separately for solving; only the display is
    percentile stretched. Raster images are decoded, not trusted by filename.
    """
    if not data or len(data) > MAX_BYTES:
        raise ValueError("Choose an image smaller than 20 MB.")
    if data.startswith(b"SIMPLE  ="):
        with fits.open(BytesIO(data), memmap=False) as hdus:
            array = next((h.data for h in hdus if h.data is not None), None)
            if array is None or array.ndim != 2 or array.size > MAX_PIXELS:
                raise ValueError("FITS upload must contain a 2D image up to 24 megapixels.")
            array = np.nan_to_num(array.astype(np.float32))
            low, high = np.percentile(array, [1, 99.8])
            gray = np.clip((array - low) * 255 / max(float(high - low), 1e-9), 0, 255).astype('uint8')
            rgb = cv2.cvtColor(gray, cv2.COLOR_GRAY2RGB)
            extension = ".fits"
    else:
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                with Image.open(BytesIO(data)) as image:
                    if image.format not in {"PNG", "JPEG", "TIFF"}:
                        raise ValueError("Use PNG, JPEG, TIFF, or a 2D FITS image.")
                    if image.width * image.height > MAX_PIXELS:
                        raise ValueError("Image must be at most 24 megapixels.")
                    rgb = np.asarray(ImageOps.exif_transpose(image).convert("RGB"))
                    # Re-encode raster inputs to a consistent solver orientation.
                    extension = ".png"
        except (UnidentifiedImageError, OSError, Image.DecompressionBombWarning,
                Image.DecompressionBombError) as exc:
            raise ValueError("The image could not be decoded.") from exc
    out = BytesIO()
    Image.fromarray(rgb).save(out, format="PNG")
    return rgb, out.getvalue(), extension


def detect_sources(rgb: np.ndarray) -> dict:
    """Detect compact bright candidates; this is not celestial identification."""
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    # Remove slowly varying background before estimating a robust noise level.
    background = cv2.GaussianBlur(gray, (0, 0), 8)
    residual = cv2.subtract(gray, background)
    median = float(np.median(residual))
    mad = float(np.median(np.abs(residual.astype(float) - median)))
    threshold = max(12, median + 5 * 1.4826 * mad)
    mask = (residual > threshold).astype('uint8')
    count, _, stats, centroids = cv2.connectedComponentsWithStats(mask)
    sources = []
    for index in range(1, count):
        x, y, width, height, area = stats[index]
        if 2 <= area <= 500 and max(width, height) <= 4 * max(1, min(width, height)):
            cx, cy = centroids[index]
            strength = float(residual[y:y+height, x:x+width].sum()) / np.sqrt(area)
            sources.append({"x": round(float(cx), 2), "y": round(float(cy), 2),
                            "area": int(area), "strength": round(strength, 2)})
    # A clipped bright star can have a flat core: background subtraction leaves
    # an annulus/spikes instead of its center. Measure saturated regions directly
    # from pixels, independently of any target or star catalog.
    saturated = (gray >= 250).astype('uint8')
    clipped_count, _, clipped_stats, clipped_centers = cv2.connectedComponentsWithStats(saturated)
    for index in range(1, clipped_count):
        _, _, width, height, area = clipped_stats[index]
        if 20 <= area <= max(10000, min(100000, gray.size*.01)) and max(width, height) <= 3 * max(1, min(width, height)):
            cx, cy = clipped_centers[index]
            if not any((s['x'] - cx) ** 2 + (s['y'] - cy) ** 2 <= 25 for s in sources):
                sources.insert(0, {'x': round(float(cx), 2), 'y': round(float(cy), 2),
                                   'area': int(area), 'strength': float(255*np.sqrt(area)),
                                   'profile': 'saturated candidate'})
    total = len(sources)
    # Keep the strongest candidates throughout the frame, rather than the
    # first 2,000 encountered from the top. Dense fields otherwise lost their
    # lower-half sources, including bright named stars.
    sources.sort(key=lambda s: s['strength'], reverse=True)
    sources = sources[:2000]
    return {"analysis_version": 3, "sources": sources, "count": len(sources),
            "total_candidates": total, "truncated": total > len(sources),
            "focus_score": round(float(cv2.Laplacian(gray, cv2.CV_64F).var()), 2),
            "mean_brightness": round(float(gray.mean()), 2),
            "width": int(rgb.shape[1]), "height": int(rgb.shape[0]),
            "warning": "Bright candidates are not confirmed stars. Plate solving verifies the field."}
