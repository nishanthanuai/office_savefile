import gpxpyimport
import geopy.distance
import os
import pandas as pd

def parse_gpx_with_distance(gpx_file, start_distance=0, reverse=False):
    gpx = gpxpy.parse(open(gpx_file))
    points = []
    total_distance = start_distance  
    last_point = None
    
    # Loop through all points in the track
    for track in gpx.tracks:
        for segment in track.segments:
            for point in segment.points:
                if last_point:
                    # Calculate distance between last point and current point
                    dist = geopy.distance.distance((last_point.latitude, last_point.longitude), 
                                                   (point.latitude, point.longitude)).meters
                    if reverse:
                        total_distance -= dist  
                    else:
                        total_distance += dist  
                        
                points.append((point.latitude, point.longitude, total_distance))
                last_point = point

    return points

# Function to find nearest distance and lat/lon in main GPX for a given lat/lon
def find_nearest_point(main_gpx_points, lat, lon):
    nearest_distance = None
    nearest_lat = None
    nearest_lon = None
    min_dist = float('inf')

    for point in main_gpx_points:
        main_lat, main_lon, main_distance = point
        dist = geopy.distance.distance((lat, lon), (main_lat, main_lon)).meters
        if dist < min_dist:
            min_dist = dist
            nearest_distance = main_distance
            nearest_lat = main_lat
            nearest_lon = main_lon

    return nearest_distance, nearest_lat, nearest_lon

# Parse other GPX file and find its start/end distances, and lat/lon nearest in main GPX
def get_other_gpx_start_end_distance(other_gpx_file, main_gpx_points, reverse=False):
    other_gpx_points = parse_gpx_with_distance(other_gpx_file, reverse=reverse)
    
    # Get start and end coordinates from the other GPX file
    start_lat, start_lon, _ = other_gpx_points[0]
    end_lat, end_lon, _ = other_gpx_points[-1]
    
    # Find nearest distance and lat/lon in the main GPX file for start and end
    start_distance, main_start_lat, main_start_lon = find_nearest_point(main_gpx_points, start_lat, start_lon)
    end_distance, main_end_lat, main_end_lon = find_nearest_point(main_gpx_points, end_lat, end_lon)
    
    return {
        'start_distance': start_distance,
        'end_distance': end_distance,
        'start_lat': start_lat,
        'start_lon': start_lon,
        'end_lat': end_lat,
        'end_lon': end_lon,
        'main_start_lat': main_start_lat,
        'main_start_lon': main_start_lon,
        'main_end_lat': main_end_lat,
        'main_end_lon': main_end_lon
    }

# Get all GPX files from the specified folder
def get_gpx_files(folder_path):
    return [os.path.join(folder_path, f) for f in os.listdir(folder_path) if f.endswith('.gpx')]

# Save data to an Excel file
def save_to_excel(gpx_data, output_file):
    # Create a DataFrame with the specified columns
    df = pd.DataFrame(gpx_data, columns=[
        'Name of GPX File', 
        'Start Distance (m)', 'End Distance (m)', 
        'Start Lat', 'Start Lon', 'End Lat', 'End Lon',
        'Main Start Lat (Nearest)', 'Main Start Lon (Nearest)',
        'Main End Lat (Nearest)', 'Main End Lon (Nearest)'
    ])
    
    # Add a column for the distance between start and end points
    df['Distance (m)'] = df['End Distance (m)'] - df['Start Distance (m)']
    
    # Save the DataFrame to an Excel file
    df.to_excel(output_file, index=False)
    
# Main processing function
def process_gpx_files(folder_path, main_gpx_file, manual_start_distance, manual_end_distance, output_file):
    # Check if reverse processing is needed (start distance is greater than end distance)
    reverse = manual_start_distance > manual_end_distance
    
    # Parse the main GPX file with the manually provided starting distance, in reverse if needed
    main_gpx_points = parse_gpx_with_distance(main_gpx_file, start_distance=manual_start_distance, reverse=reverse)
    
    # Get list of other GPX files
    gpx_files = get_gpx_files(folder_path)
    gpx_data = []

    # Process each GPX file and find the start/end distances and lat/lon relative to the main GPX
    for gpx_file in gpx_files:
        result = get_other_gpx_start_end_distance(gpx_file, main_gpx_points, reverse=reverse)
        gpx_data.append([
            os.path.basename(gpx_file),
            result['start_distance'], result['end_distance'],
            result['start_lat'], result['start_lon'],
            result['end_lat'], result['end_lon'],
            result['main_start_lat'], result['main_start_lon'],
            result['main_end_lat'], result['main_end_lon']
        ])

    # Save the results to an Excel file
    save_to_excel(gpx_data, output_file)
    print(f"Data saved to {output_file}")

# Define paths and distances
folder_path = 'gpxRHS'  
main_gpx_file = 'C:\\Users\\manav\\Desktop\\chainage_wise_SR\\MCW\\RHS\\Porbandar-Dwarka (Package VIII) from km. 379.100 to km. 496.848 RHS.gpx'  
# manual_start_distance = 379100
# manual_end_distance = 496848

manual_start_distance = 496848
manual_end_distance = 379100

output_file = 'C:\\Users\\manav\\Desktop\\chainage_wise_SR\\output\\Porbandar-Dwarka (Package VIII) from km. 379.100 to km. 496.848 RHS.xlsx'

# Process the GPX files
process_gpx_files(folder_path, main_gpx_file, manual_start_distance, manual_end_distance, output_file)
