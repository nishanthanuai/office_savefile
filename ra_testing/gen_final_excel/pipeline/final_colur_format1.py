# import xlsxwriter
# import requests


# def fetch_road_data(roadId):
#     api_url = f"https://ndd.roadathena.com/api/surveys/roads/{roadId}"
#     response = requests.get(
#         api_url, headers={"Security-Password": "admin@123"})

#     if response.status_code == 200:
#         json_response = response.json()
#         return json_response['road']
#     else:
#         print(
#             f"Failed to fetch data from API. Status code: {response.status_code}")
#         return None


# def run_final_colour_format(mcw_road_ids):

#     lhs_ranges = []
#     rhs_ranges = []

#     for road_id in mcw_road_ids:
#         road_data = fetch_road_data(str(road_id))
#         # print(f"ROAD_ID {road_id}: {road_data}")
#         if not road_data:
#             continue

#         # road_name = road_data.get("road_name", "").upper()
#         road_type = road_data.get("road_type", "").upper()

#         start = int(float(road_data["start_chainage"]))
#         end = int(float(road_data["end_chainage"]))

#         min_c = min(start, end)
#         max_c = max(start, end)

#         if "LHS" in road_type:
#             lhs_ranges.append((min_c, max_c))

#         elif "RHS" in road_type:
#             rhs_ranges.append((min_c, max_c))

#     if not lhs_ranges and not rhs_ranges:
#         print("No valid MCW roads found.")
#         return False

#     # Merge LHS
#     if lhs_ranges:
#         lhs_min = min(r[0] for r in lhs_ranges)
#         lhs_max = max(r[1] for r in lhs_ranges)
#     else:
#         lhs_min = lhs_max = None

#     # Merge RHS
#     if rhs_ranges:
#         rhs_min = min(r[0] for r in rhs_ranges)
#         rhs_max = max(r[1] for r in rhs_ranges)
#     else:
#         rhs_min = rhs_max = None

#     # Use global min/max for interval generation
#     all_mins = [x for x in [lhs_min, rhs_min] if x is not None]
#     all_maxs = [x for x in [lhs_max, rhs_max] if x is not None]

#     min_chainage = min(all_mins)
#     max_chainage = max(all_maxs)

#     intervals = []
#     # current_chainage = min_chainage
#     # next_chainage = (current_chainage // 1000 + 1) * 1000

#     # while current_chainage < max_chainage:
#     #     if next_chainage > max_chainage:
#     #         next_chainage = max_chainage
#     #     intervals.append(f"{current_chainage} - {next_chainage}")
#     #     current_chainage = next_chainage
#     #     next_chainage = (current_chainage // 1000 + 1) * 1000

#     current_chainage = min_chainage
#     next_chainage = (current_chainage // 500 + 1) * 500

#     while current_chainage < max_chainage:
#         if next_chainage > max_chainage:
#             next_chainage = max_chainage
#         intervals.append(f"{current_chainage} - {next_chainage}")
#         current_chainage = next_chainage
#         next_chainage = (current_chainage // 500 + 1) * 500

#     workbook = xlsxwriter.Workbook('Furniture_Chainage_Report.xlsx')
#     worksheet = workbook.add_worksheet()

#     bold_center = workbook.add_format(
#         {'bold': True, 'align': 'center', 'valign': 'vcenter', 'border': 1})
#     center_format = workbook.add_format(
#         {'align': 'center', 'valign': 'vcenter', 'border': 1})
#     title_format = workbook.add_format(
#         {'bold': True, 'align': 'center', 'font_size': 14, 'bg_color': '#DCE6F1'})
#     light_blue_format = workbook.add_format(
#         {'bg_color': '#ADD8E6', 'border': 1})
#     green_format = workbook.add_format({'bg_color': '#90EE90', 'border': 1})
#     yellow_format = workbook.add_format({'bg_color': '#FFFF99', 'border': 1})
#     orange_format = workbook.add_format({'bg_color': '#FFA500', 'border': 1})

