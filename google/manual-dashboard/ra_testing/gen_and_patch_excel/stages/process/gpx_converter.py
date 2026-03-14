# gpx_converter.py

import os
import json
import logging
import gpxpy
from geopy import distance
from datetime import datetime, timedelta
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

# -------------------------------------------------
# CONFIG
# -------------------------------------------------

# GPX_BASE = "gpx"
# JSON_BASE = "jsons"
# OUTPUT_BASE = "gpx_jsons"

IST_OFFSET = timedelta(hours=5, minutes=30)
TIME_FORMAT = "%Y-%m-%d %H:%M:%S"
TOLERANCE_MINUTES = 5


class GPXConversionError(Exception):
    """Raised when GPX conversion fails."""
    pass


# -------------------------------------------------
# TIME HELPERS
# -------------------------------------------------

def extract_json_timestamp(json_path: str) -> Optional[datetime]:
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        for section in ("assets", "anomalies"):
            for item in data.get(section, []):
                for key, value in item.items():
                    if "timestamp" in key.lower():
                        try:
                            return datetime.strptime(value, TIME_FORMAT)
                        except Exception:
                            continue
        return None
    except Exception as e:
        logger.exception(
            f"Failed extracting JSON timestamp | file={json_path}")
        raise


def extract_gpx_timestamp(gpx_path: str) -> Optional[datetime]:
    try:
        with open(gpx_path, "r", encoding="utf-8") as f:
            gpx = gpxpy.parse(f)

        for track in gpx.tracks:
            for segment in track.segments:
                for point in segment.points:
                    if point.time:
                        return point.time.replace(tzinfo=None)
        return None
    except Exception as e:
        logger.exception(f"Failed extracting GPX timestamp | file={gpx_path}")
        raise


def should_apply_ist(gpx_path: str, json_path: str) -> bool:
    gpx_ts = extract_gpx_timestamp(gpx_path)
    json_ts = extract_json_timestamp(json_path)

    if not gpx_ts or not json_ts:
        logger.warning("Timestamp comparison failed → IST not applied")
        return False

    diff_direct = abs((json_ts - gpx_ts).total_seconds()) / 60
    diff_ist = abs((json_ts - (gpx_ts + IST_OFFSET)).total_seconds()) / 60

    if diff_direct <= TOLERANCE_MINUTES:
        logger.info("IST not required (direct match within tolerance)")
        return False

    if diff_ist <= TOLERANCE_MINUTES:
        logger.info("IST offset applied")
        return True

    logger.warning(
        f"Timestamp mismatch > {TOLERANCE_MINUTES} min "
        f"(direct={diff_direct:.2f}m, ist={diff_ist:.2f}m) → IST not applied"
    )
    return False


# -------------------------------------------------
# CORE CONVERSION
# -------------------------------------------------

def convert_single_gpx(
    road_id: int,
    input_dir: str,
    output_dir: str,
    logger: logging.Logger
) -> str:

    gpx_path = os.path.join(input_dir, f"road_{road_id}.gpx")
    json_path = os.path.join(input_dir.replace(
        "gpx_raw", "json_raw"), f"road_{road_id}.json")
    output_path = os.path.join(output_dir, f"road_{road_id}.json")

    logger.info("Converting GPX | road_id=%s", road_id)

    if not os.path.exists(gpx_path):
        raise GPXConversionError(f"GPX missing for road {road_id}")

    if not os.path.exists(json_path):
        raise GPXConversionError(f"JSON missing for road {road_id}")

    apply_ist = should_apply_ist(gpx_path, json_path)

    ...
    # KEEP YOUR EXISTING LOGIC EXACTLY SAME
    ...

    try:
        with open(gpx_path, "r", encoding="utf-8") as f:
            gpx = gpxpy.parse(f)

        if not gpx.tracks:
            raise GPXConversionError(f"No GPX tracks in road {road_id}")

        all_gpx: Dict[str, Dict] = {}
        cumulative_distance = 0.0
        total_points = 0

        for track in gpx.tracks:
            for segment in track.segments:
                points = segment.points

                for i, point in enumerate(points):

                    if not point.time:
                        continue

                    total_points += 1

                    if i > 0:
                        p1 = (points[i - 1].latitude, points[i - 1].longitude)
                        p2 = (point.latitude, point.longitude)
                        cumulative_distance += distance.distance(p1, p2).meters

                    ts = point.time.replace(microsecond=0, tzinfo=None)

                    if apply_ist:
                        ts += IST_OFFSET

                    ts_str = ts.strftime(TIME_FORMAT)

                    all_gpx[ts_str] = {
                        "lat": point.latitude,
                        "lng": point.longitude,
                        "distanceInMeters": round(cumulative_distance, 2)
                    }

        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(all_gpx, f, indent=4)

        logger.info(
            f"GPX conversion completed | road_id={road_id} "
            f"| points={total_points} "
            f"| total_distance={round(cumulative_distance, 2)}m "
            f"| IST_applied={apply_ist}"
        )

        return output_path

    except Exception as e:
        logger.exception(f"GPX conversion failed | road_id={road_id}")
        raise GPXConversionError(
            f"Conversion failed for road {road_id}"
        ) from e


# -------------------------------------------------
# PIPELINE ENTRY
# -------------------------------------------------

def run(
    road_ids: List[int],
    input_dir: str,
    output_dir: str,
    logger: Optional[logging.Logger] = None
) -> List[str]:
    if logger is None:
        logger = logging.getLogger(__name__)

    logger.info(
        "Starting GPX conversion | roads=%s | input=%s | output=%s",
        road_ids,
        input_dir,
        output_dir
    )

    os.makedirs(output_dir, exist_ok=True)

    results = []

    for rid in road_ids:
        try:
            output = convert_single_gpx(
                int(rid),
                input_dir,
                output_dir,
                logger
            )
            results.append(output)

        except GPXConversionError as e:
            logger.error(str(e))
            continue

    logger.info(
        "Completed GPX conversion | total_success=%s",
        len(results)
    )

    return results
