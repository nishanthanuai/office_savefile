import gpxpy
from geopy import distance
from datetime import datetime, timedelta
import json
import math


class GPXProcessor:
    def __init__(self, fixed_offset_hours=5, fixed_offset_minutes=30):
        self.fixed_offset = timedelta(hours=fixed_offset_hours, minutes=fixed_offset_minutes)

    def convert_to_utc(self, time_str):
        time_obj = datetime.strptime(time_str, "%m/%d/%Y %H:%M:%S")
        time_utc = time_obj - self.fixed_offset
        return time_utc

    def convert_to_ist(self, time_str):
        time_str = time_str.split('+')[0]
        time_obj = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
        time_ist = time_obj + self.fixed_offset
        return time_ist

    def parse_gpx(self, gpx_file_name, save_path=None):
        all_gpx = {}
        gpx = gpxpy.parse(open(gpx_file_name, 'r'))

        gpx_data = {"chk_pnts": {}}
        dis = 0
        dis_in_meters = 0
        start_point = [0, 0]
        dis_3d = 0

        for track in gpx.tracks:
            for segment in track.segments:
                for i, point in enumerate(segment.points):
                    if i == 0:
                        start_point[0], start_point[1] = point.latitude, point.longitude

                    try:
                        nxt = segment.points[i + 1]
                        print("next" , nxt)
                        current_point = (point.latitude, point.longitude)
                        print("current", current_point)
                        next_point = (nxt.latitude, nxt.longitude)
                        dis += distance.distance(current_point, next_point).km
                        dis_bt_points = distance.distance(current_point, next_point).m
                        dis_in_meters += dis_bt_points
                        # elevation_diff = abs(nxt.elevation - point.elevation)
                        # dis_3d += math.sqrt(elevation_diff**2 + dis_bt_points**2)
                    except IndexError:
                        print('File extraction completed.')
                        break
                    except Exception as e:
                        print(f"Error at point {i}/{len(segment.points)}: {e}")
                        continue

                    point_time_str = str(point.time.replace(microsecond=0))
                    ist_time_str = str(self.convert_to_ist(point_time_str))

                    gpx_data['chk_pnts'][point_time_str] = {
                        "lat": point.latitude,
                        "lng": point.longitude,
                        "distanceInMeters": dis_in_meters,
                    }

                    all_gpx[ist_time_str] = {
                        "lat": point.latitude,
                        "lng": point.longitude,
                        "distanceInMeters": dis_in_meters,
                    }

        gpx_data['dist_covered'] = dis_in_meters
        print("Extraction ended.")

        if save_path:
            with open(save_path, 'w') as json_file:
                json.dump(all_gpx, json_file, indent=4)
            print(f"GPX data saved to {save_path}")

        

# Example usage
if __name__ == "__main__":
    gpx_processor = GPXProcessor()
    gpx_file_path = "example.gpx"
    save_file_path = "output.json"

    result = gpx_processor.parse_gpx(gpx_file_path, save_file_path)
    print("GPX processing completed!")
