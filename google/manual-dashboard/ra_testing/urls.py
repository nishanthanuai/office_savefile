# ra_testing/urls.py
from django.urls import path
from django.urls import path, include
from .views import *


excelmerge_patterns = (
    [
        path("", merge_excel, name="merge_excel"),
        path(
            "get-files/<str:folder_name>/",
            get_files_in_folder,
            name="get_files_in_folder",
        ),
        path("upload-file/<str:folder_name>/", upload_file, name="upload_file"),
        path("delete-files/<str:folder_name>/", delete_files, name="delete_files"),
        path("run-script/<str:folder_name>/", run_script_excel, name="run_script"),
        path("run_merge_script/", handle_json_data, name="run_merge_script"),
    ],
    "excelmerge",
)
gpxapp_patterns = (
    [
        path("", index, name="index"),
        path("download-gpx/", download_gpx, name="download_gpx"),
    ],
    "gpx_app",
)
gpx_processor_patterns = (
    [
        path("", gpx_processor_index, name="index"),
        path("upload/", upload_gpx, name="upload"),
        path("map_edit/", map_edit, name="map_edit"),
        path("update_gpx/", update_gpx, name="update_gpx"),
        path("fix_gpx/<str:file_name>/", fix_gpx_view, name="fix_gpx"),
    ],
    "gpx_processor",
)
gpx_view_patterns = (
    [
        path("save-markers/", save_markers, name="save_markers"),
        path("show-markers/", show_markers, name="show_markers"),
    ],
    "gpx_view",
)

chainage_repo_patterns = (
    [
        path("", get_data, name="get_data"),
        path("update-chainage/", update_chainage, name="update_chainage"),
    ],
    "chainage_repo",
)


gpx_edit_urls = [
    path("upload/", upload_gpx_edit, name="upload_gpx"),
    path("plot/<str:file_name>/", plot_gpx_edit, name="plot_gpx_edit"),
    path("update/<str:file_name>/", update_gpx_edit, name="update_gpx"),
    path("download/<str:file_name>/", download_gpx_edit, name="download_gpx"),
    path("get_average_gap/<str:file_name>/", get_average_gap, name="get_average_gap"),
    path(
        "generate_point/<str:file_name>/", generate_point_by_time, name="generate_point"
    ),
]

urlpatterns = [
    path("login/", custom_login_view, name="login"),
    path("logout/", custom_logout_view, name="logout"),
    path("admin-dashboard/", admin_dashboard_view, name="admin_dashboard"),
    path("register/", register_user, name="register_user"),
    path("verify-otp/", verify_otp, name="verify_otp"),
    path("set-password/<uidb64>/<token>/", set_password, name="set_password"),
    path("users/", user_list, name="user_list"),
    path("delete-user/<int:user_id>/", delete_user, name="delete_user"),
    path("", base_page, name="base_page"),
    path("upload-furniture-json/", upload_furniture_json, name="upload_furniture_json"),
    path("show-images-furniture/", show_images_furniture, name="show_images_furniture"),
    path("patch-furniture-json/", patch_furniture_json, name="patch_furniture_json"),
    # path('patch-pavement-json/' , patch_pavement_json , name='patch_pavement_json'),
    path("patch-pavement-json/", patch_pavement_json, name="patch_pavement_json"),
    path("pavement/", base_page, name="pavement_detail"),
    path("update-json/", patch_furniture_json, name="update_json"),
    path("show-images-pavement/", show_images_pavement, name="show_images_pavement"),
    path("fetch-pavement/", fetch_and_show_pavement, name="fetch_and_show_pavement"),
    # path('patch-pavement-json/', patch_pavement_json, name='patch_pavement_json'),
    path("Get-pavement-json/", get_pavement_json, name="get_pavement_json"),
    path(
        "pothole-pavement/", pothole_pavement_testing, name="pothole_pavement_testing"
    ),
    path("show-pothole-pavement/", show_pothole_pavement, name="show_pothole_pavement"),
    path("manual/", manual_testing, name="manual_data_detail"),
    path("filter-road-sign/", FilterRoadSign, name="filter_road_sign"),
    path("view-roads/", ViewRoads, name="View_Roads"),
    path("view-roads-date/", ViewRoadsByDate, name="View_Roads_Date"),
    path("export-selected-roads/", export_selected_roads, name="export_selected_roads"),
    path("upload/", upload_images, name="upload_images"),
    path("upload-pavement/", upload_images_pavement, name="upload_images_pavement"),
    path("delete_image/", delete_image, name="delete_image"),
    path("delete_all/", delete_all_images, name="delete_all_images"),
    path("process/", process_images, name="process_images"),
    path("process/<str:current_image_name>/", process_images, name="process_images"),
    path("road-data/<str:roadId>/", road_data, name="road_data"),
    path("fetch-images/", fetch_images, name="fetch_images"),
    path("save-anomalies/", save_anomalies, name="save_anomalies"),
    path("download-gpx/", download_gpx_file, name="download_gpx"),
    path(
        "download-json/<survey_id>/<road_id>/<model_type>/",
        download_json,
        name="download_json",
    ),
    path(
        "delete-json/<survey_id>/<road_id>/<model_type>/",
        delete_json,
        name="delete_json",
    ),
    path(
        "merge-json/<survey_id>/<road_id>/<model_type>/", merge_json, name="merge_json"
    ),
    path(
        "upload-json/<int:survey_id>/<int:road_id>/<str:model_type>/",
        upload_gpx_json,
        name="upload_gpx_json",
    ),
    path("upload_data/", upload_data, name="upload_data"),
    path("get_furniture_json/", get_furniture_json, name="get_furniture_json"),
    path("anomaly-upload/", AnomalyUploadView.as_view(), name="AnomalyUploadView"),
    path("excelmerge/", include(excelmerge_patterns)),
    path("gpx-app/", include(gpxapp_patterns)),
    path("gpx-processor/", include(gpx_processor_patterns)),
    path("gpx-view/", include(gpx_view_patterns)),
    path("chainage-repo/", include(chainage_repo_patterns)),
    path("gpx/", include(gpx_edit_urls)),
    path("patch_road/", fetch_data, name="fetch_data"),
    path("upload-s3/", upload_s3, name="upload_s3"),
    path(
        "commence_generate_and_patch_excel/",
        commence_generate_and_patch_excel,
        name="commence_generate_and_patch_excel",
    ),
    path("commence_generate_final_excel/",commence_generate_final_excel,name="commence_generate_final_excel"),
    path("stream-logs/<str:process_id>/", stream_logs, name="stream_logs"),
    path("download_final_excel/<str:process_id>/",download_final_excel,name="download_final_excel"),
    path("upload-image/", receive_canvas_image, name="receive_canvas_image"),
]

from django.views.generic import TemplateView

urlpatterns += [
    path(
        "generate-and-patch-excel/",
        TemplateView.as_view(template_name="ra_testing/generate_and_patch_excel.html"),
        name="generate_and_patch_excel",
    ),
    path(
        "generate-final-excel/",
        TemplateView.as_view(template_name="ra_testing/generate_final_excel.html"),
        name="generate_final_excel",
    ),
]
# AIzaSyAtVXosLTQjTMVm2K9BJf55HZAkNAGTr4U

