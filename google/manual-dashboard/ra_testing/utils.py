import gpxpy
import geopy.distance
import os
import pandas as pd

import gpxpy
import geopy.distance

def parse_gpx_with_distance(gpx_file, start_distance=0, reverse=False):
    gpx = gpxpy.parse(open(gpx_file))
    points = []
    total_distance = float(start_distance)  # Ensure it's a float
    last_point = None
    
    # Loop through all points in the track
    for track in gpx.tracks:
        for segment in track.segments:
            for point in segment.points:
                if last_point:
                    # Calculate distance between last point and current point
                    dist = geopy.distance.distance(
                        (last_point.latitude, last_point.longitude), 
                        (point.latitude, point.longitude)
                    ).meters
                    if reverse:
                        total_distance -= float(dist)  # Ensure dist is float
                    else:
                        total_distance += float(dist)  # Ensure dist is float
                        
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
def get_other_gpx_start_end_distance(other_gpx_file, main_gpx_points, road_type , reverse=False):
    other_gpx_points = parse_gpx_with_distance(other_gpx_file, reverse=reverse)
    
    # Get start and end coordinates from the other GPX file
    start_lat, start_lon, _ = other_gpx_points[0]
    end_lat, end_lon, _ = other_gpx_points[-1]
    
    # Find nearest distance and lat/lon in the main GPX file for start and end
    start_distance, main_start_lat, main_start_lon = find_nearest_point(main_gpx_points, start_lat, start_lon)
    end_distance, main_end_lat, main_end_lon = find_nearest_point(main_gpx_points, end_lat, end_lon)

    print("I AM HERE WITH THE ROAD")
    print("the MCW road type is" , road_type)

    road_type = road_type.replace(" ","")
    print("road_type after replace is",road_type)
    # if road_type == 'MCWRHS':
    #     print(" I AM HERE TO CHANGE")
    #     if(start_distance < end_distance):
    #         print("i need to change it as type is rhs")
    #         c=start_distance
    #         start_distance = end_distance
    #         end_distance = c

    # if road_type == 'MCWLHS':
    #     print("i am here to change ")
    #     if(start_distance > end_distance):
    #         print("i need to change it as type is lhs")
    #         c=start_distance
    #         start_distance = end_distance
    #         end_distance = c


    return {
        'start_distance': int(start_distance),
        'end_distance': int(end_distance),
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
def process_gpx_files(folder_path, road_type, main_gpx_file, manual_start_distance, manual_end_distance, output_file ):
    print("Road_Type in process gpx is  " , road_type)
    # Check if reverse processing is needed (start distance is greater than end distance)

    manual_start_distance = float(manual_start_distance) if manual_start_distance is not None else 0.0
    manual_end_distance = float(manual_end_distance) if manual_end_distance is not None else 0.0

    reverse = manual_start_distance > manual_end_distance

    
    # Parse the main GPX file with the manually provided starting distance, in reverse if needed
    main_gpx_points = parse_gpx_with_distance(main_gpx_file, start_distance=manual_start_distance, reverse=reverse)
    
    # Get list of other GPX files
    gpx_files =  get_gpx_files(folder_path)
    gpx_data = []

    # Process each GPX file and find the start/end distances and lat/lon relative to the main GPX
    for gpx_file in gpx_files:
        result = get_other_gpx_start_end_distance(gpx_file, main_gpx_points, road_type ,reverse=reverse)

        # Print Start and End Chainage
        print(f"File: {os.path.basename(gpx_file)}")
        print(f"Start Distance (Chainage): {result['start_distance']} meters")
        print(f"End Distance (Chainage): {result['end_distance']} meters\n")

        gpx_data.append([
            os.path.basename(gpx_file),
            result['start_distance'], result['end_distance'],
            result['start_lat'], result['start_lon'],
            result['end_lat'], result['end_lon'],
            result['main_start_lat'], result['main_start_lon'],
            result['main_end_lat'], result['main_end_lon']
        ])


    save_to_excel(gpx_data, output_file)
    print(f"Data saved to {output_file}")



# folder_path = 'C:\\Users\\manav\\Desktop\\excel_folder_final_maker\\Chainage_finding_report\\gpx'  
# main_gpx_file = 'C:\\Users\\manav\\Desktop\\excel_folder_final_maker\\Chainage_finding_report\\MCW\\PalanpurRadhanpur_LHS.gpx' 
# manual_start_distance = 21000
# manual_end_distance = 48000

# output_file = 'C:\\Users\\manav\\Desktop\\excel_folder_final_maker\\Chainage_finding_report\\output\\SL.xlsx'

# # Process the GPX files
# process_gpx_files(folder_path, main_gpx_file, manual_start_distance, manual_end_distance, output_file)