#     worksheet.merge_range('A1:O1', 'Furniture Chainage Report', title_format)
#     worksheet.conditional_format(
#         'A2:O5', {'type': 'no_blanks', 'format': light_blue_format})
#     worksheet.merge_range('A2:A5', 'Chainage', bold_center)
#     worksheet.merge_range('B2:B5', 'Road Section', bold_center)
#     worksheet.merge_range('C2:D2', 'Chainage', bold_center)
#     worksheet.merge_range('C3:C5', 'From', center_format)
#     worksheet.merge_range('D3:D5', 'To', center_format)

#     worksheet.merge_range('E2:O2', 'Furniture Assets', bold_center)
#     worksheet.merge_range('E3:F4', 'CHEVRON', bold_center)
#     worksheet.merge_range('G3:H4', 'HAZARD', bold_center)
#     worksheet.merge_range('I3:J4', 'Cautionary Warning Signs', bold_center)
#     worksheet.merge_range('K3:L4', 'Prohibitory Mandatory Signs', bold_center)
#     worksheet.merge_range('M3:O4', 'Informatory Signs', bold_center)

#     worksheet.write('E5', 'Avenue/Left', center_format)
#     worksheet.write('F5', 'Median/Right', center_format)
#     worksheet.write('G5', 'Avenue/Left', center_format)
#     worksheet.write('H5', 'Median/Right', center_format)
#     worksheet.write('I5', 'Avenue/Left', center_format)
#     worksheet.write('J5', 'Median/Right', center_format)
#     # worksheet.write('K5', 'Overhead Signs', center_format)
#     worksheet.write('K5', 'Avenue/Left', center_format)
#     worksheet.write('L5', 'Median/Right', center_format)
#     # worksheet.write('N5', 'Overhead Signs', center_format)
#     worksheet.write('M5', 'Avenue/Left', center_format)
#     worksheet.write('N5', 'Median/Right', center_format)
#     worksheet.write('O5', 'Overhead Signs', center_format)

#     start_row = 6
#     for interval in intervals:
#         from_chainage, to_chainage = map(int, interval.split(" - "))
#         # Intersecting road LHS 1 (IRL1)

#         worksheet.write(
#             start_row, 0, f"{from_chainage} - {to_chainage}", green_format)
#         worksheet.write(start_row, 1, 'Main Carriage Way LHS', green_format)
#         # worksheet.write(start_row + 1, 1,'Elevated Main Carriage Way LHS', green_format)
#         worksheet.write(start_row + 1, 1,
#                         'Service Road LHS 1 (SRL1)', green_format)
#         worksheet.write(start_row + 2, 1,
#                         'Service Road LHS 2 (SRL2)', green_format)
#         worksheet.write(start_row + 3, 1,
#                         'Service Road LHS 3 (SRL3)', green_format)
#         worksheet.write(start_row + 4, 1,
#                         'Service Road LHS 4 (SRL4)', green_format)
#         worksheet.write(start_row + 5, 1,
#                         'Service Road LHS 5 (SRL5)', green_format)
#         worksheet.write(start_row + 6, 1,
#                         'Service Road LHS 6 (SRL6)', green_format)
#         worksheet.write(start_row + 7, 1,
#                         'Service Road LHS 7 (SRL7)', green_format)
#         worksheet.write(start_row + 8, 1,
#                         'Service Road LHS 8 (SRL8)', green_format)
#         worksheet.write(start_row + 9, 1,
#                         'Service Road LHS 9 (SRL9)', green_format)
#         worksheet.write(start_row + 10, 1,
#                         'Service Road LHS 10 (SRL10)', green_format)
#         worksheet.write(start_row + 11, 1,
#                         'Intersecting road LHS 1 (IRL1)', green_format)
#         worksheet.write(start_row + 12, 1,
#                         'Intersecting road LHS 2 (IRL2)', green_format)
#         worksheet.write(start_row + 13, 1,
#                         'Intersecting road LHS 3 (IRL3)', green_format)
#         worksheet.write(
#             start_row + 14, 1, 'Intersection (Right below structure) (I1)', green_format)
#         worksheet.write(
#             start_row + 15, 1, 'Intersection (Right below structure) (I2)', green_format)
#         # worksheet.write(start_row + 16,1, 'Intersection (Right below structure) (I3)', green_format)
#         # worksheet.write(start_row + 12,1, 'Intersection (Right below structure) (I4)', green_format)
#         # worksheet.write(start_row + 13,1, 'Intersection (Right below structure) (I5)', green_format)

