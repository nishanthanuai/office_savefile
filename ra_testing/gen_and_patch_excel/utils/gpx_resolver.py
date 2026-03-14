import os


def resolve_gpx_file(root_folder, road_id):
    """
    Finds GPX JSON for a road inside mcw or service folder
    """
    for sub in ("mcw", "service"):
        path = os.path.join(root_folder, sub, f"gpx_road_{road_id}.json")
        if os.path.exists(path):
            return path, sub
    return None, None
