import xlsxwriter
import requests

def fetch_road_data(roadId):
    api_url = f"https://ndd.roadathena.com/api/surveys/roads/{roadId}"
    response = requests.get(api_url)
    if response.status_code == 200:
        json_response = response.json()
        return json_response['road']
    else:
        print(f"Failed to fetch data from API. Status code: {response.status_code}")
        return None
road_data = fetch_road_data(roadId="93")

if road_data:
    start_chainage = int(float(road_data["start_chainage"]))
    end_chainage = int(float(road_data["end_chainage"]))
    min_chainage = min(start_chainage, end_chainage)
    max_chainage = max(start_chainage, end_chainage)
    intervals = []
    current_chainage = min_chainage

    next_chainage = (current_chainage // 500 + 1) * 500
    while current_chainage < max_chainage:
        if next_chainage > max_chainage:
            next_chainage = max_chainage
        intervals.append(f"{current_chainage} - {next_chainage}")
        current_chainage = next_chainage
        next_chainage = (current_chainage // 500 + 1) * 500

    workbook = xlsxwriter.Workbook('Furniture_Chainage_Report.xlsx')

    worksheet = workbook.add_worksheet()

    bold_center = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'border': 1})
    center_format = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'border': 1})
    title_format = workbook.add_format({'bold': True, 'align': 'center', 'font_size': 14, 'bg_color': '#DCE6F1'})
    worksheet.merge_range('A1:Q1', 'Furniture Chainage Report', title_format)
    worksheet.merge_range('A2:A5', 'Chainage', bold_center)
    worksheet.merge_range('B2:B5', 'Road Section', bold_center)
    worksheet.merge_range('C2:D2', 'Chainage', bold_center)
    worksheet.merge_range('C3:C5', 'From', center_format)
    worksheet.merge_range('D3:D5', 'To', center_format)
    worksheet.merge_range('E2:Q2', 'Furniture Assets', bold_center)
    worksheet.merge_range('E3:F4', 'CHEVRON', bold_center)
    worksheet.merge_range('G3:H4', 'HAZARD', bold_center)
    worksheet.merge_range('I3:K4', 'Cautionary Warning Signs', bold_center)
    worksheet.merge_range('L3:N4', 'Prohibitory Mandatory Signs', bold_center)
    worksheet.merge_range('O3:Q4', 'Informatory Signs', bold_center)
    worksheet.write('E5', 'Avenue/Left', center_format)
    worksheet.write('F5', 'Median/Right', center_format)
    worksheet.write('G5', 'Avenue/Left', center_format)
    worksheet.write('H5', 'Median/Right', center_format)
    worksheet.write('I5', 'Avenue/Left', center_format)
    worksheet.write('J5', 'Median/Right', center_format)
    worksheet.write('K5', 'Overhead Signs', center_format)
    worksheet.write('L5', 'Avenue/Left', center_format)
    worksheet.write('M5', 'Median/Right', center_format)
    worksheet.write('N5', 'Overhead Signs', center_format)
    worksheet.write('O5', 'Avenue/Left', center_format)
    worksheet.write('P5', 'Median/Right', center_format)
    worksheet.write('Q5', 'Overhead Signs', center_format)
    start_row = 6

    for interval in intervals:

        from_chainage, to_chainage = map(int, interval.split(" - "))
        worksheet.write(start_row, 0, f"{from_chainage} - {to_chainage}", center_format)
        worksheet.write(start_row, 1, 'Main Carriage Way LHS', center_format)
        worksheet.write(start_row + 1, 1, 'Service Road LHS 1 (SRL1)', center_format)
        worksheet.write(start_row + 2, 1, 'Service Road LHS 2 (SRL2)', center_format)
        worksheet.write(start_row + 3, 1, 'Intersecting road LHS 1 (IRL1)', center_format)
        worksheet.write(start_row + 4, 1, 'Intersecting road LHS 2 (IRL2)', center_format)
        worksheet.write(start_row + 5, 1, 'Intersection (Right below structure) (I1)', center_format)
        worksheet.write(start_row + 6, 1, 'Intersection (Right below structure) (I2)', center_format)

        start_row += 7  

        worksheet.write(start_row, 0, f"{to_chainage} - {from_chainage}", center_format)
        worksheet.write(start_row, 1, 'Main Carriage Way RHS', center_format)
        worksheet.write(start_row + 1, 1, 'Service Road RHS 1 (SRR1)', center_format)
        worksheet.write(start_row + 2, 1, 'Service Road RHS 2 (SRR2)', center_format)
        worksheet.write(start_row + 3, 1, 'Intersection RHS 1 (IRR1)', center_format)
        worksheet.write(start_row + 4, 1, 'Intersection RHS 2 (IRR2)', center_format)

        start_row += 6  

    worksheet.set_column('A:A', 20)
    worksheet.set_column('B:B', 40)
    worksheet.set_column('C:D', 20)
    worksheet.set_column('E:Q', 25)
    workbook.close()

else:

    print("Failed to generate report due to missing road data.")