#         start_row += 16

#         worksheet.write(
#             start_row, 0, f"{to_chainage} - {from_chainage}", yellow_format)
#         worksheet.write(start_row, 1, 'Main Carriage Way RHS', yellow_format)
#         # worksheet.write(start_row + 1, 1,'Elevated Main Carriage Way RHS', yellow_format)
#         worksheet.write(start_row + 1, 1,
#                         'Service Road RHS 1 (SRR1)', yellow_format)
#         worksheet.write(start_row + 2, 1,
#                         'Service Road RHS 2 (SRR2)', yellow_format)
#         worksheet.write(start_row + 3, 1,
#                         'Service Road RHS 3 (SRR3)', yellow_format)
#         worksheet.write(start_row + 4, 1,
#                         'Service Road RHS 4 (SRR4)', yellow_format)
#         worksheet.write(start_row + 5, 1,
#                         'Service Road RHS 5 (SRR5)', yellow_format)
#         worksheet.write(start_row + 6, 1,
#                         'Service Road RHS 6 (SRR6)', yellow_format)
#         worksheet.write(start_row + 7, 1,
#                         'Service Road RHS 7 (SRR7)', yellow_format)
#         worksheet.write(start_row + 8, 1,
#                         'Service Road RHS 8 (SRR8)', yellow_format)
#         worksheet.write(start_row + 9, 1,
#                         'Service Road RHS 9 (SRR9)', yellow_format)

#         worksheet.write(start_row + 10, 1,
#                         'Intersecting road RHS 1 (IRR1)', yellow_format)
#         worksheet.write(start_row + 11, 1,
#                         'Intersecting road RHS 2 (IRR2)', yellow_format)
#         worksheet.write(start_row + 12, 1,
#                         'Intersecting road RHS 3 (IRR3)', yellow_format)

#         start_row += 13
#         # worksheet.merge_range(start_row, 0, start_row, 16, "", orange_format)
#         start_row += 1

#     worksheet.set_column('A:A', 20)
#     worksheet.set_column('B:B', 40)
#     worksheet.set_column('C:D', 20)
#     worksheet.set_column('E:Q', 25)
#     workbook.close()
#     return True


# # ----------------------------------------
# # Standalone Execution Support
# # ----------------------------------------
# if __name__ == "__main__":

#     print("\n===== FINAL COLOUR FORMAT (Standalone Mode) =====\n")

#     road_input = input(
#         "Enter MCW road ID(s) (comma separated): "
#     ).strip()

#     mcw_ids = [
#         int(x.strip())
#         for x in road_input.split(",")
#         if x.strip().isdigit()
#     ]

#     if not mcw_ids:
#         print("No valid road IDs entered. Exiting.")
#     else:
#         success = run_final_colour_format(mcw_ids)

#         if success:
#             print("\n✔ Furniture_Chainage_Report.xlsx generated successfully.\n")
#         else:
#             print("\n❌ Failed to generate report.\n")
import xlsxwriter
import requests
import logging
import os

# from inspect_survey import ROAD_API_PASSWORD
# import logging
logger = logging.getLogger(__name__)

# logger = logging.getLogger(__name__)

ROAD_API_PASSWORD = os.environ.get("ROAD_API_PASSWORD")

