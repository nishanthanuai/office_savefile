# utils/road_resolver.py
import os


def resolve_road_file(root_folder, road_id):
    """
    Finds road_<road_id>.json inside mcw or service folder
    """
    for sub in ("mcw", "service"):
        path = os.path.join(root_folder, sub, f"road_{road_id}.json")
        if os.path.exists(path):
            return path, sub
    return None, None