if not ROAD_API_PASSWORD:
    raise RuntimeError(
        "Environment variable 'ROAD_API_PASSWORD' not set"
    )


def fetch_road_data(roadId):
    logger.debug(f"fetch_road_data called with roadId={roadId}")

    api_url = f"https://ndd.roadathena.com/api/surveys/roads/{roadId}"
    logger.debug(f"Requesting URL: {api_url}")

    response = requests.get(
        api_url,
        headers={"Security-Password": ROAD_API_PASSWORD}
    )

    if response.status_code == 200:
        json_response = response.json()
        logger.debug(f"Received road data for {roadId}: {json_response}")
        return json_response['road']

    logger.warning(
        f"Failed to fetch road data for {roadId}, status={response.status_code}")
    return None


# ---------------------------------------------------------
# NEW FUNCTION
# Automatically detect MCW road IDs from survey
# ---------------------------------------------------------
def fetch_MCW_road_ids(survey_id):

    logger.info(f"Detecting MCW roads for survey {survey_id}")

    survey_url = f"https://ndd.roadathena.com/api/surveys/{survey_id}"

    resp = requests.get(
        survey_url,
        headers={"Security-Password": ROAD_API_PASSWORD}
    )

    if resp.status_code != 200:
        logger.error(f"Survey API failed: {resp.status_code}")
        return []

    data = resp.json()
    roads = data.get("roads", [])

    logger.info(f"Survey contains {len(roads)} roads")

    mcw_ids = []

    for road in roads:

        road_id = road.get("id")

        road_url = f"https://ndd.roadathena.com/api/surveys/roads/{road_id}"

        road_resp = requests.get(
            road_url,
            headers={"Security-Password": ROAD_API_PASSWORD}
        )

        if road_resp.status_code != 200:
            logger.warning(f"Failed road API for {road_id}")
            continue

        road_data = road_resp.json().get("road", {})
        road_type = road_data.get("road_type", "").upper()

        logger.info(f"road_id={road_id} | type={road_type}")

        if "MCW" in road_type:
            mcw_ids.append(road_id)

    logger.info(f"Detected MCW roads: {mcw_ids}")

    return mcw_ids


# ---------------------------------------------------------
# ORIGINAL LOGIC (UNCHANGED)
# ---------------------------------------------------------
def run_final_colour_format(mcw_road_ids, output_dir, logger):
    logger.info(
        f"run_final_colour_format called with road ids: {mcw_road_ids}")

    lhs_ranges = []
    rhs_ranges = []

    for road_id in mcw_road_ids:

        road_data = fetch_road_data(str(road_id))
        logger.debug(f"road_data for {road_id}: {road_data}")

        if not road_data:
            logger.warning(f"No data for road {road_id}, skipping")
            continue

        road_type = road_data.get("road_type", "").upper()

        start = int(float(road_data["start_chainage"]))
        end = int(float(road_data["end_chainage"]))

        min_c = min(start, end)
        max_c = max(start, end)

        logger.debug(
            f"road {road_id}: type={road_type}, range=({min_c},{max_c})")

        if "LHS" in road_type:
            lhs_ranges.append((min_c, max_c))

        elif "RHS" in road_type:
            rhs_ranges.append((min_c, max_c))

    if not lhs_ranges and not rhs_ranges:
        logger.warning("No valid MCW roads found.")
        return False
    logger.debug(f"lhs_ranges={lhs_ranges}, rhs_ranges={rhs_ranges}")

    if lhs_ranges:
        lhs_min = min(r[0] for r in lhs_ranges)
        lhs_max = max(r[1] for r in lhs_ranges)
    else:
        lhs_min = lhs_max = None

    if rhs_ranges:
        rhs_min = min(r[0] for r in rhs_ranges)
        rhs_max = max(r[1] for r in rhs_ranges)
    else:
        rhs_min = rhs_max = None

    all_mins = [x for x in [lhs_min, rhs_min] if x is not None]
    all_maxs = [x for x in [lhs_max, rhs_max] if x is not None]

    min_chainage = min(all_mins)
    max_chainage = max(all_maxs)

    intervals = []

    current_chainage = min_chainage
    next_chainage = (current_chainage // 500 + 1) * 500

    while current_chainage < max_chainage:

        if next_chainage > max_chainage:
            next_chainage = max_chainage

        intervals.append(f"{current_chainage} - {next_chainage}")
        logger.debug(f"Added interval {current_chainage} - {next_chainage}")

        current_chainage = next_chainage
        next_chainage = (current_chainage // 500 + 1) * 500

    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, 'Furniture_Chainage_Report.xlsx')
    workbook = xlsxwriter.Workbook(output_path)
    worksheet = workbook.add_worksheet()
    logger.info(f"Creating workbook with {len(intervals)} intervals")

    bold_center = workbook.add_format(
        {'bold': True, 'align': 'center', 'valign': 'vcenter', 'border': 1})
    center_format = workbook.add_format(
        {'align': 'center', 'valign': 'vcenter', 'border': 1})
    title_format = workbook.add_format(
        {'bold': True, 'align': 'center', 'font_size': 14, 'bg_color': '#DCE6F1'})
    light_blue_format = workbook.add_format(
        {'bg_color': '#ADD8E6', 'border': 1})
    green_format = workbook.add_format({'bg_color': '#90EE90', 'border': 1})
    yellow_format = workbook.add_format({'bg_color': '#FFFF99', 'border': 1})
    orange_format = workbook.add_format({'bg_color': '#FFA500', 'border': 1})

    worksheet.merge_range('A1:O1', 'Furniture Chainage Report', title_format)

    worksheet.conditional_format(
        'A2:O5', {'type': 'no_blanks', 'format': light_blue_format})

    worksheet.merge_range('A2:A5', 'Chainage', bold_center)
    worksheet.merge_range('B2:B5', 'Road Section', bold_center)

    worksheet.merge_range('C2:D2', 'Chainage', bold_center)
    worksheet.merge_range('C3:C5', 'From', center_format)
    worksheet.merge_range('D3:D5', 'To', center_format)

    worksheet.merge_range('E2:O2', 'Furniture Assets', bold_center)

    worksheet.merge_range('E3:F4', 'CHEVRON', bold_center)
    worksheet.merge_range('G3:H4', 'HAZARD', bold_center)
    worksheet.merge_range('I3:J4', 'Cautionary Warning Signs', bold_center)
    worksheet.merge_range('K3:L4', 'Prohibitory Mandatory Signs', bold_center)
    worksheet.merge_range('M3:O4', 'Informatory Signs', bold_center)

    worksheet.write('E5', 'Avenue/Left', center_format)
    worksheet.write('F5', 'Median/Right', center_format)
    worksheet.write('G5', 'Avenue/Left', center_format)
    worksheet.write('H5', 'Median/Right', center_format)
    worksheet.write('I5', 'Avenue/Left', center_format)
    worksheet.write('J5', 'Median/Right', center_format)
    worksheet.write('K5', 'Avenue/Left', center_format)
    worksheet.write('L5', 'Median/Right', center_format)
    worksheet.write('M5', 'Avenue/Left', center_format)
    worksheet.write('N5', 'Median/Right', center_format)
    worksheet.write('O5', 'Overhead Signs', center_format)

    start_row = 6

    for interval in intervals:

        from_chainage, to_chainage = map(int, interval.split(" - "))

        worksheet.write(
            start_row, 0, f"{from_chainage} - {to_chainage}", green_format)

        worksheet.write(start_row, 1, 'Main Carriage Way LHS', green_format)

        worksheet.write(start_row + 1, 1,
                        'Service Road LHS 1 (SRL1)', green_format)
        worksheet.write(start_row + 2, 1,
                        'Service Road LHS 2 (SRL2)', green_format)
        worksheet.write(start_row + 3, 1,
                        'Service Road LHS 3 (SRL3)', green_format)
        worksheet.write(start_row + 4, 1,
                        'Service Road LHS 4 (SRL4)', green_format)
        worksheet.write(start_row + 5, 1,
                        'Service Road LHS 5 (SRL5)', green_format)
        worksheet.write(start_row + 6, 1,
                        'Service Road LHS 6 (SRL6)', green_format)
        worksheet.write(start_row + 7, 1,
                        'Service Road LHS 7 (SRL7)', green_format)
        worksheet.write(start_row + 8, 1,
                        'Service Road LHS 8 (SRL8)', green_format)
        worksheet.write(start_row + 9, 1,
                        'Service Road LHS 9 (SRL9)', green_format)
        worksheet.write(start_row + 10, 1,
                        'Service Road LHS 10 (SRL10)', green_format)
        worksheet.write(start_row + 11, 1,
                        'Intersecting road LHS 1 (IRL1)', green_format)
        worksheet.write(start_row + 12, 1,
                        'Intersecting road LHS 2 (IRL2)', green_format)
        worksheet.write(start_row + 13, 1,
                        'Intersecting road LHS 3 (IRL3)', green_format)
        worksheet.write(
            start_row + 14, 1, 'Intersection (Right below structure) (I1)', green_format)
        worksheet.write(
            start_row + 15, 1, 'Intersection (Right below structure) (I2)', green_format)

        start_row += 16

        worksheet.write(
            start_row, 0, f"{to_chainage} - {from_chainage}", yellow_format)

        worksheet.write(start_row, 1, 'Main Carriage Way RHS', yellow_format)

        worksheet.write(start_row + 1, 1,
                        'Service Road RHS 1 (SRR1)', yellow_format)
        worksheet.write(start_row + 2, 1,
                        'Service Road RHS 2 (SRR2)', yellow_format)
        worksheet.write(start_row + 3, 1,
                        'Service Road RHS 3 (SRR3)', yellow_format)
        worksheet.write(start_row + 4, 1,
                        'Service Road RHS 4 (SRR4)', yellow_format)
        worksheet.write(start_row + 5, 1,
                        'Service Road RHS 5 (SRR5)', yellow_format)
        worksheet.write(start_row + 6, 1,
                        'Service Road RHS 6 (SRR6)', yellow_format)
        worksheet.write(start_row + 7, 1,
                        'Service Road RHS 7 (SRR7)', yellow_format)
        worksheet.write(start_row + 8, 1,
                        'Service Road RHS 8 (SRR8)', yellow_format)
        worksheet.write(start_row + 9, 1,
                        'Service Road RHS 9 (SRR9)', yellow_format)

        worksheet.write(start_row + 10, 1,
                        'Intersecting road RHS 1 (IRR1)', yellow_format)
        worksheet.write(start_row + 11, 1,
                        'Intersecting road RHS 2 (IRR2)', yellow_format)
        worksheet.write(start_row + 12, 1,
                        'Intersecting road RHS 3 (IRR3)', yellow_format)

        start_row += 13
        start_row += 1

    worksheet.set_column('A:A', 20)
    worksheet.set_column('B:B', 40)
    worksheet.set_column('C:D', 20)
    worksheet.set_column('E:Q', 25)

    workbook.close()

    logger.info("Furniture_Chainage_Report.xlsx generated")

    return True


# ---------------------------------------------------------
# PIPELINE ENTRYPOINT
# ---------------------------------------------------------
def run(survey_id, output_dir, logger):

    logger.info("Running final_colour_format module")

    mcw_ids = fetch_MCW_road_ids(survey_id)

    if not mcw_ids:
        logger.error("No MCW roads found for survey")
        return False

    return run_final_colour_format(mcw_ids, output_dir, logger)

