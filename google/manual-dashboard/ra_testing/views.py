import base64, json, math, os, queue, random, shutil, smtplib, threading, uuid, boto3, gpxpy, gpxpy.gpx, requests, pandas as pd
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from io import BytesIO
from pathlib import Path
from urllib.parse import urljoin
from dotenv import load_dotenv
from geopy import Point
from geopy.distance import geodesic
from openpyxl import Workbook
from requests.exceptions import RequestException
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.tokens import default_token_generator
from django.core.files.storage import FileSystemStorage, default_storage
from django.core.paginator import Paginator
from django.http import (
    FileResponse,
    Http404,
    HttpResponse,
    JsonResponse,
    StreamingHttpResponse,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.views import View
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from django.views.decorators.http import require_POST
from .forms import GpxUploadForm, UserRegistrationForm
from .gpxProcess import GPXProcessor
from .help.CL_final import generate_json_from_folder as generate_json_from_CL_Final
from .help.CR_final import generate_json_from_folder as generate_json_from_CR_Final
from .help.M_final import generate_json_from_folder as generate_json_from_M_final
from .help.SL_final import generate_json_from_folder as generate_json_from_SL_final
from .help.SR_final import generate_json_from_folder as generate_json_from_SR_final
from .help.TL_final import generate_json_from_folder as generate_json_from_TL_Final
from .help.TR_final import generate_json_from_folder as generate_json_from_TR_Final
from .help.dp2 import excel_updation
from .help.final_colur_format import final_colur_format
from .models import Environment
from .utils import process_gpx_files

load_dotenv()

AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")
AWS_STORAGE_BUCKET_NAME = os.environ.get("AWS_STORAGE_BUCKET_NAME")
AWS_S3_REGION_NAME = os.environ.get("AWS_S3_REGION_NAME")
AWS_S3_URL = f"https://{AWS_STORAGE_BUCKET_NAME}.s3.{AWS_S3_REGION_NAME}.amazonaws.com"
s3_client = boto3.client(
    "s3",
    region_name=AWS_S3_REGION_NAME,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
)

SECURITY_PASSWORD = os.environ.get("ROADATHENA_SECURITY_PASSWORD")

HEADERS = {"Security-Password": SECURITY_PASSWORD}

# Global dictionaries for background processing
active_processes = {}
log_queues = {}
from . import cloud_module as cloud
from . import detect_timestamp as ocr
from .gen_and_patch_excel import master_orchestrator as mo
from .gen_final_excel.master_runner import run_pipeline as execute_pipeline


@csrf_exempt
def commence_generate_and_patch_excel(request):
    if request.method != "POST":
        return render(request, "ra_testing/generate_and_patch_excel.html")

    # 1. Extract Survey ID
    if request.content_type == "application/json":
        survey_id = json.loads(request.body).get("survey_id")
    else:
        survey_id = request.POST.get("survey_id")

    if not survey_id:
        return JsonResponse({"error": "Please enter a Survey ID."}, status=400)

    q = queue.Queue()

    def progress_callback(msg):
        q.put({"type": "progress", "message": msg})

    def run_pipeline():
        try:
            # Note: master_orchestrator.execute handles both survey and road IDs
            input_id = int(survey_id)
            password = os.environ.get("ROAD_API_PASSWORD")

            # Execute Pipeline
            result_data = mo.execute(
                input_id=input_id,
                security_password=password,
                run_stages=["fetch", "process", "excel"],
                progress_callback=progress_callback,
            )

            report_dir = os.path.join(settings.MEDIA_ROOT, "excel_reports")
            os.makedirs(report_dir, exist_ok=True)
            road_results = []

            # Handle both single road result and survey result (dict of results)
            all_categories = (
                result_data.get("results", {})
                if "results" in result_data
                else {"result": result_data}
            )

            # If it's a survey run, mo.execute likely returns a dict mapping categories to summaries
            # We simplify by flattening all results
            items_to_process = []
            if "mcw" in result_data or "service" in result_data:
                for cat in ["mcw", "service"]:
                    if cat in result_data:
                        items_to_process.append((cat, result_data[cat]))
            else:
                items_to_process.append(("road", result_data))

            for category_key, category_data in items_to_process:
                # Copy generated excel files
                for excel_info in category_data.get("generated_excels", []):
                    rid = excel_info["road_id"]
                    src = excel_info["file_path"]
                    dest = os.path.join(report_dir, f"{rid}_formatted.xlsx")
                    if os.path.exists(src):
                        shutil.copy(src, dest)

                # Format results for frontend
                for road_id, road_data in category_data.get("results", {}).items():
                    stages = {
                        "fetch": {
                            "json": len(road_data.get("fetch", {}).get("json", [])) > 0,
                            "gpx": len(road_data.get("fetch", {}).get("gpx", [])) > 0,
                        },
                        "process": {
                            "json_cleaner": bool(
                                road_data.get("process", {}).get("json_cleaner")
                            ),
                            "gpx_converter": bool(
                                road_data.get("process", {}).get("gpx_converter")
                            ),
                            "category": bool(
                                road_data.get("process", {}).get("category")
                            ),
                            "side_check": bool(
                                road_data.get("process", {}).get("side_check")
                            ),
                            "json_patch": len(
                                road_data.get("process", {})
                                .get("json_patch", {})
                                .get("patched", [])
                            )
                            > 0,
                        },
                        "excel": {
                            "excel_generated": bool(
                                road_data.get("excel", {}).get("excel_generation")
                            ),
                            "excel_patched": road_data.get("excel", {})
                            .get("excel_patch", {})
                            .get("patched", False),
                        },
                    }
                    road_results.append(
                        {
                            "road_id": road_id,
                            "road_type": category_key,
                            "stages": stages,
                            "excel_url": f"{settings.MEDIA_URL}excel_reports/{road_id}_formatted.xlsx",
                        }
                    )

            q.put(
                {"type": "result", "survey_id": input_id, "road_results": road_results}
            )

        except Exception as e:
            q.put({"type": "error", "message": str(e)})
        finally:
            q.put(None)

    threading.Thread(target=run_pipeline).start()

    def event_stream():
        while True:
            msg = q.get()
            if msg is None:
                break
            yield f"data: {json.dumps(msg)}\n\n"

    return StreamingHttpResponse(event_stream(), content_type="text/event-stream")


@csrf_exempt
def commence_generate_final_excel(request):
    if request.method != "POST":
        return render(request, "ra_testing/generate_final_excel.html")
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON mapping"}, status=400)

    survey_id = data.get("survey_id", "").strip()
    if not survey_id and not survey_id.isdigit():
        return JsonResponse({"error": "Please enter a valid Survey ID."}, status=400)

    process_id = f"{survey_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    log_queues[process_id] = queue.Queue()

    def run_pipeline_process(survey_id, process_id):
        """Run master_runner pipeline directly and stream logs via queue"""

        try:
            log_queue = log_queues[process_id]

            # Custom logger handler to capture logs
            import logging

            class QueueHandler(logging.Handler):
                def emit(self, record):
                    log_entry = self.format(record)
                    log_queue.put(log_entry)

            # Attach handler to MASTER_RUNNER logger
            queue_handler = QueueHandler()
            queue_handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s | %(name)s | %(levelname)s | %(message)s"
                )
            )

            root_logger = logging.getLogger()
            root_logger.setLevel(logging.INFO)
            root_logger.addHandler(queue_handler)

            # Run pipeline
            result = execute_pipeline(int(survey_id))

            # Remove handler after execution
            root_logger.removeHandler(queue_handler)

            if result:
                active_processes[process_id] = {
                    "excel_path": result.get("excel_path"),
                    "api_counts": result.get("api_counts"),
                    "excel_counts": result.get("excel_counts"),
                    "validation_status": result.get("validation_status"),
                }

                log_queue.put("__COMPLETED__")

            else:
                log_queue.put("__ERROR__Pipeline returned no result")

        except Exception as e:
            log_queue.put(f"__ERROR__{str(e)}")

    thread = threading.Thread(target=run_pipeline_process, args=(survey_id, process_id))
    thread.daemon = True
    thread.start()

    return JsonResponse({"process_id": process_id, "status": "started"})


def stream_logs(request, process_id):
    """Stream logs to the client using Server-Sent Events"""

    def generate():
        if process_id not in log_queues:
            yield f"data: {json.dumps({'error': 'Process not found'})}\n\n"
            return

        log_queue = log_queues[process_id]

        while True:
            try:
                log_line = log_queue.get(timeout=30)

                if log_line.startswith("__COMPLETED__"):
                    result = active_processes.get(process_id, {})
                    yield f"data: {json.dumps({'status': 'completed', 'validation_status': result.get('validation_status'), 'api_counts': result.get('api_counts'), 'excel_counts': result.get('excel_counts')})}\n\n"
                    break

                elif log_line.startswith("__ERROR__"):
                    error_msg = log_line.replace("__ERROR__", "")
                    yield f"data: {json.dumps({'status': 'error', 'message': error_msg})}\n\n"
                    break

                else:
                    yield f"data: {json.dumps({'log': log_line})}\n\n"

            except queue.Empty:
                yield f"data: {json.dumps({'keepalive': True})}\n\n"

    return StreamingHttpResponse(generate(), content_type="text/event-stream")


def download_final_excel(request, process_id):
    result = active_processes.get(process_id)

    if not result:
        return JsonResponse({"error": "File not ready"})

    excel_path = result.get("excel_path")

    if not excel_path or not os.path.exists(excel_path):
        return JsonResponse({"error": "File not found"})

    return FileResponse(
        open(excel_path, "rb"),
        as_attachment=True,
        filename=os.path.basename(excel_path),
    )


# ============================================================================================================= CLOUD MODULE NISHANT
# inpect the url in path in the process canva fetch in send to backend


@csrf_exempt  # remove if you handle CSRF properly
def receive_canvas_image(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request method"}, status=405)

    image_file = request.FILES.get("image")

    if not image_file:
        return JsonResponse({"error": "No image provided"}, status=400)

    try:
        # Ensure upload directory exists
        upload_dir = os.path.join(settings.MEDIA_ROOT, "to_s3_cloud_temp")
        os.makedirs(upload_dir, exist_ok=True)

        # Generate unique filename
        file_ext = os.path.splitext(image_file.name)[1] or ".png"
        filename = f"{uuid.uuid4()}{file_ext}"
        file_path = os.path.join(upload_dir, filename)

        # Save file
        with open(file_path, "wb+") as destination:
            for chunk in image_file.chunks():
                destination.write(chunk)

        cloud.upload_file(
            local_path=Path(file_path),
            s3_path=f"anotationdata_test/data/DATASET/{filename}",
        )
        print("file is uploaded to the cloud successfully")

        # cleanup

        if os.path.exists(file_path):  #uncomment this in order to delete the image file after it is uploaded sucessfully.
            os.remove(file_path)
        print(
            "the image file is deleted successfully(uncomment in order to really delete the image file.)"
        )

        return JsonResponse({"status": "success", "filename": filename})

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def custom_login_view(request):
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")

        user = authenticate(request, email=email, password=password)

        if user is not None:
            login(request, user)

            # Redirect based on role--
            if user.role == "admin":
                return redirect("admin_dashboard")  # Define this view later
            elif user.role == "developer":
                return redirect("survey_dashboard:dashboard")
            else:
                return redirect("base_page")  # Tester/Developer dashboard
        else:
            messages.error(request, "Invalid email or password.")

    return render(
        request, "ra_testing/login.html"
    )  # Replace with your actual login page


@login_required
def admin_dashboard_view(request):
    if request.user.role != "admin":
        return redirect("base_page")  # Block non-admins
    return render(request, "ra_testing/admin.html", {"user": request.user})


@login_required
def custom_logout_view(request):
    logout(request)
    return redirect("login")


@login_required
def base_page(request):
    if request.method == "POST":
        env_name = request.POST.get("environment", "dev")
        try:
            env = Environment.objects.get(name=env_name)
            road_api = env.base_url
        except Environment.DoesNotExist:
            road_api = "ndd.roadathena.com"  # fallback

        request.session["road_api"] = road_api
        return redirect("base_page")

    # Pass all environment options to the template-
    environments = Environment.objects.all()
    return render(
        request,
        "ra_testing/base.html",
        {"user": request.user, "environments": environments},
    )


# def verify_otp(request):
#     if request.method == 'POST':
#         entered_otp = request.POST.get('otp')
#         actual_otp = request.session.get('otp')

#         if entered_otp == actual_otp:
#             data = request.session.get('pending_user')
#             if data:
#                 # Create user
#                 form = UserRegistrationForm(data)
#                 user = form.save(commit=False)
#                 user.set_password(data['password'])
#                 user.save()

#                 # Clear session data
#                 del request.session['otp']
#                 del request.session['pending_user']


#                 return redirect('user_list')
#         else:
#             messages.error(request, "Invalid OTP. Try again.")

#     return render(request, 'ra_testing/verify_otp.html')


def verify_otp(request):
    if request.method == "POST":
        entered_otp = request.POST.get("otp")
        actual_otp = request.session.get("otp")

        if entered_otp == actual_otp:
            data = request.session.get("pending_user")
            if data:
                # Create user
                form = UserRegistrationForm(data)
                user = form.save(commit=False)
                user.set_password(data["password"])
                user.save()

                # Clear session data
                del request.session["otp"]
                del request.session["pending_user"]

                send_set_password_email(user)

                return redirect("user_list")

            else:
                messages.error(request, "Invalid OTP. Try again.")

    return render(request, "ra_testing/verify_otp.html")


def send_otp_to_email(request, email):
    otp = str(random.randint(100000, 999999))  # Generate a random 6-digit OTP
    # send_mail(
    #     'Your OTP for Registration',
    #     f'Your OTP is: {otp}',
    #     'noreply@yourdomain.com',
    #     [email],
    #     fail_silently=False,
    # )
    s = smtplib.SMTP("smtp.gmail.com", 587)
    s.starttls()
    s.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)

    msg = MIMEMultipart()
    msg["From"] = settings.EMAIL_HOST_USER
    msg["To"] = email
    msg["Subject"] = "Your OTP Verification Code"

    mail_body = f"Your One Time Password (OTP) is: {otp}"
    msg.attach(MIMEText(mail_body, "plain"))

    s.sendmail(settings.EMAIL_HOST_USER, email, msg.as_string())
    s.quit()

    return otp


def send_set_password_email(user):
    token = default_token_generator.make_token(user)
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    link = f"http://127.0.0.1:8000/set-password/{uid}/{token}/"

    # SMTP setup
    s = smtplib.SMTP("smtp.gmail.com", 587)
    s.starttls()
    s.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)

    msg = MIMEMultipart()
    msg["From"] = settings.EMAIL_HOST_USER
    msg["To"] = user.email
    msg["Subject"] = "Set Your Password - YourApp"

    mail_body = f"""
    Hello,

    Please click the link below to set your password:

    {link}

    If you did not request this, you can ignore this email.

    Thank you,
    YourApp Team
    """

    msg.attach(MIMEText(mail_body, "plain"))
    s.send_message(msg)
    s.quit()


def set_password(request, uidb64, token):
    User = get_user_model()
    uid = urlsafe_base64_decode(uidb64).decode()
    user = User.objects.get(pk=uid)

    if not default_token_generator.check_token(user, token):
        return HttpResponse("Invalid or expired token.")

    if request.method == "POST":
        password = request.POST.get("password")
        confirm = request.POST.get("confirm_password")

        if password == confirm:
            user.set_password(password)
            user.save()
            return redirect("login")  # or show success page

    return render(request, "ra_testing/set_password.html", {"user": user})


@login_required
def register_user(request):
    if request.user.role != "admin":
        return render(request, "ra_testing/403.html")  # Or raise PermissionDenied

    if request.method == "POST":
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"]
            otp = send_otp_to_email(request, email)
            request.session["pending_user"] = form.cleaned_data
            request.session["otp"] = otp
            return redirect("verify_otp")  # Replace with actual redirect target
    else:
        form = UserRegistrationForm()

    return render(request, "ra_testing/register_user.html", {"form": form})


@login_required
def user_list(request):
    if request.user.role != "admin":
        return render(request, "403.html")

    user_list = get_user_model().objects.all().order_by("email")
    paginator = Paginator(user_list, 10)  # 10 users per page

    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        "ra_testing/dash_users.html",
        {
            "users": page_obj,  # For table loop
            "page_obj": page_obj,  # For pagination controls
        },
    )


User = get_user_model()


@require_POST
@login_required
def delete_user(request, user_id):
    context = {}

    if request.user.id == user_id:
        context["error"] = "You cannot delete your own account."
    else:
        user = get_object_or_404(User, id=user_id)
        user.delete()
        context["success"] = "User deleted successfully."

    users = User.objects.all()
    context["users"] = users
    return render(request, "ra_testing/dash_users.html", context)


# def upload_furniture_json(request):
#     if request.method == 'POST':
#         file = request.FILES.get('json_file')
#         if file:
#             # Save the file using Django's default storage system
#             furniture_file = FurnitureFile.objects.create(file=file)
#             original_filename = file.name

#             # Load the JSON data from the uploaded file
#             with default_storage.open(furniture_file.file.name) as f:
#                 data = json.load(f)

#             # Store the data in session
#             request.session['furniture_data'] = json.dumps(data)
#             request.session['original_filename'] = original_filename

#             return redirect('show_images_furniture')  # Redirect to the view that shows images

#     return render(request, 'ra_testing/uploadFurnitureJson.html')


@never_cache
def upload_furniture_json(request):
    context = {}

    if request.method == "POST":
        road_api = request.session.get("road_api", None)
        road_id = request.POST.get("numberInput")

        if not road_id:
            return JsonResponse({"error": "No number provided"}, status=400)

        try:
            road_id = int(road_id)
            print("...road_id is", road_id)

            api_url = f"https://{road_api}/api/surveys/roads/{road_id}"
            print("API URL is", api_url)

            response = requests.get(api_url, headers=HEADERS)
            data = response.json()
            print("...data is", data)

            # Extract the file URL
            file_url = data.get("furniture_json")
            original_filename = data["road"]["name"]
            print("file URL is", file_url)

            if not file_url:
                context["json_error"] = True
                return render(request, "ra_testing/uploadFurnitureJson.html", context)

            # Full file URL
            base_url = f"https://{road_api}"
            file_url = urljoin(base_url, file_url)
            print("Resolved file URL is", file_url)

            # Try to fetch and decode the JSON file
            file_response = requests.get(file_url, headers=HEADERS)
            try:
                file_data_json = file_response.json()
            except json.JSONDecodeError:
                context["json_error"] = True
                return render(request, "ra_testing/uploadFurnitureJson.html", context)

            # Store data in session
            request.session["furniture_data"] = json.dumps(file_data_json)
            request.session["original_filename"] = original_filename
            request.session["road_id"] = road_id

            return redirect("show_images_furniture")

        except (ValueError, RequestException, KeyError) as e:
            print("Error occurred:", str(e))
            context["json_error"] = True
            return render(request, "ra_testing/uploadFurnitureJson.html", context)

    return render(request, "ra_testing/uploadFurnitureJson.html")


@never_cache
def show_images_furniture(request):
    data = request.session.get("furniture_data")
    road_id = request.session.get("road_id")
    print(road_id)
    original_filename = request.session.get("original_filename")
    deleted_items = request.session.get("deleted_items", [])

    if not data:
        return redirect(
            "upload_furniture_json"
        )  # Redirect to the upload page if no data in session

    data = json.loads(data)

    index = int(request.GET.get("index", 0))
    image_type = request.GET.get("type", "assets")

    items = data.get(image_type, [])

    if not items:
        current_item = None
        next_index = 0
    else:
        if index >= len(items):
            index = 0

        current_item = items[index] if index < len(items) else None
        next_index = (index + 1) % len(items)

    context = {
        "data": json.dumps(data),  # Send the data to the template as JSON
        "current_item": current_item,
        "next_index": next_index,
        "type": image_type,
        "road_id": road_id,
        "original_filename": original_filename,
        "deleted_items": json.dumps(
            deleted_items
        ),  # Send the deleted items to the template
    }

    return render(request, "ra_testing/show_images_furniture.html", context)


@csrf_exempt
# def patch_furniture_json(request):
#     if request.method == 'PATCH':
#         try:
#             # Extract data from request body
#             newdata = json.loads(request.body)
#             print('type of newdata is  , ' , type(newdata))

#             # Retrieve session data
#             road_api = request.session.get('road_api', None)
#             road_id = request.session.get('road_id', None)

#             print("road api is " , road_api)
#             print("road_id id ,",road_id)

#             if not road_api or not road_id:
#                 return JsonResponse({"error": "Missing road_api or road_id in session"}, status=400)

#             road_id = int(road_id)
#             api_url = f"https://{road_api}/api/surveys/roads/{road_id}"
#             print("API URL:", api_url)


#             response = requests.get(api_url, headers=HEADERS)
#             response.raise_for_status()  # Raise error for HTTP failures

#             data = response.json()


#             # Get furniture JSON file URL
#             file_url = data.get('furniture_json')
#             if not file_url:
#                 return HttpResponse("No furniture JSON file URL found in the response.", status=404)

#             base_url = f'https://{road_api}'
#             file_url = urljoin(base_url, file_url)
#             print('File URL:', file_url)

#             # Fetch JSON file data
#             json_response = requests.get(file_url, headers=HEADERS)
#             json_response.raise_for_status()  # Raise error for HTTP failures

#             json_data = json_response.json()  # Convert response to JSON

#             # Extract filename from URL
#             file_name = os.path.basename(file_url)
#             print('Filename:', file_name)

#             # Define file path
#             directory = os.path.join(settings.MEDIA_ROOT , "Furniture_json")
#             file_path = os.path.join(directory, file_name)

#             # Ensure directory exists
#             os.makedirs(directory, exist_ok=True)

#             # Save old data into the file
#             with open(file_path, "w") as file:
#                 json.dump(json_data, file, indent=4)

#            # Save the new data into the file (overwrite)
#             with open(file_path, "w") as file:
#                 json.dump(newdata, file, indent=4)

#             # PATCH the file properly
#             print("I have the patch payload")

#             with open(file_path, 'rb') as f:
#                 patch_response = requests.patch(
#                     api_url,
#                     files={"furniture_json": (file_name, f)},
#                     headers=HEADERS
#                 )
#                 patch_response.raise_for_status()

#             print('I HAVE SUCCESSFULLY PATCHED IT')

#             return JsonResponse({"message": "Data patched successfully", "file_path": file_path}, status=200)

#         except requests.exceptions.RequestException as e:
#             return JsonResponse({"error": f"Request failed: {str(e)}"}, status=500)
#         except json.JSONDecodeError:
#             return JsonResponse({"error": "Invalid JSON received"}, status=400)
#         except Exception as e:
#             return JsonResponse({"error": f"Unexpected error: {str(e)}"}, status=500)


#     return JsonResponse({"error": "Invalid HTTP method"}, status=405)
@csrf_exempt
def patch_furniture_json(request):
    if request.method in ["POST", "PATCH"]:
        try:
            # 1. Parse and clean the incoming JSON structure
            received_payload = json.loads(request.body)

            if isinstance(received_payload, dict) and "data" in received_payload:
                newdata = received_payload["data"]
            else:
                newdata = received_payload

            if not isinstance(newdata, dict):
                return JsonResponse({"error": "Data must be a JSON object"}, status=400)

            # Ensure the required keys exist for the final file
            newdata.setdefault("assets", [])
            newdata.setdefault("anomalies", [])

            # 2. Retrieve session data
            road_api = request.session.get("road_api")
            road_id = request.session.get("road_id")

            if not road_api or not road_id:
                return JsonResponse({"error": "Missing session data"}, status=400)

            road_id = int(road_id)
            api_url = f"https://{road_api}/api/surveys/roads/{road_id}"

            # 3. Get the existing road info to find the filename
            response = requests.get(api_url, headers=HEADERS)
            response.raise_for_status()
            road_data = response.json()

            file_url_path = road_data.get("furniture_json")
            if not file_url_path:
                return JsonResponse(
                    {"error": "No furniture JSON file URL found on server"}, status=404
                )

            # 4. Prepare local directory and filename
            file_name = os.path.basename(file_url_path)
            directory = os.path.join(settings.MEDIA_ROOT, "Furniture_json")
            os.makedirs(directory, exist_ok=True)
            file_path = os.path.join(directory, file_name)

            # 5. Save the CLEANED newdata (without the 'filename' or 'data' wrapper)
            with open(file_path, "w") as file:
                json.dump(newdata, file, indent=4)

            # 6. PATCH the local file back to the remote API
            with open(file_path, "rb") as f:
                patch_response = requests.patch(
                    api_url, files={"furniture_json": (file_name, f)}, headers=HEADERS
                )
                patch_response.raise_for_status()

            return JsonResponse(
                {"message": "Successfully patched", "file": file_name}, status=200
            )

        except requests.exceptions.RequestException as e:
            return JsonResponse({"error": f"API Error: {str(e)}"}, status=500)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Invalid Method"}, status=405)


# def upload_pavement_json(request):
#     if request.method == 'POST':
#         file = request.FILES.get('json_file')
#         if file:
#             furniture_file = FurnitureFile.objects.create(file=file)
#             original_filename = file.name

#             with open(furniture_file.file.path) as f:
#                 data = json.load(f)

#             # Debug: Print the loaded JSON data
#             print("Uploaded JSON Data:", data)

#             request.session['uploaded_pavement_data'] = data
#             request.session['original_filename'] = original_filename

#             return redirect('show_images_pavement')  # Redirect to the view that shows images

#     return render(request, 'ra_testing/uploadPavement.html')


@never_cache
def show_images_pavement(request):
    data = request.session.get("uploaded_pavement_data")
    original_filename = request.session.get("original_filename")

    # Debug: Print data and original filename
    print("Session JSON Data:", data)
    print("Original Filename:", original_filename)

    if not data:
        print("No data found in session, redirecting to upload page.")
        return redirect(
            "upload_pavement_json"
        )  # Redirect to the upload page if no data in session

    index = int(request.GET.get("index", 0))
    image_type = request.GET.get("type", "Anomalies")

    items = data.get(image_type, [])

    # Debug: Print the items length and details
    print(f"Number of {image_type} items:", len(items))
    print(f"Items: {items}")

    if not items:
        current_image = None
        next_index = 0
    else:
        if index >= len(items):
            index = 0

        current_image = items[index].get("image") if index < len(items) else None
        next_index = (index + 1) % len(items)

    context = {
        "data": json.dumps(data),  # Include JSON data in the context
        "original_filename": original_filename,
        "current_image": current_image,
        "next_index": next_index,
        "type": image_type,
    }

    return render(request, "ra_testing/show_images_pavement.html", context)


@csrf_exempt
def upload_data(request):

    road_api = request.session.get("road_api", None)
    if request.method == "POST":
        # Handling JSON file upload for road data
        road_id = request.POST.get("road_id")
        json_file = request.FILES.get("json_file")

        # Handling Excel file upload for survey report
        survey_id = request.POST.get("survey_id")
        excel_file = request.FILES.get("excel_file")

        # Handling the processed videos link
        processed_videos_link = request.POST.get("processed_videos_link")

        # Handling the JSON file
        if road_id and json_file:
            road_api_url = f"https://{road_api}/api/surveys/roads/{road_id}"
            # Save the JSON file to disk
            json_file_name = default_storage.save(json_file.name, json_file)
            json_file_path = default_storage.path(
                json_file_name
            )  # Get the full path to the file

            with open(json_file_path, "rb") as f:
                road_files = {"json_file": f}
                road_response = requests.patch(
                    road_api_url, files=road_files, headers=HEADERS
                )
                if road_response.status_code != 200:
                    return JsonResponse(
                        {"error": f"Failed to patch JSON file: {road_response.text}"},
                        status=400,
                    )

        # Prepare data for PATCH request to the survey report API
        if survey_id:
            survey_api_url = f"https://{road_api}/api/surveys/reports/{survey_id}/"
            survey_data = {}
            survey_files = {}

            # Handle Excel file upload
            if excel_file:
                excel_file_name = default_storage.save(excel_file.name, excel_file)
                excel_file_path = default_storage.path(
                    excel_file_name
                )  # Get the full path to the file
                survey_files["excelreport"] = open(excel_file_path, "rb")

            # Handle processed videos link
            if processed_videos_link:
                survey_data["processed_videos_link"] = processed_videos_link

            # Perform the PATCH request for the Excel file
            if survey_files:
                survey_response = requests.patch(
                    survey_api_url, files=survey_files, headers=HEADERS
                )
                if survey_response.status_code != 200:
                    return JsonResponse(
                        {
                            "error": f"Failed to patch Excel file: {survey_response.text}"
                        },
                        status=400,
                    )

            # Perform the PATCH request for additional data (processed videos link)
            if survey_data:
                survey_response = requests.patch(
                    survey_api_url, data=survey_data, headers=HEADERS
                )
                if survey_response.status_code != 200:
                    return JsonResponse(
                        {
                            "error": f"Failed to patch processed videos link: {survey_response.text}"
                        },
                        status=400,
                    )

        return JsonResponse({"message": "Files successfully uploaded and patched."})

    return render(request, "ra_testing/upload_data.html")


@never_cache
def get_pavement_json(request):
    road_api = request.session.get("road_api", None)

    if request.method == "POST":
        road_id = request.POST.get("road_id")
        if not road_id:
            return HttpResponse("Road ID is required.", status=400)

        # URL to fetch JSON data from
        api_url = f"https://{road_api}/api/surveys/roads/{road_id}"

        try:
            response = requests.get(api_url, headers=HEADERS)
            response.raise_for_status()
        except requests.RequestException as e:
            return HttpResponse(f"Error fetching data: {e}", status=500)

        data = response.json()

        file_url = data.get("json_file")
        if not file_url:
            return HttpResponse("No JSON file URL found in the response.", status=404)

        # Ensure the file URL is absolute
        base_url = (
            f"https://{road_api}"  # Replace with the actual base URL if different
        )
        file_url = urljoin(base_url, file_url)

        try:
            # Download the file from the URL
            file_response = requests.get(file_url, headers=HEADERS)
            file_response.raise_for_status()  # Raise an error for bad responses
        except requests.RequestException as e:
            return HttpResponse(f"Error downloading file: {e}", status=500)

        response = HttpResponse(
            file_response.content,
            content_type="application/json",
            headers={
                "Content-Disposition": f'attachment; filename="road_{road_id}.json"',
            },
        )

        return response

    # Handle GET request to display the form
    return render(request, "ra_testing/get_pavement_json.html")


@never_cache
def fetch_and_show_pavement(request):
    road_api = request.session.get("road_api", None)
    context = {}

    if request.method == "POST":
        road_id = request.POST.get("road_id")

        if not road_id:
            context["error"] = "Road ID is required."
            return render(request, "ra_testing/fetchPavement.html", context)

        road_id = int(road_id)
        request.session["road_id"] = road_id
        request.session["road_api"] = road_api
        api_url = f"https://{road_api}/api/surveys/roads/{road_id}"

        try:
            response = requests.get(api_url, headers=HEADERS)
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as e:
            context["error"] = f"Error fetching road data: {e}"
            return render(request, "ra_testing/fetchPavement.html", context)

        file_url = data.get("json_file")
        if not file_url:
            context["error"] = "No JSON file URL found in the API response."
            return render(request, "ra_testing/fetchPavement.html", context)

        file_url = urljoin(f"https://{road_api}", file_url)

        try:
            file_response = requests.get(file_url, headers=HEADERS)
            file_response.raise_for_status()
        except requests.RequestException as e:
            context["error"] = f"Error downloading JSON: {e}"
            return render(request, "ra_testing/fetchPavement.html", context)

        try:
            json_data = file_response.json()
        except json.JSONDecodeError:
            context["error"] = "Downloaded file is not valid JSON."
            return render(request, "ra_testing/fetchPavement.html", context)

        request.session["uploaded_pavement_data"] = json_data
        request.session["original_filename"] = f"road_{road_id}.json"
        return redirect("show_images_pavement")

    return render(request, "ra_testing/fetchPavement.html", context)


# @csrf_exempt
# def patch_pavement_json(request):
#     if request.method == 'POST':
#         try:
#             # Safely parse incoming data, even if it's a double-encoded string
#             raw_body = request.body
#             try:
#                 newdata = json.loads(raw_body)
#                 if isinstance(newdata, str):  # If still a string, parse again
#                     newdata = json.loads(newdata)
#             except json.JSONDecodeError:
#                 return JsonResponse({"error": "Invalid or double-encoded JSON received."}, status=400)

#             print('Final parsed newdata type:', type(newdata))

#             # Session data
#             road_api = request.session.get('road_api')
#             road_id = request.session.get('road_id')

#             print("road_api:", road_api)
#             print("road_id:", road_id)

#             if not road_api or not road_id:
#                 return JsonResponse({"error": "Missing road_api or road_id in session"}, status=400)

#             road_id = int(road_id)
#             api_url = f"https://{road_api}/api/surveys/roads/{road_id}"

#             response = requests.get(api_url, headers=HEADERS)
#             response.raise_for_status()
#             data = response.json()

#             file_url = data.get('json_file')
#             if not file_url:
#                 return JsonResponse({"error": "No pavement JSON file URL found."}, status=404)

#             full_url = urljoin(f'https://{road_api}', file_url)
#             print("🔗 Pavement file URL:", full_url)

#             json_response = requests.get(full_url, headers=HEADERS)
#             json_response.raise_for_status()
#             old_json_data = json_response.json()

#             # File paths
#             file_name = os.path.basename(file_url)
#             directory = os.path.join(settings.MEDIA_ROOT, "Pavement_json")
#             os.makedirs(directory, exist_ok=True)
#             file_path = os.path.join(directory, file_name)
#             backup_path = os.path.join(directory, f"backup_{file_name}")

#             # Backup old JSON
#             with open(backup_path, "w") as f:
#                 json.dump(old_json_data, f, indent=4)
#                 print(f"Backup saved to: {backup_path}")

#             # Save updated JSON
#             with open(file_path, "w") as f:
#                 json.dump(newdata, f, indent=4)
#                 print(f"Updated JSON saved to: {file_path}")

#             # Send PATCH with file
#             with open(file_path, "rb") as f:
#                 patch_response = requests.patch(
#                     api_url,
#                     files={"json_file": f},
#                     headers=HEADERS
#                 )
#             patch_response.raise_for_status()
#             print("Successfully patched pavement JSON.")

#             return JsonResponse({
#                 "message": "Pavement JSON patched successfully.",
#                 "file_path": file_path
#             }, status=200)

#         except requests.exceptions.RequestException as e:
#             return JsonResponse({"error": f"Request failed: {str(e)}"}, status=500)
#         except Exception as e:
#             return JsonResponse({"error": f"Unexpected error: {str(e)}"}, status=500)

#     return JsonResponse({"error": "Invalid HTTP method"}, status=405)


@csrf_exempt
def patch_pavement_json(request):
    if request.method == "POST":
        try:
            # Safely parse incoming data
            raw_body = request.body
            try:
                newdata = json.loads(raw_body)
                if isinstance(newdata, str):
                    newdata = json.loads(newdata)
            except json.JSONDecodeError:
                return JsonResponse(
                    {"error": "Invalid or double-encoded JSON received."}, status=400
                )

            # --- PATCH 1: Unwrap incoming data ---
            # If newdata has the {"filename": ..., "data": ...} wrapper, extract just the "data"
            if isinstance(newdata, dict) and "data" in newdata:
                newdata = newdata["data"]
            # -------------------------------------

            road_api = request.session.get("road_api")
            road_id = request.session.get("road_id")

            if not road_api or not road_id:
                return JsonResponse(
                    {"error": "Missing road_api or road_id in session"}, status=400
                )

            road_id = int(road_id)
            api_url = f"https://{road_api}/api/surveys/roads/{road_id}"

            # Fetch existing file from server
            response = requests.get(api_url, headers=HEADERS)
            response.raise_for_status()
            data = response.json()

            file_url = data.get("json_file")
            if not file_url:
                return JsonResponse(
                    {"error": "No pavement JSON file URL found."}, status=404
                )

            full_url = urljoin(f"https://{road_api}", file_url)

            json_response = requests.get(full_url, headers=HEADERS)
            json_response.raise_for_status()
            old_json_data = json_response.json()

            # --- PATCH 2: Unwrap existing server data for the backup ---
            # This ensures the backup file is also in the clean format
            if isinstance(old_json_data, dict) and "data" in old_json_data:
                old_json_data = old_json_data["data"]
            # -----------------------------------------------------------

            # File paths
            file_name = os.path.basename(file_url)
            directory = os.path.join(settings.MEDIA_ROOT, "Pavement_json")
            os.makedirs(directory, exist_ok=True)
            file_path = os.path.join(directory, file_name)
            backup_path = os.path.join(directory, f"backup_{file_name}")

            # Save clean Backup
            with open(backup_path, "w") as f:
                json.dump(old_json_data, f, indent=4)

            # Save clean Updated JSON (Without the wrapper)
            with open(file_path, "w") as f:
                json.dump(newdata, f, indent=4)

            # Send PATCH with the cleaned file
            with open(file_path, "rb") as f:
                patch_response = requests.patch(
                    api_url, files={"json_file": f}, headers=HEADERS
                )
            patch_response.raise_for_status()

            return JsonResponse(
                {
                    "message": "Pavement JSON patched successfully in backup format.",
                    "file_path": file_path,
                },
                status=200,
            )

        except requests.exceptions.RequestException as e:
            return JsonResponse({"error": f"Request failed: {str(e)}"}, status=500)
        except Exception as e:
            return JsonResponse({"error": f"Unexpected error: {str(e)}"}, status=500)

    return JsonResponse({"error": "Invalid HTTP method"}, status=405)


@never_cache
def show_pothole_pavement(request):
    data = request.session.get("uploaded_pavement_data")
    original_filename = request.session.get("original_filename")

    # Debug: Print data and original filename
    print("Session JSON Data:", data)
    print("Original Filename:", original_filename)

    if not data:
        print("No data found in session, redirecting to upload page.")
        return redirect(
            "upload_pavement_json"
        )  # Redirect to the upload page if no data in session

    index = int(request.GET.get("index", 0))
    image_type = request.GET.get("type", "Anomalies")

    items = data.get(image_type, [])

    # Debug: Print the items length and details
    print(f"Number of {image_type} items:", len(items))
    print(f"Items: {items}")

    if not items:
        current_image = None
        next_index = 0
    else:
        if index >= len(items):
            index = 0

        current_image = items[index].get("image") if index < len(items) else None
        next_index = (index + 1) % len(items)

    context = {
        "data": json.dumps(data),  # Include JSON data in the context
        "original_filename": original_filename,
        "current_image": current_image,
        "next_index": next_index,
        "type": image_type,
    }

    return render(request, "ra_testing/show_pothole_pavement.html", context)


@never_cache
def pothole_pavement_testing(request):
    road_api = request.session.get("road_api", None)
    context = {}

    if request.method == "POST":
        road_id = request.POST.get("road_id")

        if not road_id:
            context["error"] = "Road ID is required."
            return render(request, "ra_testing/potholePavement.html", context)

        road_id = int(road_id)
        request.session["road_id"] = road_id
        request.session["road_api"] = road_api
        api_url = f"https://{road_api}/api/surveys/roads/{road_id}"

        try:
            response = requests.get(api_url, headers=HEADERS)
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as e:
            context["error"] = f"Error fetching road data: {e}"
            return render(request, "ra_testing/potholePavement.html", context)

        file_url = data.get("json_file")
        if not file_url:
            context["error"] = "No JSON file URL found in the API response."
            return render(request, "ra_testing/potholePavement.html", context)

        file_url = urljoin(f"https://{road_api}", file_url)

        try:
            file_response = requests.get(file_url, headers=HEADERS)
            file_response.raise_for_status()
        except requests.RequestException as e:
            context["error"] = f"Error downloading JSON: {e}"
            return render(request, "ra_testing/potholePavement.html", context)

        try:
            json_data = file_response.json()
        except json.JSONDecodeError:
            context["error"] = "Downloaded file is not valid JSON."
            return render(request, "ra_testing/potholePavement.html", context)

        request.session["uploaded_pavement_data"] = json_data
        request.session["original_filename"] = f"road_{road_id}.json"
        return redirect("show_pothole_pavement")

    return render(request, "ra_testing/potholePavement.html", context)


@never_cache
def get_furniture_json(request):
    road_api = request.session.get("road_api", None)

    # Check if road_api is None
    if road_api is None:
        return HttpResponse("Road API not set in session.", status=400)

    if request.method == "POST":
        road_id = request.POST.get("road_id")
        if not road_id:
            return HttpResponse("Road ID is required.", status=400)

        # URL to fetch JSON data from
        api_url = f"https://{road_api}/api/surveys/roads/{road_id}"

        try:
            response = requests.get(api_url, headers=HEADERS)
            response.raise_for_status()  # Raise an error for bad responses
        except requests.RequestException as e:
            return HttpResponse(f"Error fetching data from API: {str(e)}", status=500)

        # Check if the response contains valid JSON
        try:
            data = response.json()
        except ValueError:
            return HttpResponse("Invalid JSON response from API.", status=500)

        # Extract the file URL from the response
        file_url = data.get("furniture_json")
        if not file_url:
            return HttpResponse("No JSON file URL found in the response.", status=404)

        # Ensure the file URL is absolute
        base_url = (
            f"https://{road_api}"  # Replace with the actual base URL if different
        )
        file_url = urljoin(base_url, file_url)
        print(f"File URL: {file_url}")  # Debugging output

        try:
            # Download the file from the URL
            file_response = requests.get(file_url, headers=HEADERS)
            file_response.raise_for_status()  # Raise an error for bad responses
        except requests.RequestException as e:
            return HttpResponse(f"Error downloading file: {str(e)}", status=500)

        # Create the HTTP response with the file data
        response = HttpResponse(
            file_response.content,
            content_type="application/json",
            headers={
                "Content-Disposition": f'attachment; filename="road_furniture_{road_id}.json"',
            },
        )

        return response

    # Handle GET request to display the form
    return render(request, "ra_testing/get_furniture_json.html")


class AnomalyUploadView(View):
    def get(self, request):
        return render(request, "ra_testing/upload_anomalies.html")

    def post(self, request):
        json_files = request.FILES.getlist("json_files")
        anomalies_data = []
        file_names = []

        fs = FileSystemStorage()

        # Process each uploaded JSON file
        for json_file in json_files:
            filename = fs.save(json_file.name, json_file)
            file_names.append(json_file.name)  # Store file name

            with open(fs.path(filename)) as f:
                data = json.load(f)

                # Extract only the 'assets' array from the JSON structure
                if "assets" in data:
                    anomalies_data.append(
                        {
                            "name": json_file.name,  # Add filename to data
                            "assets": data["assets"],  # Add assets to anomalies_data
                        }
                    )
                else:
                    anomalies_data.append(
                        {
                            "name": json_file.name,
                            "assets": [],  # Handle case where 'assets' may not exist
                        }
                    )

        return JsonResponse({"files": anomalies_data, "file_names": file_names})


def manual_testing(request):
    # render ('ra_testing\templates\ra_testing\upload_images.html')
    context = {}
    return render(request, "ra_testing/upload_images.html", context)


# def upload_images(request):


#     fs = FileSystemStorage()

#     if request.method == 'POST' and request.FILES.getlist('images'):
#         for image in request.FILES.getlist('images'):
#             fs.save(image.name, image)
#         return redirect('upload_images')


#     uploaded_images = FileSystemStorage().listdir('')[1]
#     context = {'uploaded_images': [{'url': fs.url(img), 'name': img} for img in uploaded_images]}
#     return render(request, 'ra_testing/upload_images.html' , context)


def upload_images(request):
    uploaded_images = []
    road_api = request.session.get("road_api", None)
    if request.method == "POST" and request.FILES.getlist("images"):
        # Get the values from the form
        model_type = request.POST.get("model_type", "default_model")
        survey_id = request.POST.get("surveyId", "default_survey")
        road_id = request.POST.get("roadId", "default_road")

        # Create the dynamic folder path
        upload_path = os.path.join(
            settings.MEDIA_ROOT,
            "Model_Testing",
            road_api,
            model_type,
            survey_id,
            road_id,
            "images",
        )
        os.makedirs(upload_path, exist_ok=True)

        # Save images in the specific folder
        fs = FileSystemStorage(location=upload_path)
        for image in request.FILES.getlist("images"):
            fs.save(image.name, image)

        # return redirect('upload_images')

        context = {
            "uploaded_images": uploaded_images,
            "survey_id": request.POST.get("surveyId", ""),
            "road_id": request.POST.get("roadId", ""),
        }
        return render(request, "ra_testing/upload_images.html", context)

    elif request.method == "GET":
        # Retrieve form values for folder structure
        model_type = request.GET.get("model_type", "default_model")
        survey_id = request.GET.get("surveyId", "default_survey")
        road_id = request.GET.get("roadId", "default_road")

        # Determine the folder to list images from
        folder_path = os.path.join(
            settings.MEDIA_ROOT,
            "Model_Testing",
            road_api,
            model_type,
            survey_id,
            road_id,
        )
        if os.path.exists(folder_path):
            for file_name in os.listdir(folder_path):
                file_path = os.path.join(folder_path, file_name)
                if os.path.isfile(file_path):  # Ensure it's a file
                    rel_path = os.path.relpath(file_path, settings.MEDIA_ROOT)
                    uploaded_images.append(
                        {
                            "url": os.path.join(settings.MEDIA_URL, rel_path).replace(
                                "\\", "/"
                            ),
                            "name": file_name,
                        }
                    )

    context = {
        "uploaded_images": uploaded_images,
        "survey_id": request.POST.get("surveyId", ""),
        "road_id": request.POST.get("roadId", ""),
    }
    return render(request, "ra_testing/upload_images.html", context)


def upload_images_pavement(request):
    uploaded_images = []
    road_api = request.session.get("road_api", None)
    if request.method == "POST" and request.FILES.getlist("images"):
        # Get the values from the form
        model_type = request.POST.get("model_type", "default_model")
        survey_id = request.POST.get("surveyId", "default_survey")
        road_id = request.POST.get("roadId", "default_road")

        # Create the dynamic folder path
        upload_path = os.path.join(
            settings.MEDIA_ROOT,
            "Model_Testing",
            road_api,
            model_type,
            survey_id,
            road_id,
            "images",
        )
        os.makedirs(upload_path, exist_ok=True)

        # Save images in the specific folder
        fs = FileSystemStorage(location=upload_path)
        for image in request.FILES.getlist("images"):
            fs.save(image.name, image)

        # return redirect('upload_images')

        context = {
            "uploaded_images": uploaded_images,
            "survey_id": request.POST.get("surveyId", ""),
            "road_id": request.POST.get("roadId", ""),
        }
        return render(request, "ra_testing/upload_images_pavement.html", context)

    elif request.method == "GET":
        # Retrieve form values for folder structure
        model_type = request.GET.get("model_type", "default_model")
        survey_id = request.GET.get("surveyId", "default_survey")
        road_id = request.GET.get("roadId", "default_road")

        # Determine the folder to list images from
        folder_path = os.path.join(
            settings.MEDIA_ROOT,
            "Model_Testing",
            road_api,
            model_type,
            survey_id,
            road_id,
        )
        if os.path.exists(folder_path):
            for file_name in os.listdir(folder_path):
                file_path = os.path.join(folder_path, file_name)
                if os.path.isfile(file_path):  # Ensure it's a file
                    rel_path = os.path.relpath(file_path, settings.MEDIA_ROOT)
                    uploaded_images.append(
                        {
                            "url": os.path.join(settings.MEDIA_URL, rel_path).replace(
                                "\\", "/"
                            ),
                            "name": file_name,
                        }
                    )

    context = {
        "uploaded_images": uploaded_images,
        "survey_id": request.POST.get("surveyId", ""),
        "road_id": request.POST.get("roadId", ""),
    }
    return render(request, "ra_testing/upload_images_pavement.html", context)


@never_cache
def fetch_images(request):
    road_api = request.session.get("road_api", None)
    if request.method == "GET":
        # Get the values from the request
        survey_id = request.GET.get("surveyId", "default_survey")
        road_id = request.GET.get("roadId", "default_road")
        model_type = request.GET.get("model_type", "default_model")

        # Construct the folder path
        folder_path = os.path.join(
            settings.MEDIA_ROOT,
            "Model_Testing",
            road_api,
            model_type,
            survey_id,
            road_id,
            "images",
        )
        images = []

        if os.path.exists(folder_path):
            for file_name in os.listdir(folder_path):
                file_path = os.path.join(folder_path, file_name)
                if os.path.isfile(file_path):
                    rel_path = os.path.relpath(file_path, settings.MEDIA_ROOT)
                    images.append(
                        {
                            "url": os.path.join(settings.MEDIA_URL, rel_path).replace(
                                "\\", "/"
                            ),
                            "name": file_name,
                        }
                    )

        return JsonResponse({"images": images})
    return JsonResponse({"error": "Invalid request method"}, status=400)


## delete the images
# def delete_image(request):
#     if request.method == 'POST':
#         image_name = request.POST.get('image_name')
#         if image_name:
#             file_path = os.path.join(FileSystemStorage().location, image_name)
#             if os.path.exists(file_path):
#                 os.remove(file_path)
#                 messages.success(request, f"Image '{image_name}' deleted successfully.")
#             else:
#                 messages.error(request, f"Image '{image_name}' not found.")
#         return redirect('upload_images')


def delete_image(request):
    if request.method == "DELETE":
        data = json.loads(request.body)
        image_name = data.get("image_name")
        survey_id = data.get("surveyId", "default_survey")
        road_id = data.get("roadId", "default_road")
        model_type = data.get("model_type", "default_model")
        road_api = request.session.get("road_api", None)
        folder_path = os.path.join(
            settings.MEDIA_ROOT,
            "Model_Testing",
            road_api,
            model_type,
            survey_id,
            road_id,
            "images",
        )
        image_path = os.path.join(folder_path, image_name)

        if os.path.exists(image_path):
            os.remove(image_path)
            return JsonResponse(
                {
                    "success": True,
                    "message": "Image deleted successfully. Please reload the page ",
                }
            )
        else:
            return JsonResponse({"success": False, "message": "Image not found."})

    return JsonResponse(
        {"success": False, "message": "Invalid request method."}, status=400
    )


def delete_all_images(request):
    road_api = request.session.get("road_api", None)
    if request.method == "DELETE":
        print("Hit POST request")

        data = json.loads(request.body)
        survey_id = data.get("surveyId", "default_survey")
        road_id = data.get("roadId", "default_road")
        model_type = data.get("model_type", "default_model")

        folder_path = os.path.join(
            settings.MEDIA_ROOT,
            "Model_Testing",
            road_api,
            model_type,
            survey_id,
            road_id,
            "images",
        )

        if os.path.exists(folder_path):
            try:
                # Delete the folder and its contents
                shutil.rmtree(folder_path)
                return JsonResponse(
                    {
                        "success": True,
                        "message": "Folder deleted successfully. Please reload the page.",
                    }
                )
            except PermissionError as e:
                return JsonResponse(
                    {"success": False, "message": f"Permission denied: {str(e)}"}
                )
            except Exception as e:
                return JsonResponse({"success": False, "message": f"Error: {str(e)}"})
        else:
            return JsonResponse({"success": False, "message": "Folder not found."})


## process unages
# def process_images(request, current_image_name=None):

#     survey_id = request.GET.get('surveyId', None)
#     road_id = request.GET.get('roadId', None)
#     model_type = request.GET.get('model_type', 'default_model')  # default to 'default_model' if not specified

#     if not survey_id or not road_id:
#         return HttpResponse("Survey ID and Road ID are required.", status=400)

#     # Construct the path to the folder where images are stored
#     base_path = os.path.join(settings.MEDIA_ROOT, "Model_Testing", road_api, model_type, survey_id, road_id , "images")

#     # Check if the directory exists
#     if not os.path.exists(base_path):
#         return HttpResponse(f"No images found for the specified Survey ID {survey_id} and Road ID {road_id}.", status=404)

#     # Get all the images from the specified folder
#     images = os.listdir(base_path)  # List all files in the folder
#     images = sorted(images)  # Optional: Sort the images alphabetically


#     if not images:
#         return HttpResponse("No images to process.", status=404)  # No images to process

#     if not current_image_name:
#         # Default to the first image if no specific image is provided
#         current_index = 0
#     else:
#         # Get the index of the current image
#         try:
#             current_index = images.index(current_image_name)
#         except ValueError:
#             return HttpResponse(f"Image {current_image_name} not found in the folder.", status=404)

#     # Determine the next and previous images
#     previous_image = images[current_index - 1] if current_index > 0 else None
#     next_image = images[current_index + 1] if current_index < len(images) - 1 else None

#     print(images , "images")

#     # Construct the correct URLs
#     def construct_image_url(image_name):
#         if image_name:
#             # Build the relative URL
#             return f"/media/{model_type}/{survey_id}/{road_id}/images/{image_name}"
#         return None

#     # Context to pass to the template
#     context = {
#         'survey_id': int(survey_id),
#         'road_id': int(road_id),
#         'model_type': model_type,
#         'current_image': {
#             'url': construct_image_url(images[current_index]),
#             'name': images[current_index]
#         },
#         'previous_image': {
#             'url': construct_image_url(previous_image),
#             'name': previous_image
#         } if previous_image else None,
#         'next_image': {
#             'url': construct_image_url(next_image),
#             'name': next_image
#         } if next_image else None,
#     }


#     # if current_image_name is not None :

#     #     return JsonResponse(context)

#     # else:

#     return render(request, 'ra_testing/process_images.html', context)

# @never_cache
# def process_images(request, current_image_name=None):


#     json_path = "ra_testing/static/ra_testing/data/data_class.json"

#     road_api = request.session.get('road_api', None)

#     if road_api is None:
#         messages.error(request, "Please select an environment first.")
#         return redirect('base_page')

#     subdomain = road_api.split('.')[0]
#     print(subdomain)  # Output: dev

#     with open(json_path) as f:
#         anomaly_data = json.load(f)


#     # Retrieve the GET parameters from the request
#     survey_id = request.GET.get('surveyId', None)
#     road_id = request.GET.get('roadId', None)
#     model_type = request.GET.get('model_type', 'default_model')  # Default to 'default_model' if not specified
#     print("let's process the images we have with us")
#     # If survey_id or road_id are not provided, return an error message
#     if not survey_id or not road_id:
#         return HttpResponse("Survey ID and Road ID are required.", status=400)

#     # Construct the path to the folder where images are stored
#     base_path = os.path.join(settings.MEDIA_ROOT, "Model_Testing", road_api, model_type, survey_id, road_id, "images")

#     # Check if the directory exists
#     if not os.path.exists(base_path):
#         return HttpResponse(f"No images found for the specified Survey ID {survey_id} and Road ID {road_id}.", status=404)

#     # Get all the images from the specified folder
#     images = os.listdir(base_path)  # List all files in the folder
#     images = sorted(images)  # Sort the images alphabetically (optional)

#     # If no images are found, return a message indicating that
#     if not images:
#         return HttpResponse("No images to process.", status=404)

#     # Default to the first image if no current_image_name is provided
#     if not current_image_name:
#         current_index = 0
#     else:
#         try:
#             # Get the index of the current image
#             current_index = images.index(current_image_name)
#         except ValueError:
#             return HttpResponse(f"Image {current_image_name} not found in the folder.", status=404)

#     # Determine the next and previous images in the list
#     previous_image = images[current_index - 1] if current_index > 0 else None
#     next_image = images[current_index + 1] if current_index < len(images) - 1 else None

#     # Function to generate the URL for the images
#     def construct_image_url(image_name):
#         if image_name:
#             return f"/media/Model_Testing/{road_api}/{model_type}/{survey_id}/{road_id}/images/{image_name}"
#         return None

#     # Context to pass to the template "Model_Testing", road_api, model_type, survey_id, road_id, "images")
#     context = {
#         'road_api': road_api,
#         'survey_id': int(survey_id),
#         'road_id': int(road_id),
#         'model_type': model_type,
#         'subdomain': subdomain,
#         "anomaly_data":anomaly_data ,
#         'current_image': {
#             'url': construct_image_url(images[current_index]),
#             'name': images[current_index]
#         },
#         'previous_image': {
#             'url': construct_image_url(previous_image),
#             'name': previous_image
#         } if previous_image else None,
#         'next_image': {
#             'url': construct_image_url(next_image),
#             'name': next_image
#         } if next_image else None,
#     }

# # Set Cache-Control headers for the response to prevent caching
# response = render(request, 'ra_testing/process_images.html', context)
# # response['Cache-Control'] = 'no-cache, no-store, must-revalidate'  # Disable caching
# response['Cache-Control'] = 'no-store, max-age=0, must-revalidate, private'
# response['Pragma'] = 'no-cache'  # For HTTP/1.0 compatibility
# response['Expires'] = '0'  # Disable cache in the past

# return response

# 1. Update the function to accept 'current_frame_number'
def get_total_existing_assets_and_anomalies(road_api, model_type, survey_id, road_id, current_frame_number):
    total_existing_assets = 0
    total_existing_anomalies = 0

    folder_path = os.path.join(settings.MEDIA_ROOT, "Model_Testing", road_api, model_type, survey_id, road_id, "jsonfile")
    file_path = os.path.join(folder_path, f"manual_{road_id}.json")

    if os.path.exists(file_path):
        try:
            with open(file_path, "r") as f:
                existing_data = json.load(f)

            if model_type == "furniture":
                # Find the prefix for the current frame, e.g., "1." or "2."
                prefix = f"{current_frame_number}."
                
                # Count only the items that start with this frame's prefix
                total_existing_assets = sum(
                    1 for a in existing_data.get("assets", []) 
                    if str(a.get("Assets number", "")).startswith(prefix)
                )
                
                total_existing_anomalies = sum(
                    1 for a in existing_data.get("anomalies", []) 
                    if str(a.get("Anomaly number", "")).startswith(prefix)
                )

            elif model_type == "pavement":
                prefix = f"{current_frame_number}."
                total_existing_assets = 0
                total_existing_anomalies = sum(
                    1 for a in existing_data.get("Anomalies", [])
                    if str(a.get("Anomaly number", "")).startswith(prefix)
                )

            else:
                total_existing_assets = 0
                total_existing_anomalies = 0

        except (json.JSONDecodeError, IOError, KeyError):
            pass
    return total_existing_assets, total_existing_anomalies





def process_images(request, current_image_name=None):

    json_path = "ra_testing/static/ra_testing/data/data_class.json"

    road_api = request.session.get("road_api", None)

    if road_api is None:
        messages.error(request, "Please select an environment first.")
        return redirect("base page")

    subdomain = road_api.split(".")[0]
    print(subdomain)  # Output: dev

    with open(json_path) as f:
        anomaly_data = json.load(f)

    # Retrieve the GET parameters from the request
    survey_id = request.GET.get("surveyId", None)
    road_id = request.GET.get("roadId", None)
    model_type = request.GET.get(
        "model_type", "default_model"
    )  # Default to 'default_model' if not specified
    print("let's process the images we have with us")
    # If survey_id or road_id are not provided, return an error message
    if not survey_id or not road_id:
        return HttpResponse("Survey ID and Road ID are required.", status=400)

    # Construct the path to the folder where images are stored
    base_path = os.path.join(
        settings.MEDIA_ROOT,
        "Model_Testing",
        road_api,
        model_type,
        survey_id,
        road_id,
        "images",
    )

    # Check if the directory exists
    if not os.path.exists(base_path):
        return HttpResponse(
            f"No images found for the specified Survey ID {survey_id} and Road ID {road_id}.",
            status=404,
        )

    # Get all the images from the specified folder
    images = os.listdir(base_path)  # List all files in the folder
    images = sorted(images)  # Sort the images alphabetically (optional)

    # If no images are found, return a message indicating that
    if not images:
        return HttpResponse("No images to process.", status=404)

    # Default to the first image if no current_image_name is provided
    if not current_image_name:
        current_index = 0
    else:
        try:
            # Get the index of the current image
            current_index = images.index(current_image_name)
        except ValueError:
            return HttpResponse(
                f"Image {current_image_name} not found in the folder.", status=404
            )

    # Determine the next and previous images in the list
    previous_image = images[current_index - 1] if current_index > 0 else None

    next_image = images[current_index + 1] if current_index < len(images) - 1 else None

    print(images, "images")

    # Function to generate the URL for the images
    def construct_image_url(image_name):
        if image_name:
            return f"/media/Model_Testing/{road_api}/{model_type}/{survey_id}/{road_id}/images/{image_name}"
        return None



        # Ensure current image has its local path resolved
    local_img_path = os.path.join(base_path, images[current_index])
    
    # Precalculate variables
    fetched_timestamp_from_image = ""
    next_timestamp = ""
    prev_timestamp = ""
    
    # 1. Fetch current timestamp
    precalculated_ts = request.GET.get('precalculated_ts', None)
    if precalculated_ts:
        fetched_timestamp_from_image = precalculated_ts
    else:
        fetched_timestamp_from_image = ocr.fetch_timestamp(local_img_path)

    
    # 2. Fetch previous timestamp (if a previous image exists)
    if previous_image:
        prev_img_path = os.path.join(base_path, previous_image)
        prev_timestamp = ocr.fetch_timestamp(prev_img_path)
        
    # 3. Fetch next timestamp (if a next image exists)
    if next_image:
        next_img_path = os.path.join(base_path, next_image)
        next_timestamp = ocr.fetch_timestamp(next_img_path)


    # 4. Count existing assets or anomalies to fix numbering reset issue
    current_frame_number = current_index + 1
    total_existing_assets, total_existing_anomalies = get_total_existing_assets_and_anomalies(road_api, model_type, survey_id, road_id, current_frame_number)

    # Context to pass to the template
    context = {
        "survey_id": int(survey_id),
        "road_id": int(road_id),
        "model_type": model_type,
        "subdomain": subdomain,
        "anomaly_data": anomaly_data,
        "current_image": {
            "url": construct_image_url(images[current_index]),
            "name": images[current_index],
        },
        "current_frame_number": current_frame_number,
        "fetched_timestamp_from_image": fetched_timestamp_from_image,
        "prev_timestamp": prev_timestamp,
        "next_timestamp": next_timestamp,
        "total_frames": len(images),
        "total_existing_assets": total_existing_assets,
        "total_existing_anomalies": total_existing_anomalies,
        "previous_image": (
            (
                {"url": construct_image_url(previous_image), "name": previous_image}
                if previous_image
                else None
            )
        ),
        "next_image": (
            {"url": construct_image_url(next_image), "name": next_image}
            if next_image
            else None
        ),
    }
    # Set Cache-Control headers for the response to prevent caching
    response = render(request, "ra_testing/process_images.html", context)
    # response['Cache-Control'] = 'no-cache, no-store, must-revalidate'  # Disable caching
    response["Cache-Control"] = "no-store, max-age=0, must-revalidate, private"
    response["Pragma"] = "no-cache"  # For HTTP/1.0 compatibility
    response["Expires"] = "0"  # Disable cache in the past

    return response


def road_data(request, roadId):
    print("Received request for road ID:", roadId)

    if roadId:
        url = f"https://dev.road.com/api/surveys/roads/{roadId}"
        try:
            response = requests.get(url, headers=HEADERS)
            response.raise_for_status()  # Raise an exception for HTTP errors
            return JsonResponse(response.json(), safe=False)  # Return the API response
        except requests.exceptions.RequestException as e:
            print(f"API Request failed: {e}")
            return JsonResponse(
                {"error": "Failed to fetch data from external API"}, status=500
            )

    return JsonResponse({"error": "Road ID not provided"}, status=400)


# @csrf_exempt


def save_anomalies(request):
    """
    Saves or updates assets and anomalies data to a JSON file.
    This view is designed to handle different payload structures based on the 'modelType'.
    - For 'furniture', it expects 'assets' and 'anomalies' lists.
    - For 'pavement', it expects an 'Anomalies' list.
    """
    if request.method != "POST":
        return JsonResponse(
            {"error": "Invalid request method. Only POST is allowed."}, status=405
        )

    try:
        data = json.loads(request.body)
        road_api = request.session.get("road_api", None)
        # --- 1. Extract Metadata from Request ---
        survey_id = data.get("surveyId")
        road_id = data.get("roadId")
        model_type = data.get("modelType")

        if not all([survey_id, road_id, model_type]):
            return JsonResponse(
                {"error": "Missing required fields: surveyId, roadId, or modelType."},
                status=400,
            )

        # --- 2. Define File Path and Ensure Directory Exists ---
        base_dir = "media"
        folder_path = os.path.join(
            base_dir,
            "Model_Testing",
            str(road_api),
            str(model_type),
            str(survey_id),
            str(road_id),
            "jsonfile",
        )
        os.makedirs(folder_path, exist_ok=True)
        file_path = os.path.join(folder_path, f"manual_{road_id}.json")

        # --- 3. Load Existing Data or Initialize Correct Structure ---
        existing_data = {}
        if os.path.exists(file_path):
            with open(file_path, "r") as json_file:
                # Handle cases where the file might be empty or corrupted
                try:
                    existing_data = json.load(json_file)
                except json.JSONDecodeError:
                    pass  # Keep existing_data as {}

        # Ensure the base structure is correct for the model type
        if model_type == "furniture":
            if "assets" not in existing_data:
                existing_data["assets"] = []
            if "anomalies" not in existing_data:
                existing_data["anomalies"] = []
        elif model_type == "pavement":
            if "Anomalies" not in existing_data:
                existing_data["Anomalies"] = []

        # --- 4. THE CORE LOGIC: Process and Append New Data Correctly ---

        # Process ASSETS (only applies to furniture)
        new_assets = data.get(
            "assets", []
        )  # Safely get new assets, default to empty list
        if new_assets and "assets" in existing_data:
            print(f"Received {len(new_assets)} new assets.")
            for asset in new_assets:
                if asset not in existing_data["assets"]:
                    existing_data["assets"].append(asset)

        # Process ANOMALIES (handles both furniture and pavement structures)
        # Pavement uses 'Anomalies' key, Furniture uses 'anomalies'
        anomaly_key = "Anomalies" if model_type == "pavement" else "anomalies"
        new_anomalies = data.get(anomaly_key, [])  # Safely get new anomalies

        if new_anomalies and anomaly_key in existing_data:
            print(
                f"Received {len(new_anomalies)} new anomalies for key '{anomaly_key}'."
            )
            for anomaly in new_anomalies:
                if anomaly not in existing_data[anomaly_key]:
                    existing_data[anomaly_key].append(anomaly)

        # --- 5. Write the Updated Data Back to the File ---
        with open(file_path, "w") as json_file:
            json.dump(existing_data, json_file, indent=2)

        return JsonResponse({"message": "Data saved successfully!"}, status=200)

    except json.JSONDecodeError:
        return JsonResponse(
            {"error": "Invalid JSON format in request body."}, status=400
        )
    except Exception as e:
        # Log the exception for debugging
        print(f"An unexpected error occurred: {e}")
        return JsonResponse(
            {"error": f"An internal server error occurred: {e}"}, status=500
        )


@csrf_exempt
def upload_gpx_json(request, survey_id, road_id, model_type):

    MEDIA_ROOT = "media"
    if request.method == "POST":
        uploaded_file = request.FILES.get("gpxJson")
        if not uploaded_file:
            return JsonResponse({"error": "No file uploaded"}, status=400)

        # Save file to the specified path
        save_dir = os.path.join(
            MEDIA_ROOT, model_type, f"survey_{survey_id}", f"road_{road_id}", "gpx"
        )
        os.makedirs(save_dir, exist_ok=True)
        save_path = os.path.join(save_dir, f"{road_id}_gpx.json")

        # Remove the existing file if it exists
        if os.path.exists(save_path):
            print(f"File {save_path} already exists. Removing it.")
            os.remove(save_path)

        with open(save_path, "wb") as file:
            for chunk in uploaded_file.chunks():
                file.write(chunk)

        return JsonResponse(
            {"message": "File uploaded successfully", "path": save_path}
        )
    return JsonResponse({"error": "Invalid request method"}, status=405)


def download_gpx_file(request):

    if request.method == "GET":
        return JsonResponse({"error": "Road ID not provided"}, status=400)

    if request.method == "POST":
        try:
            data = json.loads(request.body)
            print("found data post helloo there ...........", data)
            survey_id = data["surveyId"]
            road_id = data["roadId"]
            model_type = data["modelType"]

        except Exception as e:
            print("errpr ")

        FILE_BASE_URL = f"https://{request.session.get('road_api', None)}"
        print("file based ", FILE_BASE_URL)

        API_BASE_URL = f"{FILE_BASE_URL}/api/surveys/roads/{road_id}"
        OUTPUT_DIR = "media"
        save_file_path = os.path.join(
            "media",
            model_type,
            f"survey_{survey_id}",
            f"road_{road_id}",
            "gpx",
            f"{road_id}_gpx.json",
        )
        # Fetch JSON metadata
        response = requests.get(API_BASE_URL, headers=HEADERS)
        if response.status_code == 200:

            if not os.path.exists(save_file_path):

                json_data = response.json()

                # Extract GPX file URL
                gpx_file_url = json_data.get("gpx_file")
                if not gpx_file_url:
                    return JsonResponse(
                        {"error": "GPX file not found in the API response"}, status=404
                    )

                full_gpx_url = f"{FILE_BASE_URL}{gpx_file_url}"

                # Download the GPX file
                file_response = requests.get(full_gpx_url, headers=HEADERS)
                if file_response.status_code == 200:
                    # Create directory structure for saving files
                    output_path = os.path.join(
                        OUTPUT_DIR,
                        model_type,
                        f"survey_{survey_id}",
                        f"road_{road_id}",
                        "gpx",
                    )
                    os.makedirs(output_path, exist_ok=True)

                    # Save the file locally
                    file_path = os.path.join(output_path, "gpx_file.gpx")

                    with open(file_path, "wb") as file:
                        file.write(file_response.content)

                    gpx_processor = GPXProcessor()
                    gpx_file_path = file_path

                    gpx_processor.parse_gpx(gpx_file_path, save_file_path)
                    print("GPX processing completed!")

                ## NOW CONVERTING THE GPX FILE TO JSON

            # Return the file as a response
            with open(save_file_path, "rb") as file:
                response = HttpResponse(file.read(), content_type="application/json")
                response["Content-Disposition"] = (
                    f'attachment; filename="{road_id}_gpx.json"'
                )
                return response
        else:
            return JsonResponse({"error": "Failed to download GPX file"}, status=404)

    else:
        return JsonResponse(
            {"error": f"Failed to fetch API data: {response.status_code}"},
            status=response.status_code,
        )


# def upload_s32(request):
#     if request.method == "POST":
#         # Get the data from the request
#         data = json.loads(request.body)
#         survey_id = data.get("surveyId")
#         road_id = data.get("roadId")
#         model_type = data.get("modelType")
#         image = data.get("image")  # Image path to upload

#         print("Received data:", data)

#         # Create an S3 client
#         # //s3_client = boto3.client('s3')

#         # Get the full file path by joining the media root and the image path
#         # Remove the leading '/media' from the image path to append it to MEDIA_ROOT
#         file_path = os.path.join(settings.MEDIA_ROOT, image.lstrip("/media")).replace(
#             "\\", "/"
#         )

#         # Extract directory and file name
#         directory, file_name = os.path.split(file_path)

#         # Replace blank spaces in the file name with '+'
#         new_file_name = file_name.replace(" ", "_")

#         # Construct the new file path
#         new_file_path = os.path.join(directory, new_file_name).replace("\\", "/")

#         # Rename the file
#         if os.path.exists(file_path):
#             os.rename(file_path, new_file_path)
#             print(f"File renamed to: {new_file_path}")
#             file_path = new_file_path
#         else:
#             print(f"Original file not found: {file_path}")
#             print("File path:", file_path)

#         # S3 path to store the image
#         s3_path = f"{model_type}/output/frames/survey_{survey_id}/road_{road_id}/{new_file_name}"
#         ## fill s3-path
#         # s3_path = s3_path.replace(" " , "_")
#         print("S3 path:", s3_path)

#         if os.path.exists(file_path):
#             print("path exists ")
#             print(AWS_STORAGE_BUCKET_NAME)

#         # Check if the file exists before uploading
#         if os.path.exists(file_path):

#             with open(file_path, "rb") as file:
#                 s3_client.upload_fileobj(
#                     file,
#                     AWS_STORAGE_BUCKET_NAME,
#                     s3_path,
#                     ExtraArgs={"ACL": "public-read"},
#                 )

#             return JsonResponse({"message": "Image uploaded successfully!"})
#         else:
#             return JsonResponse(
#                 {"message": f"File {image} does not exist on the server."}, status=400
#             )

#     return JsonResponse({"message": "Invalid request method."}, status=400)


@csrf_exempt
def upload_s3(request):

    road_api = request.session.get("road_api", None)

    subdomain = road_api.split(".")[0]
    print(subdomain)  # Output: dev
    if request.method == "POST":
        update_image = True
        survey_id = request.POST.get("surveyId")
        road_id = request.POST.get("roadId")
        model_type = request.POST.get("modelType")
        image = request.FILES.get("image")  # Uploaded image file
        original_file_name = request.POST.get("originalFileName")

        s3_folder_path = request.POST.get("s3Folder")

        if not all([survey_id, road_id, model_type, image]):
            return JsonResponse({"message": "Missing required fields."}, status=400)

        if update_image:
            print(original_file_name)
            # original_file_name = original_file_name.split('?')[0]
            file_path = os.path.join(
                settings.MEDIA_ROOT, original_file_name.lstrip("/media")
            ).replace("\\", "/")

            if os.path.exists(file_path):
                # Save the new image file to the updated path
                with open(file_path, "wb+") as destination:
                    for chunk in image.chunks():
                        destination.write(chunk)
                print(f"New image saved at: {file_path}")

            else:
                print(f"Original file not found: {file_path}")
                return JsonResponse({"message": "Original file not found."}, status=400)

        if s3_folder_path:

            s3_path = f"output/{subdomain}/{model_type}/{s3_folder_path}/frames/survey_{survey_id}/road_{road_id}/{image.name}"

        else:

            s3_path = f"output/{subdomain}/{model_type}/frames/survey_{survey_id}/road_{road_id}/{image.name}"

        print(s3_path, "path ")

        try:

            image.seek(0)
            # Upload image to S3
            s3_client.upload_fileobj(
                image,
                AWS_STORAGE_BUCKET_NAME,
                s3_path,
                ExtraArgs={"ACL": "public-read"},
            )
            return JsonResponse(
                {
                    "message": "Image uploaded successfully!",
                    "s3_url": f"https://{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com/{s3_path}",
                }
            )
        except Exception as e:
            return JsonResponse(
                {"message": f"Failed to upload image to S3. {str(e)}", "error": str(e)},
                status=500,
            )


##  download the json file
def download_json(request, survey_id, road_id, model_type):
    road_api = request.session.get("road_api", None)
    try:
        # Construct the file path from the provided parameters
        file_path = os.path.join(
            "media",
            "Model_Testing",
            road_api,
            model_type,
            survey_id,
            road_id,
            "jsonfile",
            f"manual_{road_id}.json",
        )

        # Check if the file exists
        if os.path.exists(file_path):
            with open(file_path, "r") as file:
                json_data = file.read()

            # Return the file as a downloadable response
            response = HttpResponse(json_data, content_type="application/json")
            response["Content-Disposition"] = (
                f"attachment; filename=manual_{road_id}.json"
            )
            return response
        else:
            return JsonResponse({"error": "File not found"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


## delete the json file
def delete_json(request, survey_id, road_id, model_type):
    road_api = request.session.get("road_api", None)
    try:
        # Construct the file path from the provided parameters
        file_path = os.path.join(
            "media",
            "Model_Testing",
            road_api,
            model_type,
            survey_id,
            road_id,
            "jsonfile",
            f"manual_{road_id}.json",
        )
        # Check if the file exists
        if os.path.exists(file_path):
            os.remove(file_path)  # Delete the file
            return JsonResponse({"message": "File deleted successfully!"}, status=200)
        else:
            return JsonResponse({"error": "File not found"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def merge_json(request, survey_id, road_id, model_type):
    """
    Fetches a "dashboard" JSON from an external API, merges it with a local "manual" JSON,
    and returns the merged file for download. This function is dynamic and handles
    both 'furniture' and 'pavement' model types and their unique data structures.
    """
    if request.method != "GET":
        return JsonResponse(
            {"error": "Invalid request method. Only GET is allowed."}, status=405
        )

    try:
        # --- Step 1: Set up paths and URLs ---
        road_api_url = request.session.get("road_api")
        if not road_api_url:
            return JsonResponse(
                {"error": "Session expired or 'road_api' not found."}, status=400
            )

        FILE_BASE_URL = f"https://{road_api_url}"
        API_BASE_URL = f"{FILE_BASE_URL}/api/surveys/roads/{road_id}"

        output_path = os.path.join(
            "media",
            "Model_Testing",
            str(road_api_url),
            str(model_type),
            str(survey_id),
            str(road_id),
            "jsonfile",
        )
        os.makedirs(output_path, exist_ok=True)

        manual_file_path = os.path.join(output_path, f"manual_{road_id}.json")
        dashboard_file_path = os.path.join(output_path, f"dashboard_{road_id}.json")
        merged_file_path = os.path.join(output_path, f"merged_{road_id}.json")

        # --- Step 2: Fetch and Download the Dashboard JSON ---
        print(f"Fetching metadata from: {API_BASE_URL}")
        meta_response = requests.get(API_BASE_URL, headers=HEADERS)
        if meta_response.status_code != 200:
            return JsonResponse(
                {
                    "error": f"Failed to fetch metadata from API. Status: {meta_response.status_code}"
                },
                status=502,
            )

        meta_json = meta_response.json()

        # *** THIS IS THE CORRECTED LOGIC ***
        # Determine which key to use to find the JSON file URL in the API response.
        if model_type == "furniture":
            # For furniture, we expect the 'furniture_json' key.
            json_file_url = meta_json.get("furniture_json")
            json_url_key = "furniture_json"
        else:
            # For other models like 'pavement', we expect the generic 'json_file' key.
            json_file_url = meta_json.get("json_file")
            json_url_key = "json_file"
        # *** END OF CORRECTION ***

        if not json_file_url:
            return JsonResponse(
                {
                    "error": f"'{json_url_key}' key not found in API response for road {road_id}"
                },
                status=404,
            )

        full_json_url = f"{FILE_BASE_URL}{json_file_url}"
        print(f"Downloading dashboard JSON from: {full_json_url}")
        file_response = requests.get(full_json_url, headers=HEADERS)
        if file_response.status_code != 200:
            return JsonResponse(
                {
                    "error": f"Failed to download dashboard JSON file. Status: {file_response.status_code}"
                },
                status=502,
            )

        with open(dashboard_file_path, "wb") as file:
            file.write(file_response.content)
        print(f"Dashboard JSON saved to: {dashboard_file_path}")

        # --- Step 3: Load Both Local JSON Files ---
        manual_data = {}
        if os.path.exists(manual_file_path):
            with open(manual_file_path, "r", encoding="utf-8") as file:
                manual_data = json.load(file)

        with open(dashboard_file_path, "r", encoding="utf-8") as file:
            dashboard_data = json.load(file)

        # --- Step 4: Merge Data Based on Model Type ---
        merged_data = {}
        if model_type == "furniture":
            print("Merging data for 'furniture' model...")
            merged_data["anomalies"] = _deduplicate_lists(
                manual_data.get("anomalies", []),
                dashboard_data.get("anomalies", []),
                key_fields=(
                    "Anomaly number",
                    "Latitude",
                    "Longitude",
                    "Timestamp on processed video",
                ),
            )
            merged_data["assets"] = _deduplicate_lists(
                manual_data.get("assets", []),
                dashboard_data.get("assets", []),
                key_fields=(
                    "Assets number",
                    "Latitude",
                    "Longitude",
                    "Timestamp on processed video",
                ),
            )

        elif model_type == "pavement":
            print("Merging data for 'pavement' model...")
            merged_data["Anomalies"] = _deduplicate_lists(
                manual_data.get("Anomalies", []),
                dashboard_data.get("Anomalies", []),
                key_fields=(
                    "Anomaly number",
                    "Latitude",
                    "Longitude",
                    "Timestamp on processed video",
                ),
            )

        else:
            return JsonResponse(
                {"error": f"Unknown model_type: {model_type}"}, status=400
            )

        # --- Step 5: Save Merged JSON and Return for Download ---
        with open(merged_file_path, "w", encoding="utf-8") as file:
            json.dump(merged_data, file, indent=4)
        print(f"Merged JSON saved to: {merged_file_path}")

        response = HttpResponse(
            json.dumps(merged_data, indent=4), content_type="application/json"
        )
        response["Content-Disposition"] = (
            f'attachment; filename="merged_{road_id}.json"'
        )
        return response

    except Exception as e:
        print(f"An unexpected error occurred in merge_json: {e}")
        return JsonResponse({"error": str(e)}, status=500)


def _deduplicate_lists(list1, list2, key_fields):
    """A helper function to merge two lists of dictionaries and remove duplicates."""
    seen_identifiers = set()
    merged_list = []

    for item in list1 + list2:
        identifier = tuple(item.get(key) for key in key_fields)

        if identifier not in seen_identifiers:
            seen_identifiers.add(identifier)
            merged_list.append(item)

    return merged_list


def user_session_folder():
    print("making the folder structure for the user")
    user_folder_path = os.path.join(
        settings.MEDIA_ROOT,
        "excelmerge",
        f"my_session{datetime.now().strftime('%Y%m%d%H%M%S')}",
    )

    if not os.path.exists(user_folder_path):
        os.makedirs(user_folder_path)

    subfolders = ["MCW", "CL", "CR", "generated_files", "Jsons", "SL", "SR", "TL", "TR"]
    for subfolder in subfolders:
        subfolder_path = os.path.join(user_folder_path, subfolder)
        if not os.path.exists(subfolder_path):
            os.makedirs(subfolder_path)

    return user_folder_path


def assign_folder_to_session(request):
    print("i am here to assign folder structure to the session")
    user_folder = user_session_folder()

    # Store the folder path in the session
    request.session["user_folder"] = user_folder


def merge_excel(request):
    # Delete all session data for the current user
    request.session.flush()
    # print("session deleted successfully")

    print("the session key is ,", request.session.session_key)
    # session at the entry point
    if not request.session.session_key:
        print("i am here")
        request.session.create()
        request.session["visitor_id"] = str(uuid.uuid4())
        print("session created with id ", request.session["visitor_id"])
        request.session["visit_count"] = 0
        user_folder = assign_folder_to_session(request)

    visitor_id = request.session.get("visitor_id")
    visit_count = request.session.get("visit_count", 0)
    user_folder = request.session.get("user_folder")

    request.session["visit_count"] = visit_count + 1
    print(
        f"Welcome! Your session ID is: {visitor_id}, You have visited {visit_count + 1} times."
    )
    print("The folder assigned to user is : ", user_folder)
    if request.method == "POST" and request.FILES.getlist("files"):
        uploaded_files = request.FILES.getlist("files")
        dfs = []

        # Validate that files are Excel files
        for file in uploaded_files:
            # Check if the file is an Excel file based on its extension
            if not (file.name.endswith(".xls") or file.name.endswith(".xlsx")):
                return HttpResponse(
                    "Invalid file type. Please upload only Excel files.", status=400
                )

            # Save the uploaded file
            fs = FileSystemStorage()
            filename = fs.save(file.name, file)
            filepath = fs.path(filename)  # Get the full path of the file saved

            # Read the Excel file
            try:
                df = pd.read_excel(filepath)
                dfs.append(df)
            except Exception as e:
                return HttpResponse(f"Error reading {file.name}: {e}", status=500)

        # Merge all dataframes
        merged_df = pd.concat(dfs, ignore_index=True)

        # Save merged dataframe to a temporary file
        merged_file_path = "merged_output.xlsx"
        merged_df.to_excel(merged_file_path, index=False)

        # Serve the merged file for download
        with open(merged_file_path, "rb") as merged_file:
            response = HttpResponse(
                merged_file.read(),
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
            response["Content-Disposition"] = (
                'attachment; filename="merged_output.xlsx"'
            )

        # Clean up the temporary file after serving
        os.remove(merged_file_path)

        return response

    return render(request, "ra_testing/excelmerge.html")


def get_files_in_folder(request, folder_name):
    print("i am here as per the call ", folder_name)
    # Path to the base folder containing the subfolders
    user_folder = request.session.get("user_folder", None)
    # print("the folder is " ,user_folder)
    base_path = f"{user_folder}"
    # Build the full folder path
    folder_path = os.path.join(base_path, folder_name)

    print("folder path is in get files in folder ", folder_path)
    print("folder hai ki nhi ", os.path.isdir(folder_path))

    if os.path.exists(folder_path) and os.path.isdir(folder_path):
        # List all files in the folder
        files = os.listdir(folder_path)
        print("i am here")
        return JsonResponse({"files": files})
    else:
        print("no files are found")
        return JsonResponse({"error": "Folder not found"}, status=404)


@csrf_exempt  # Disable CSRF for testing; remove in production if CSRF is properly handled
def upload_file(request, folder_name):
    if request.method == "POST":
        user_folder = request.session.get("user_folder", None)
        base_path = f"{user_folder}"
        uploaded_files = request.FILES.getlist("files[]")
        print("Files uploaded:", uploaded_files)

        folder_path = os.path.join(base_path, folder_name)
        print("This is the path:", folder_path)

        # Ensure the folder exists
        if not os.path.exists(folder_path):
            print("Folder does not exist, creating it...")
            os.makedirs(folder_path)

        if not uploaded_files:
            return JsonResponse({"error": "No files provided"}, status=400)

        for uploaded_file in uploaded_files:
            # Get the path to save the file
            file_path = os.path.join(folder_path, uploaded_file.name)
            print(file_path)

            # Save the file
            with open(file_path, "wb+") as destination:
                for chunk in uploaded_file.chunks():
                    destination.write(chunk)

            print(f"File {uploaded_file.name} saved successfully.")

        return JsonResponse(
            {
                "message": "Files uploaded successfully",
                "files": [file.name for file in uploaded_files],
            }
        )
    else:
        return JsonResponse({"error": "Invalid request method"}, status=405)


@csrf_exempt  # For testing; use CSRF tokens in production
def delete_files(request, folder_name):
    user_folder = request.session.get("user_folder", None)
    base_path = f"{user_folder}"
    if request.method == "POST":
        folder_path = os.path.join(base_path, folder_name)

        # Check if the folder exists
        if not os.path.exists(folder_path):
            return JsonResponse(
                {"error": f"Folder '{folder_name}' does not exist"}, status=404
            )

        # Delete all files in the folder
        try:
            for file_name in os.listdir(folder_path):
                file_path = os.path.join(folder_path, file_name)
                if os.path.isfile(file_path):
                    os.remove(file_path)

            return JsonResponse(
                {"message": f"All files in '{folder_name}' deleted successfully"}
            )
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    else:
        return JsonResponse({"error": "Invalid request method"}, status=405)


@csrf_exempt  # For testing; use CSRF tokens in production
def run_script_excel(request, folder_name):
    if request.method == "POST":
        print("inside post")
        user_folder = request.session.get("user_folder", None)
        base_path = f"{user_folder}"
        folder_path = os.path.join(base_path, folder_name)
        print("path of the folder ", folder_path)

        output_json_path = os.path.join(base_path, "Jsons/MCW.json")

        try:
            print("inside try")
            # Call the function to generate the JSON file
            if folder_name == "MCW":
                folder_path = os.path.join(base_path, folder_name)
                print("path of the folder ", folder_path)
                output_json_path = os.path.join(base_path, f"Jsons/{folder_name}.json")
                generate_json_from_M_final(folder_path, output_json_path)

            if folder_name == "SL":
                folder_path = os.path.join(base_path, folder_name)
                print("path of the folder ", folder_path)
                output_json_path = os.path.join(base_path, f"Jsons/{folder_name}.json")
                generate_json_from_SL_final(folder_path, output_json_path)

            if folder_name == "SR":
                folder_path = os.path.join(base_path, folder_name)
                print("path of the folder ", folder_path)
                output_json_path = os.path.join(base_path, f"Jsons/{folder_name}.json")
                generate_json_from_SR_final(folder_path, output_json_path)

            if folder_name == "CL":
                folder_path = os.path.join(base_path, folder_name)
                print("path of the folder ", folder_path)
                output_json_path = os.path.join(base_path, f"Jsons/{folder_name}.json")
                generate_json_from_CL_Final(folder_path, output_json_path)

            if folder_name == "CR":
                folder_path = os.path.join(base_path, folder_name)
                print("path of the folder ", folder_path)
                output_json_path = os.path.join(base_path, f"Jsons/{folder_name}.json")
                generate_json_from_CR_Final(folder_path, output_json_path)

            if folder_name == "TL":
                folder_path = os.path.join(base_path, folder_name)
                print("path of the folder ", folder_path)
                output_json_path = os.path.join(base_path, f"Jsons/{folder_name}.json")
                generate_json_from_TL_Final(folder_path, output_json_path)

            if folder_name == "TR":
                folder_path = os.path.join(base_path, folder_name)
                print("path of the folder ", folder_path)
                output_json_path = os.path.join(base_path, f"Jsons/{folder_name}.json")
                generate_json_from_TR_Final(folder_path, output_json_path)

            return JsonResponse(
                {"message": f"Script executed successfully for folder '{folder_name}'"}
            )

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    else:
        return JsonResponse({"error": "Invalid request method"}, status=405)


@csrf_exempt
def handle_json_data(request):

    if request.method == "POST":

        user_folder = request.session.get("user_folder", None)
        base_path = f"{user_folder}"
        print("base path in handle json data function ", base_path)

        try:

            data = json.loads(request.body)

            road_id = data.get("road_id")
            excel_name = data.get("name_excel")
            print("road id ", road_id)
            print("excel_name ", excel_name)

            final_colur_format(road_id, headers=HEADERS)

            excel_updation(excel_name, session_folder_path=base_path)

            print("Excel is ready now i want to print it ")

            file_path = os.path.join(base_path, f"generated_files/{excel_name}.xlsx")
            print("file path for generated files is  ", file_path)

            print("checking thr existence of the file path ", os.path.exists(file_path))

            if os.path.exists(file_path):
                print("generated files path exists with name file path")
                with open(file_path, "rb") as excel_file:
                    response = HttpResponse(
                        excel_file.read(),
                        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )
                    response["Content-Disposition"] = (
                        f'attachment; filename="{excel_name}.xlsx"'
                    )
                    print("ready with the response to download ")
                    return response
            else:
                return JsonResponse(
                    {"status": "error", "message": "File not found"}, status=404
                )

            return JsonResponse(
                {
                    "status": "success",
                    "road_id": road_id,
                }
            )

        except json.JSONDecodeError:

            return JsonResponse({"status": "error", "message": "Invalid road id"})

    else:

        return JsonResponse(
            {"status": "error", "message": "Only POST requests are allowed"}
        )


def index(request):
    return render(request, "ra_testing/gpx_app.html")


df = pd.read_excel("ra_testing/media/Es2.xlsx")  # adjust path if needed
excel_dict = df.set_index("Figure no.").to_dict("index")


def FilterRoadSign(request):
    result_file = None
    if request.method == "POST":
        fig_input = request.POST.get("figures", "")
        fig_list = [fig.strip() for fig in fig_input.split(",") if fig.strip()]

        # Extract matching rows
        filtered_rows = [excel_dict[fig] for fig in fig_list if fig in excel_dict]

        if filtered_rows:
            result_df = pd.DataFrame(filtered_rows)
            result_df.insert(
                0, "Figure No", fig_list[: len(result_df)]
            )  # re-add index column

            output = BytesIO()
            result_df.to_excel(output, index=False)
            output.seek(0)

            response = HttpResponse(
                output.read(),
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
            response["Content-Disposition"] = (
                "attachment; filename=filtered_figures.xlsx"
            )
            return response

    return render(request, "ra_testing/filterRoadSign.html")


def download_gpx(request):
    if request.method == "POST":
        try:
            # Receive and parse the incoming JSON data
            data = json.loads(request.body.decode("utf-8"))

            # Change 'roads' to 'road' to handle a single road
            road = data.get("road")
            if not road:
                return JsonResponse({"error": "No road data provided."}, status=400)

            road_name = road.get(
                "name", "road_1"
            )  # Provide a default name if none is given
            points = road.get("points", [])

            if not points:
                return JsonResponse(
                    {"error": "No points provided for the road."}, status=400
                )

            # Generate GPX string for the road
            gpx_string = generate_gpx(points, road_name)

            # Encode GPX string to Base64 to safely include in JSON
            gpx_base64 = base64.b64encode(gpx_string.encode("utf-8")).decode("utf-8")

            # Create a single gpx_file dictionary
            gpx_file = {
                "filename": f"{sanitize_filename(road_name)}.gpx",
                "data": gpx_base64,
            }

            # Return the single gpx_file in the response
            return JsonResponse({"gpx_file": gpx_file}, status=200)

        except Exception as e:
            return JsonResponse(
                {"error": f"Error processing data: {str(e)}"}, status=500
            )
    else:
        return JsonResponse({"error": "Only POST method is allowed."}, status=405)


def sanitize_filename(name):
    """
    Sanitize the filename by replacing unsafe characters.
    """
    import re

    return re.sub(r"[^a-zA-Z0-9_\- ]", "_", name)


def generate_gpx(road, road_name):
    """
    Generate a GPX file string for a single road.

    :param road: A list of point dicts:
                 [ { "lat": <float>, "lon": <float>, "time": <string> }, ... ]
    :param road_name: The name of the road to use in the GPX file.
    :return: A string containing valid GPX data for the road.
    """
    # GPX header
    gpx_header = """<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="MyApp"
     xmlns="http://www.topografix.com/GPX/1/1"
     xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
     xsi:schemaLocation="http://www.topografix.com/GPX/1/1
                         http://www.topografix.com/GPX/1/1/gpx.xsd">
"""

    # Start the track
    gpx_content = [gpx_header]
    gpx_content.append(f"  <trk>\n")
    gpx_content.append(f"    <name>{road_name}</name>\n")
    gpx_content.append(f"    <trkseg>\n")

    # Add points
    for p in road:
        lat = p.get("lat", 0)
        lon = p.get("lng", 0)  # Ensure correct key
        time_str = p.get("time") if "time" in p else datetime.utcnow().isoformat() + "Z"
        gpx_content.append(f'      <trkpt lat="{lat}" lon="{lon}">\n')
        gpx_content.append(f"        <time>{time_str}</time>\n")
        gpx_content.append(f"      </trkpt>\n")

    # Close track segment and track
    gpx_content.append(f"    </trkseg>\n")
    gpx_content.append(f"  </trk>\n")
    gpx_content.append("</gpx>\n")

    return "".join(gpx_content)


def gpx_processor_index(request):
    form = GpxUploadForm()
    return render(request, "ra_testing/gpxProcessor.html", {"form": form})


def upload_gpx(request):
    print("started")
    if request.method == "POST":
        print("post")
        form = GpxUploadForm(request.POST, request.FILES)
        print("request.FILES:", request.FILES)
        # if form.is_valid():
        print("form is valid")
        gpx_files = request.FILES.getlist("gpx_file")
        print("i have the gpx files")
        all_files_data = []

        for file in gpx_files:

            gpx = gpxpy.parse(file.read().decode("utf-8", errors="ignore"))

            points_list = []
            # [{l,l,t},{l,l,t}]
            for track in gpx.tracks:
                for segment in track.segments:
                    for point in segment.points:
                        points_list.append(
                            {
                                "lat": point.latitude,
                                "lng": point.longitude,
                                "time": (
                                    point.time.strftime("%Y-%m-%dT%H:%M:%S")
                                    if point.time
                                    else None
                                ),
                            }
                        )
            all_files_data.append({"file_name": file.name, "points": points_list})
        request.session["uploaded_points"] = all_files_data
        print("going in session", all_files_data)
        return redirect("gpx_processor:map_edit")

    return render(request, "ra_testing/gpxProcessor.html", {"form": form})


def map_edit(request):
    files_data = request.session.get("uploaded_points", [])
    # print("take from session",points_list)
    files_data = json.dumps(files_data)
    context = {
        "files_data": files_data,
        "google_maps_api_key": "AIzaSyAtVXosLTQjTMVm2K9BJf55HZAkNAGTr4U",
    }

    return render(request, "ra_testing/map_edit.html", context)


def update_gpx(request):
    if request.method == "POST":
        updated_points = request.POST.get("points_json")
        if not updated_points:
            return HttpResponse("No points provided", status=400)

        points_data = json.loads(updated_points)

        gpx = gpxpy.gpx.GPX()
        track = gpxpy.gpx.GPXTrack()
        gpx.tracks.append(track)
        segment = gpxpy.gpx.GPXTrackSegment()
        track.segments.append(segment)

        for p in points_data:
            lat = float(p["lat"])
            lng = float(p["lng"])
            time = p.get("time")
            segment.points.append(
                gpxpy.gpx.GPXTrackPoint(
                    latitude=lat,
                    longitude=lng,
                    time=datetime.strptime(time, "%Y-%m-%dT%H:%M:%S") if time else None,
                )
            )

        gpx_output = gpx.to_xml()

        response = HttpResponse(gpx_output, content_type="application/gpx+xml")
        response["Content-Disposition"] = 'attachment; filename="updated_route.gpx"'
        return response

    return HttpResponse("Invalid request method.", status=405)


def calculate_bearing(point1, point2):
    """
    Calculate the bearing between two points.
    """
    lat1, lon1 = point1.latitude, point1.longitude
    lat2, lon2 = point2.latitude, point2.longitude

    # Convert latitude and longitude from degrees to radians
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])

    d_lon = lon2 - lon1
    x = math.sin(d_lon) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - (
        math.sin(lat1) * math.cos(lat2) * math.cos(d_lon)
    )

    bearing = math.atan2(x, y)

    # Convert bearing from radians to degrees
    bearing = math.degrees(bearing)
    bearing = (bearing + 360) % 360
    return bearing


def interpolate_geodesic(point1, point2, fraction):
    """
    Interpolate a point between two points along the geodesic path.
    """
    lat1, lon1 = point1.latitude, point1.longitude
    lat2, lon2 = point2.latitude, point2.longitude

    # Calculate the bearing and the distance
    bearing = calculate_bearing(point1, point2)
    total_distance = geodesic((lat1, lon1), (lat2, lon2)).meters
    intermediate_distance = fraction * total_distance

    # Find the intermediate point using the geodesic path and bearing
    origin = Point(lat1, lon1)
    destination = geodesic(meters=intermediate_distance).destination(origin, bearing)

    return destination.latitude, destination.longitude


def generate_intermediate_points(point1, point2, interval_seconds=1):
    """
    Generate intermediate points between two GPXTrackPoint objects along the geodesic path.
    """
    time_diff = (
        point2.time.replace(tzinfo=None) - point1.time.replace(tzinfo=None)
    ).total_seconds()
    if time_diff <= interval_seconds:
        return []

    steps = int(time_diff / interval_seconds)
    time_step = timedelta(seconds=interval_seconds)

    points = []
    for i in range(1, steps):
        fraction = i / steps
        new_lat, new_lon = interpolate_geodesic(point1, point2, fraction)
        new_time = point1.time + i * time_step
        new_point = gpxpy.gpx.GPXTrackPoint(new_lat, new_lon, time=new_time)
        points.append(new_point)

    return points


def fix_gpx(gpx_file, output_file, interval_seconds=1):
    """
    Process the GPX file and add intermediate points along the geodesic path.
    """
    with open(gpx_file, "r") as f:
        gpx = gpxpy.parse(f)

    for track in gpx.tracks:
        for segment in track.segments:
            new_points = []
            for i in range(len(segment.points) - 1):
                point1 = segment.points[i]
                point2 = segment.points[i + 1]
                new_points.append(point1)
                interpolated_points = generate_intermediate_points(
                    point1, point2, interval_seconds
                )
                new_points.extend(interpolated_points)
            new_points.append(segment.points[-1])
            segment.points = new_points

    with open(output_file, "w") as f:
        f.write(gpx.to_xml())


def fix_gpx_view(request, file_name):
    print("coming")
    os.makedirs("gpx", exist_ok=True)
    os.makedirs("output", exist_ok=True)
    gpx_file = os.path.join("gpx", file_name)
    output_file = os.path.join("output", f"fixed_{file_name}")
    print("Now Fixing")
    fix_gpx(gpx_file, output_file)
    with open(output_file, "rb") as f:
        response = HttpResponse(f.read(), content_type="application/gpx+xml")
        response["Content-Disposition"] = f"attachment; filename=fixed_{file_name}"
        return response


@csrf_exempt
def save_markers(request):
    print("has come to save_markers")
    if request.method == "POST":
        try:
            markers = json.loads(request.POST.get("markers", "[]"))
            print("when saving", markers)
            request.session["markers_to_delete"] = markers
            print("done saving in session")
            return JsonResponse({"status": "success"})
        except json.JSONDecodeError as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)
    return JsonResponse(
        {"status": "error", "message": "Invalid request method"}, status=400
    )


def show_markers(request):
    markers = request.session.get("markers_to_delete", [])
    if not markers:
        print("after saving", markers)
    return render(request, "ra_testing/show_markers.html", {"markers": markers})


@never_cache
def get_data(request):

    road_api = request.session.get("road_api")
    print("the road api is , ", road_api)
    clear_media()
    os.makedirs("media/chainage_media", exist_ok=True)
    print("i have made the directory")
    data = []
    mcw_file_saved = None
    other_file_saved = []
    start_distance = None
    end_distance = None

    if request.method == "POST":
        mcw_id = request.POST.get("mcw_id")
        other_ids = request.POST.get("other_ids")

        # Fetch
        mcw_metadata_url = f"https://{road_api}/api/roads/{mcw_id}/"
        print("the url to get metadata is ", mcw_metadata_url)
        mcw_gpx_url, start_distance, end_distance, road_type = get_gpx_download_url(
            mcw_metadata_url, road_api, fetch_distances=True
        )
        mcw_road_type = road_type
        print("mcw road type is ", road_type)

        if all(
            v is None for v in [mcw_gpx_url, start_distance, end_distance, road_type]
        ):
            return render(request, "ra_testing/chainagerepo.html", {"no_id": True})

        road_type = str(road_type)
        print("the mcw road type is ,", road_type)

        if not mcw_gpx_url:
            return render(
                request,
                "ra_testing/chainagerepo.html",
                {"error": "Failed to fetch GPX file for MCW ID."},
            )

        mcw_file_saved = save_gpx_file(
            mcw_gpx_url,
            "main_gpx.gpx",
            os.path.join(settings.MEDIA_ROOT, "chainage_media"),
        )

        # Process Other IDs GPX Files
        if other_ids:
            other_ids_list = [
                oid.strip() for oid in other_ids.split(",") if oid.strip()
            ]
            other_folder = os.path.join(
                os.path.join(settings.MEDIA_ROOT, "chainage_media"), "other_files"
            )
            os.makedirs(other_folder, exist_ok=True)

            for oid in other_ids_list:
                other_metadata_url = f"https://{road_api}/api/roads/{oid}/"
                print("the other metadata url is ", other_metadata_url)
                other_gpx_url, _, _, road_type = get_gpx_download_url(
                    other_metadata_url, road_api, fetch_distances=False
                )  # Skip chainage
                if all(
                    v is None
                    for v in [mcw_gpx_url, start_distance, end_distance, road_type]
                ):
                    return render(
                        request, "ra_testing/chainagerepo.html", {"no_id": True}
                    )
                road_type = str(road_type)
                if other_gpx_url:
                    file_name = f"{oid}.gpx"
                    save_status = save_gpx_file(other_gpx_url, file_name, other_folder)
                    if save_status:
                        other_file_saved.append(file_name)

        # Run the script if GPX files were saved successfully
        if mcw_file_saved and (not other_ids or other_file_saved):
            run_script(start_distance, end_distance, mcw_road_type)

            # Fetch processed data from output file

            output_excel_path = os.path.join(
                settings.MEDIA_ROOT, "chainage_media", "output.xlsx"
            )
            print("the output excel path is with us , ", output_excel_path)
            if os.path.exists(output_excel_path):
                try:
                    df = pd.read_excel(
                        output_excel_path,
                        usecols=[
                            "Name of GPX File",
                            "Start Distance (m)",
                            "End Distance (m)",
                        ],
                    )

                    # Remove ".gpx" from file names for API requests
                    df["Name of GPX File"] = df["Name of GPX File"].str.replace(
                        ".gpx", "", regex=False
                    )

                    # Fetch road_name using API for each GPX file
                    df["road_name"] = df["Name of GPX File"].apply(
                        lambda x: fetch_road_name(x, road_api)
                    )

                    # IF THE STRING CONTAINS IRR | IRL THEN THE END CHAINAGE IS ZERO
                    df.loc[
                        df["road_name"].str.contains("IRL|IRR", case=False, na=False),
                        "End Distance (m)",
                    ] = 0

                    # Rename columns for template compatibility
                    df.rename(
                        columns={
                            "Name of GPX File": "name_of_gpx_file",
                            "Start Distance (m)": "start_distance",
                            "End Distance (m)": "end_distance",
                        },
                        inplace=True,
                    )

                    # Convert DataFrame to list of dictionaries
                    data = df.to_dict(orient="records")
                    print("data for the chainage is : ", data)

                except Exception as e:
                    print(f"Error reading output Excel file: {e}")

    return render(
        request,
        "ra_testing/chainagerepo.html",
        {
            "data": data,
            "mcw_file_status": "Saved" if mcw_file_saved else "Failed",
            "other_file_status": (
                ", ".join(other_file_saved) if other_file_saved else "None"
            ),
            "start_distance": start_distance if mcw_file_saved else None,
            "end_distance": end_distance if mcw_file_saved else None,
        },
    )


def get_gpx_download_url(metadata_url, road_api, fetch_distances=True):
    """Fetch road metadata and extract GPX download URL. Optionally fetch chainage data."""
    try:
        response = requests.get(metadata_url, headers=HEADERS)
        data = response.json()
        if response.status_code != 200:
            return None, None, None, None
            # return render(request,"ra_testing/chainagerepo.html", {"error": error_message})

        # print("my data is ",data)

        print("gpx file is ", data.get("gpx_file"))

        gpx_path = data.get("gpx_file", "").strip()
        start_distance = data.get("start_chainage") if fetch_distances else None
        end_distance = data.get("end_chainage") if fetch_distances else None
        road_type = data.get("road_type") if fetch_distances else None

        if not gpx_path:
            return None, start_distance, end_distance, road_type  # No GPX file found

        gpx_url = f"https://{road_api}/{gpx_path.lstrip('/')}"
        return gpx_url, start_distance, end_distance, road_type

    except requests.exceptions.RequestException as e:
        print(f"Error fetching metadata from {metadata_url}: {e}")
        return None, None, None, None


def fetch_road_name(gpx_file_name, road_api):
    """Fetch road type using GPX file name via API call."""
    metadata_url = f"https://{road_api}/api/roads/{gpx_file_name}/"
    try:
        response = requests.get(metadata_url, headers=HEADERS)
        response.raise_for_status()
        data = response.json()
        return data.get("name", "Unknown")
    except requests.exceptions.RequestException as e:
        print(f"Error fetching road type for {gpx_file_name}: {e}")
        return "Unknown"


def fetch_road_type(gpx_file_name, road_api):
    """Fetch road type using GPX file name via API call."""
    metadata_url = f"https://{road_api}/api/roads/{gpx_file_name}/"
    try:
        response = requests.get(metadata_url, headers=HEADERS)
        response.raise_for_status()
        data = response.json()
        return data.get("name", "Unknown")
    except requests.exceptions.RequestException as e:
        print(f"Error fetching road type for {gpx_file_name}: {e}")
        return "Unknown"


def save_gpx_file(gpx_url, file_name, save_folder):

    if not gpx_url:
        return False

    try:
        os.makedirs(save_folder, exist_ok=True)

        response = requests.get(gpx_url, headers=HEADERS, stream=True)
        response.raise_for_status()
        gpx_file_path = os.path.join(save_folder, file_name)

        with open(gpx_file_path, "wb") as f:
            shutil.copyfileobj(response.raw, f)

        print(f"Saved: {gpx_file_path}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"Error downloading {gpx_url}: {e}")
        return False


def run_script(start_distance, end_distance, road_type):
    other_gpx_folder = os.path.join(
        os.path.join(settings.MEDIA_ROOT, "chainage_media"), "other_files"
    )
    main_gpx_path = os.path.join(
        os.path.join(settings.MEDIA_ROOT, "chainage_media"), "main_gpx.gpx"
    )
    output_path = os.path.join(
        os.path.join(settings.MEDIA_ROOT, "chainage_media"), "output.xlsx"
    )
    manual_start_distance = start_distance
    manual_end_distance = end_distance
    road_type = road_type
    print("other gpx folder path ", other_gpx_folder)
    print("main gpx file path ", main_gpx_path)

    print("manual start distance is ", manual_start_distance)
    print("manual end distance is ", manual_end_distance)

    process_gpx_files(
        other_gpx_folder,
        road_type,
        main_gpx_file=main_gpx_path,
        manual_start_distance=manual_start_distance,
        manual_end_distance=manual_end_distance,
        output_file=output_path,
    )


# def display_chainage(request):
#     data = []  # Default empty data
#     if request.method == "POST":
#         output_excel_path = os.path.join(settings.MEDIA_ROOT, "output.xlsx")
#         print("i am here to display the chainage")

#         # Read Excel file
#         df = pd.read_excel(output_excel_path, usecols=["Name of GPX File", "Start Distance (m)", "End Distance (m)"])

#         # Remove ".gpx" from file names
#         df["Name of GPX File"] = df["Name of GPX File"].str.replace(".gpx", "", regex=False)

#          # Rename columns to remove spaces (Jinja2 does not support spaces in attribute names)
#         df.rename(columns={
#         "Name of GPX File": "name_of_gpx_file",
#         "Start Distance (m)": "start_distance",
#         "End Distance (m)": "end_distance"
#     }, inplace=True)

#         print("columns are renamed ")


#         # Convert DataFrame to list of dictionaries
#         data = df.to_dict(orient="records")
#         print("data is in dictionary format")
#         print("data is " , data)

#     return render(request, 'ra_testing/index.html', {"data": data})


@csrf_exempt
def update_chainage(request):
    print(request.method)
    if request.method == "POST":
        road_api = request.session.get("road_api")
        print("i am here")
        try:
            data = json.loads(request.body)  # Extract JSON payload from request
            road_id = data.get("road_id")  # Name of GPX file (without .gpx extension)
            start_distance = data.get("start_distance")
            end_distance = data.get("end_distance")

            print("let us patch it ")
            print("road id is ", road_id)
            print("start distance is ", start_distance)
            print("end distance is ", end_distance)

            if not all([road_id, start_distance, end_distance]):
                return JsonResponse({"message": "Missing required data"}, status=400)

            API_URL = f"https://{road_api}/api/roads/{road_id}/"
            payload = {"start_chainage": start_distance, "end_chainage": end_distance}

            response = requests.patch(API_URL, headers=HEADERS, json=payload)

            if response.status_code == 200:
                return JsonResponse(
                    {"message": f"Updated road {road_id} successfully!"}
                )
            else:
                return JsonResponse(
                    {"message": f"Failed to update road {road_id}: {response.text}"},
                    status=response.status_code,
                )

        except json.JSONDecodeError:
            return JsonResponse({"message": "Invalid JSON format"}, status=400)

    return JsonResponse({"message": "Invalid request method"}, status=405)


def clear_media():
    media_folder = os.path.join(settings.MEDIA_ROOT, "chainage_media")
    print("Path to the media folder is:", media_folder)

    if os.path.exists(media_folder):
        try:
            # Delete the entire media folder and its contents
            shutil.rmtree(media_folder)
            print(
                f"Media folder '{media_folder}' and all its contents have been deleted."
            )
        except Exception as e:
            print(f"Error while deleting the media folder: {e}")
    else:
        print(f"The folder '{media_folder}' does not exist.")


def upload_gpx_edit(request):
    if request.method == "POST":
        delete_files_in_gpx_edit("gpx_edit")
        gpx_files = request.FILES.getlist("gpx_files")  # Get list of uploaded files
        saved_files = []

        for gpx_file in gpx_files:
            file_path = os.path.join(settings.MEDIA_ROOT, "gpx_edit", gpx_file.name)
            with open(file_path, "wb+") as destination:
                for chunk in gpx_file.chunks():
                    destination.write(chunk)
            saved_files.append(gpx_file.name)

        media_path = os.path.join(settings.MEDIA_ROOT, "gpx_edit")
        gpx_files = [file for file in os.listdir(media_path) if file.endswith(".gpx")]
        print("..........", gpx_files)

        return render(
            request,
            "ra_testing/plot_gpx.html",
            {"gpx_files": gpx_files, "file_name": None},
        )

    return render(request, "ra_testing/upload_gpx.html")


def plot_gpx_files(request):
    gpx_files = [
        file
        for file in os.listdir(settings.MEDIA_ROOT, (settings.MEDIA_ROOT, "gpx_edit"))
        if file.endswith(".gpx")
    ]  # Get all GPX files from the media folder

    print(gpx_files)
    return render(
        request, "ra_testing/plot_gpx.html", {"gpx_files": gpx_files, "file_name": None}
    )


# file_name = "gpx_files_asfsdfsdfd_YoNxvT1_processed.gpx"
def plot_gpx_edit(request, file_name):
    file_path = os.path.join(settings.MEDIA_ROOT, "gpx_edit", file_name)

    # Check if the file exists in MEDIA_ROOT
    if not os.path.exists(file_path):
        raise Http404("File not found")

    # Read and parse the GPX file
    with open(file_path, "r", encoding="utf-8") as f:
        gpx = gpxpy.parse(f)

    # Extract track points
    track_points = []
    for track in gpx.tracks:
        for segment in track.segments:
            for point in segment.points:
                track_points.append([point.latitude, point.longitude])

    # List all GPX files from MEDIA_ROOT
    media_path = os.path.join(settings.MEDIA_ROOT, "gpx_edit")
    gpx_files = [file for file in os.listdir(media_path) if file.endswith(".gpx")]

    return render(
        request,
        "ra_testing/plot_gpx.html",
        {
            "track_points": track_points,  # GPS coordinates for plotting
            "file_name": file_name,  # Current file name
            "file_id": file_name,  # Using file_name instead of DB ID
            "gpx_files": gpx_files,  # List of available GPX files
        },
    )


def calculate_average_gap(gpx):
    distances = []
    for track in gpx.tracks:
        for segment in track.segments:
            points = segment.points
            for i in range(1, len(points)):
                distances.append(
                    geodesic(
                        (points[i - 1].latitude, points[i - 1].longitude),
                        (points[i].latitude, points[i].longitude),
                    ).meters
                )

    return (
        sum(distances) / len(distances) if distances else 10
    )  # Default 10m if no data


def get_average_gap(request, file_name):
    file_path = os.path.join(settings.MEDIA_ROOT, "gpx_edit", file_name)

    # Check if the file exists
    if not os.path.exists(file_path):
        raise Http404("File not found")

    # Read and parse the GPX file
    with open(file_path, "r", encoding="utf-8") as f:
        gpx = gpxpy.parse(f)

    avg_gap = calculate_average_gap(gpx)  # Assuming this function is defined elsewhere

    return JsonResponse({"average_gap": avg_gap})


def generate_intermediate_points_with_time(start, end, speed):
    points = []
    distance = geodesic(start[:2], end[:2]).meters
    duration = distance / speed  # Total time in seconds

    time_gap = 1  # One second interval
    num_points = int(duration // time_gap)

    start_time = start[2]
    lat1, lon1 = start[:2]
    lat2, lon2 = end[:2]

    for i in range(1, num_points + 1):
        fraction = i / (num_points + 1)
        lat = lat1 + fraction * (lat2 - lat1)
        lon = lon1 + fraction * (lon2 - lon1)
        timestamp = start_time + timedelta(seconds=i)

        points.append((lat, lon, timestamp))

    return points


def update_gpx_edit(request, file_name):
    file_path = os.path.join(settings.MEDIA_ROOT, "gpx_edit", file_name)

    # Check if file exists
    if not os.path.exists(file_path):
        return HttpResponse("File not found", status=404)

    if request.method == "POST":
        # Parse the new structure that keeps start and end points separate
        new_points_data = json.loads(request.POST.get("new_points", "{}"))
        add_to_beginning = (
            request.POST.get("add_to_beginning", "false").lower() == "true"
        )

        start_points = new_points_data.get("startPoints", [])
        end_points = new_points_data.get("endPoints", [])

        if not start_points and not end_points:
            return HttpResponse("No new points were added.", status=400)

        # Read and parse GPX file
        with open(file_path, "r", encoding="utf-8") as f:
            gpx = gpxpy.parse(f)

        if not gpx.tracks or not gpx.tracks[0].segments:
            return HttpResponse("Invalid GPX file structure.", status=400)

        segment = gpx.tracks[0].segments[0]
        speed = calculate_average_speed(gpx)  # Ensure this function is implemented

        # Process start points
        if start_points:
            first_point = segment.points[0]
            for new in reversed(start_points):  # Add points in correct order
                lat, lon = new
                distance = geodesic(
                    (lat, lon), (first_point.latitude, first_point.longitude)
                ).meters
                new_time = first_point.time - timedelta(seconds=int(distance / speed))
                segment.points.insert(
                    0, gpxpy.gpx.GPXTrackPoint(lat, lon, time=new_time)
                )
                first_point = segment.points[0]

        # Process end points
        if end_points:
            last_point = segment.points[-1]
            for new in end_points:
                lat, lon = new
                distance = geodesic(
                    (last_point.latitude, last_point.longitude), (lat, lon)
                ).meters
                new_time = last_point.time + timedelta(seconds=int(distance / speed))
                segment.points.append(gpxpy.gpx.GPXTrackPoint(lat, lon, time=new_time))
                last_point = segment.points[-1]

        # Save updated GPX file
        updated_file_name = file_name.replace(".gpx", "_updated.gpx")
        updated_file_path = os.path.join(
            settings.MEDIA_ROOT, "gpx_edit", updated_file_name
        )
        with open(updated_file_path, "w", encoding="utf-8") as f:
            f.write(gpx.to_xml())

        # Set variable to indicate successful update
        update_successful = True

        return render(
            request,
            "ra_testing/plot_gpx.html",
            {
                "file_name": file_name,
                "message": "GPX file updated successfully with time tags!",
                "download_url": f"/media/gpx_edit/{updated_file_name}",
                "update_successful": update_successful,  # Added this variable
            },
        )

    return HttpResponse("Invalid request", status=400)


def calculate_bearing(point1, point2):
    """
    Calculate the bearing between two points.
    """
    lat1, lon1 = point1.latitude, point1.longitude
    lat2, lon2 = point2.latitude, point2.longitude

    # Convert latitude and longitude from degrees to radians
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])

    d_lon = lon2 - lon1
    x = math.sin(d_lon) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - (
        math.sin(lat1) * math.cos(lat2) * math.cos(d_lon)
    )

    bearing = math.atan2(x, y)

    # Convert bearing from radians to degrees
    bearing = math.degrees(bearing)
    bearing = (bearing + 360) % 360
    return bearing


def interpolate_geodesic(point1, point2, fraction):
    """
    Interpolate a point between two points along the geodesic path.
    """
    lat1, lon1 = point1.latitude, point1.longitude
    lat2, lon2 = point2.latitude, point2.longitude

    # Calculate the bearing and the distance
    bearing = calculate_bearing(point1, point2)
    total_distance = geodesic((lat1, lon1), (lat2, lon2)).meters
    intermediate_distance = fraction * total_distance

    # Find the intermediate point using the geodesic path and bearing
    origin = Point(lat1, lon1)
    destination = geodesic(meters=intermediate_distance).destination(origin, bearing)

    return destination.latitude, destination.longitude


def remove_milliseconds(dt):
    """
    Remove milliseconds from a datetime object.
    """
    if dt is None:
        return None
    return dt.replace(microsecond=0)


def generate_intermediate_points(point1, point2, interval_seconds=1):
    """
    Generate intermediate points between two GPXTrackPoint objects along the geodesic path.
    """
    # Make sure both points have time data
    if point1.time is None or point2.time is None:
        return []

    time_diff = (
        point2.time.replace(tzinfo=None) - point1.time.replace(tzinfo=None)
    ).total_seconds()
    if time_diff <= interval_seconds:
        return []

    steps = int(time_diff / interval_seconds)
    time_step = timedelta(seconds=interval_seconds)

    points = []
    for i in range(1, steps):
        fraction = i / steps
        new_lat, new_lon = interpolate_geodesic(point1, point2, fraction)
        new_time = remove_milliseconds(point1.time + i * time_step)
        new_point = gpxpy.gpx.GPXTrackPoint(new_lat, new_lon, time=new_time)
        points.append(new_point)

    return points


def process_gpx_for_download(gpx_path, interval_seconds=1):
    """
    Process the GPX file and add intermediate points along the geodesic path.
    """
    with open(gpx_path, "r") as f:
        gpx = gpxpy.parse(f)

    for track in gpx.tracks:
        for segment in track.segments:
            new_points = []
            for i in range(len(segment.points) - 1):
                point1 = segment.points[i]
                point2 = segment.points[i + 1]

                # Remove milliseconds from original points
                if point1.time:
                    point1.time = remove_milliseconds(point1.time)
                if point2.time:
                    point2.time = remove_milliseconds(point2.time)

                new_points.append(point1)
                interpolated_points = generate_intermediate_points(
                    point1, point2, interval_seconds
                )
                new_points.extend(interpolated_points)
            new_points.append(segment.points[-1])
            segment.points = new_points

    # Save processed file
    processed_path = gpx_path.replace("_updated.gpx", "_processed.gpx")
    with open(processed_path, "w") as f:
        f.write(gpx.to_xml())

    return processed_path


def download_gpx_edit(request, file_name):
    updated_gpx_path = os.path.join(
        settings.MEDIA_ROOT, "gpx_edit", file_name.replace(".gpx", "_updated.gpx")
    )
    print("updated.........", updated_gpx_path)

    # Ensure the file exists
    if not os.path.exists(updated_gpx_path):
        raise Http404("File not found.")

    # Process the GPX file before downloading (if needed)
    processed_gpx_path = process_gpx_for_download(updated_gpx_path)

    print("the processed gpx path is ", processed_gpx_path)

    # Return the processed GPX file as a download
    with open(processed_gpx_path, "r", encoding="utf-8") as f:
        response = HttpResponse(f.read(), content_type="application/gpx+xml")
        # response["Content-Disposition"] = f'attachment; filename="{file_name.replace(".gpx", "_processed.gpx")}"'
        return response


def calculate_average_speed(gpx):
    speeds = []
    for track in gpx.tracks:
        for segment in track.segments:
            points = segment.points
            for i in range(1, len(points)):
                distance = geodesic(
                    (points[i - 1].latitude, points[i - 1].longitude),
                    (points[i].latitude, points[i].longitude),
                ).meters
                time_diff = (points[i].time - points[i - 1].time).total_seconds()
                if time_diff > 0:
                    speed = distance / time_diff  # meters per second
                    speeds.append(speed)

    return sum(speeds) / len(speeds) if speeds else 5  # Default 5 m/s if no data


last_added_point = None  # Track the last manually added or generated point


def generate_point_by_time(request, file_name):
    """
    Generates a new point at a distance based on speed * time from the last point.
    Allows the new point to be moved along a radial path.
    """
    global last_added_point

    gpx_path = os.path.join(settings.MEDIA_ROOT, "gpx_edit", file_name)

    # Ensure the GPX file exists
    if not os.path.exists(gpx_path):
        return JsonResponse({"error": "GPX file not found"}, status=404)

    # Open and parse the GPX file
    with open(gpx_path, "r", encoding="utf-8") as f:
        gpx = gpxpy.parse(f)

    if not gpx.tracks or not gpx.tracks[0].segments:
        return JsonResponse({"error": "Invalid GPX file"}, status=400)

    segment = gpx.tracks[0].segments[0]

    # Determine the last point (either from GPX or last added point)
    base_point = last_added_point if last_added_point else segment.points[-1]

    speed = calculate_average_speed(gpx)  # Speed in meters/second

    try:
        time_input = int(request.GET.get("time", 10))  # Default 10s if not provided
    except ValueError:
        return JsonResponse({"error": "Invalid time value"}, status=400)

    distance = speed * time_input  # Distance = speed × time

    # Generate new point at fixed distance in a default direction (0°)
    new_location = geodesic(meters=distance).destination(
        (base_point.latitude, base_point.longitude), 0  # Default north
    )

    new_lat, new_lon = new_location.latitude, new_location.longitude

    # Store new point with time
    new_time = base_point.time + timedelta(seconds=time_input)
    last_added_point = gpxpy.gpx.GPXTrackPoint(
        new_lat, new_lon, elevation=0, time=new_time
    )

    return JsonResponse(
        {
            "lat": new_lat,
            "lon": new_lon,
            "time": new_time.isoformat(),
            "distance": distance,
            "base_lat": base_point.latitude,
            "base_lon": base_point.longitude,
        }
    )


def delete_files_in_gpx_edit(folder_name):
    media_folder = os.path.join("media", folder_name)

    if os.path.exists(media_folder) and os.path.isdir(media_folder):
        for file in os.listdir(media_folder):
            file_path = os.path.join(media_folder, file)
            try:
                if os.path.isfile(file_path):
                    os.remove(file_path)  # Delete file
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)  # Delete subdirectory
            except Exception as e:
                print(f"Error deleting {file_path}: {e}")
        print(f"All files in {media_folder} deleted successfully.")
    else:
        print(f"Folder '{media_folder}' does not exist.")


# Create your views here.
HEADERS = {
    "Security-Password": "admin@123",
}


@csrf_protect
def fetch_data(request):
    context = {}
    road_api = request.session.get("road_api", None)
    api_base_url = (
        f"https://{road_api}/api/roads/"  # Replace with your actual API base URL
    )

    if request.method == "POST":
        road_id = request.POST.get("object_id")
        action = request.POST.get("action")

        if action == "fetch":
            try:
                road_url = f"{api_base_url}{road_id}"
                print("the api url is ..... ", road_url)
                response = requests.get(road_url, headers=HEADERS)
                if response.status_code == 200:
                    data = response.json()
                    context["road_data"] = data
                    messages.success(request, "Road data fetched successfully!")
                else:
                    messages.error(
                        request,
                        f"Road not found or error occurred. Status code: {response.status_code}",
                    )
            except requests.RequestException as e:
                messages.error(request, f"Error fetching data: {str(e)}")

        elif action == "update":
            # Only include fields that are actually submitted and not empty
            update_data = {}
            fields = [
                "name",
                "code",
                "length",
                "start_chainage",
                "end_chainage",
                "start_LatLng",
                "end_LatLng",
                "road_type",
            ]

            # Add non-empty fields to update data
            for field in fields:
                value = request.POST.get(field)
                print(
                    "the values i have got are for ", field, " and the value is ", value
                )
                if value is not None and value.strip() != "":

                    if field == "length":
                        update_data[field] = float(value)
                    else:
                        update_data[field] = value

            if "LHR_side" in request.POST:
                update_data["LHR_side"] = True
            elif request.POST.get("action") == "update":
                update_data["LHR_side"] = False

            if "RHR_side" in request.POST:
                update_data["RHR_side"] = True
            elif request.POST.get("action") == "update":
                update_data["RHR_side"] = False

            files = None
            if "gpx_file" in request.FILES:
                files = {"gpx_file": request.FILES["gpx_file"]}

            print("update data is ", update_data)
            print("the files are ", files)
            try:
                response = requests.patch(
                    f"{api_base_url}{road_id}/",
                    data=update_data,
                    files=files,
                    headers=HEADERS,
                )
                if response.status_code in [200, 201, 204]:
                    messages.success(request, "Road data updated successfully!")

                    updated_response = requests.get(
                        f"{api_base_url}{road_id}/", headers=HEADERS
                    )
                    if updated_response.status_code == 200:
                        data = updated_response.json()
                        context["road_data"] = data
                else:
                    messages.error(
                        request,
                        f"Error updating data. Status code: {response.status_code}",
                    )
            except requests.RequestException as e:
                messages.error(request, f"Error updating data: {str(e)}")

    return render(request, "ra_testing/fetch_form.html", context)


@never_cache
def ViewRoads(request):
    headers = {"security-Password": "admin@123"}

    def safe_fetch_json(url):
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()  # raises HTTPError for bad responses
            return response.json()
        except (requests.RequestException, ValueError) as e:
            print(f"Error fetching from {url}: {e}")
            return []

    ho_list = safe_fetch_json("https://ndd.roadathena.com/api/head-offices/")
    ro_list = safe_fetch_json("https://ndd.roadathena.com/api/market-committees/")
    div_list = safe_fetch_json("https://ndd.roadathena.com/api/sub-divisions/")

    roads_data = []

    if request.method == "GET":
        ho_id = request.GET.get("ho")
        ro_id = request.GET.get("ro")
        division_id = request.GET.get("division")

        if ho_id and ro_id and division_id:
            roads_url = f"https://ndd.roadathena.com/api/roads/?ho={ho_id}&ro={ro_id}&division={division_id}"
            roads_data = safe_fetch_json(roads_url)

    context = {
        "head_offices": ho_list,
        "regions": ro_list,
        "divisions": div_list,
        "roads_data": roads_data,
    }
    return render(request, "ra_testing/GetRoadsId.html", context)


@csrf_exempt
def ViewRoadsByDate(request):
    headers = {"security-Password": "admin@123"}
    road_api = request.GET.get("road_api")  # get selected environment

    ho_list, ro_list, div_list, roads_data = [], [], [], []
    ho_id = request.GET.get("ho")
    ro_id = request.GET.get("ro")
    division_id = request.GET.get("division")
    created_date = request.GET.get("created_date")

    def safe_fetch_json(url):
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error fetching from {url}: {e}")
            return []

    # ✅ Only fetch HO/RO/Division lists if an environment is selected
    if road_api:
        ho_list = safe_fetch_json(f"https://{road_api}/api/head-offices/")
        ro_list = safe_fetch_json(f"https://{road_api}/api/market-committees/")
        div_list = safe_fetch_json(f"https://{road_api}/api/sub-divisions/")

        # ✅ Fetch roads only when all 3 filters are chosen
        if ho_id and ro_id and division_id:
            roads_url = f"https://{road_api}/api/roads/?ho={ho_id}&ro={ro_id}&division={division_id}"
            all_roads = safe_fetch_json(roads_url)

            if created_date:
                try:
                    filter_date = datetime.strptime(created_date, "%Y-%m-%d").date()
                    roads_data = [
                        road
                        for road in all_roads
                        if road.get("created_at")
                        and datetime.fromisoformat(road["created_at"][:-1]).date()
                        == filter_date
                    ]
                except Exception as e:
                    print(f"Date filtering error: {e}")
                    roads_data = all_roads
            else:
                roads_data = all_roads

    context = {
        "head_offices": ho_list,
        "regions": ro_list,
        "divisions": div_list,
        "roads_data": roads_data,
        "selected_ho": ho_id,
        "selected_ro": ro_id,
        "selected_division": division_id,
        "selected_date": created_date,
        "selected_api": road_api,
    }

    return render(request, "ra_testing/Roadsbydate.html", context)


@csrf_exempt
def export_selected_roads(request):
    if request.method == "POST":
        road_ids = request.POST.get("road_ids", "")
        if not road_ids:
            return HttpResponse("No road IDs provided.", status=400)

        road_ids = [r.strip() for r in road_ids.split(",") if r.strip()]
        road_api = request.POST.get("road_api")
        headers = {"security-Password": "admin@123"}

        def safe_fetch_json(url):
            try:
                resp = requests.get(url, headers=headers, timeout=10)
                resp.raise_for_status()
                return resp.json()
            except Exception as e:
                print(f"Error fetching {url}: {e}")
                return []

        # ✅ Fetch HO, RO, and Division lists once for name mapping
        ho_list = safe_fetch_json(f"https://{road_api}/api/head-offices/")
        ro_list = safe_fetch_json(f"https://{road_api}/api/market-committees/")
        div_list = safe_fetch_json(f"https://{road_api}/api/sub-divisions/")

        # ✅ Build ID → Name maps
        ho_map = {str(h["id"]): h.get("name", "") for h in ho_list}
        ro_map = {str(r["id"]): r.get("name", "") for r in ro_list}
        div_map = {str(d["id"]): d.get("sub_division", "") for d in div_list}

        # Excel setup
        wb = Workbook()
        ws = wb.active
        ws.title = "Selected Roads"

        ws.append(
            [
                "ID",
                "Name",
                "Code",
                "Road Type",
                "Pavement Type",
                "Length",
                "Width",
                "Head Office",
                "Region Office",
                "Division",
                "Created At",
                "Updated At",
            ]
        )

        # ✅ Fetch each road’s full details
        for rid in road_ids:
            url = f"https://{road_api}/api/roads/{rid}/"
            try:
                resp = requests.get(url, headers=headers, timeout=10)
                resp.raise_for_status()
                road = resp.json()

                ho_name = ho_map.get(str(road.get("ho")), "")
                ro_name = ro_map.get(str(road.get("ro")), "")
                div_name = div_map.get(str(road.get("division")), "")

                ws.append(
                    [
                        road.get("id"),
                        road.get("name"),
                        road.get("code"),
                        road.get("road_type"),
                        road.get("pavement_type"),
                        road.get("length"),
                        road.get("width"),
                        ho_name,
                        ro_name,
                        div_name,
                        road.get("created_at", "")[:10],
                        road.get("updated_at", "")[:10],
                    ]
                )
            except Exception as e:
                print(f"Error fetching road {rid}: {e}")
                ws.append(
                    [rid, "Error fetching data", "", "", "", "", "", "", "", "", ""]
                )

        # ✅ Return Excel
        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = 'attachment; filename="selected_roads.xlsx"'
        wb.save(response)
        return response

    return HttpResponse("Invalid request method.", status=405)


# import os
# import json
# import base64
# from django.conf import settings
# from django.shortcuts import render, redirect
# from django.http import JsonResponse
# from django.views.decorators.csrf import csrf_exempt
# import shutil


# # Allowed image extensions (only these will be saved / shown)
# ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

# # Directory where uploaded images will be stored
# UPLOAD_DIR = os.path.join(settings.MEDIA_ROOT, "Annotations","uploads")
# os.makedirs(UPLOAD_DIR, exist_ok=True)  # Ensure upload folder exists


# IGNORED_FILES = ["desktop.ini", ".ds_store", "thumbs.db"]

# def upload_folder(request):
#     if request.method == "POST":
#         uploaded_files = request.FILES.getlist("folder")
#         saved_any = False

#         if uploaded_files:
#             # define filters
#             ALLOWED_EXTENSIONS = [".jpg", ".jpeg", ".png"]
#             IGNORED_FILES = ["desktop.ini", "thumbs.db"]

#             # filter valid images only
#             valid_files = [
#                 f for f in uploaded_files
#                 if os.path.splitext(f.name)[1].lower() in ALLOWED_EXTENSIONS
#                 and f.name.lower() not in IGNORED_FILES
#             ]

#             # clean old uploads
#             if os.path.exists(UPLOAD_DIR):
#                 shutil.rmtree(UPLOAD_DIR)
#             os.makedirs(UPLOAD_DIR, exist_ok=True)

#             for image in valid_files:
#                 image_path = os.path.join(UPLOAD_DIR, image.name)
#                 with open(image_path, "wb+") as f:
#                     for chunk in image.chunks():
#                         f.write(chunk)
#                 saved_any = True

#             if saved_any:
#                 return redirect("labeling_tool")

#     return render(request, "drawapp/upload.html")


# def labeling_tool(request):
#     """
#     Page 2: Show labeling canvas with uploaded images
#     We'll pass:
#       - images: a JSON-serializable Python list of filenames (NOT full URLs)
#       - base_url: the base URL where those files are served (MEDIA_URL + 'uploads/')
#     """
#     try:
#         all_files = os.listdir(UPLOAD_DIR)
#     except FileNotFoundError:
#         all_files = []

#     # Filter only allowed extensions and sort (optional)
#     image_files = [f for f in all_files if os.path.splitext(f)[1].lower() in ALLOWED_EXTENSIONS and f.lower() not in IGNORED_FILES]
#     image_files.sort()

#     # Pass filenames (as JSON) and base url separately
#     return render(request, "drawapp/labeling_tool.html", {
#         "images": json.dumps(image_files),                 # e.g. ["img1.jpg","img2.png"]
#         "base_url": f"{settings.MEDIA_URL}Annotations/uploads/"        # e.g. "/media/uploads/"
#     })

# @csrf_exempt
# def save_annotations(request):

#     road_api = request.session.get('road_api', None)  # environment

#     if request.method == "POST":
#         try:
#             data = json.loads(request.body.decode("utf-8"))
#             image_name = data.get("image_name")
#             annotations = data.get("annotations", {})
#             image_data = data.get("imageData")
#             category = data.get("category")
#             subCategory = data.get("subCategory")

#             if not image_name or not category or not subCategory:
#                 return JsonResponse({"error": "Missing required fields"}, status=400)

#             src_image_path = os.path.join(UPLOAD_DIR, image_name)
#             if not os.path.exists(src_image_path):
#                 return JsonResponse({"error": "Raw image not found"}, status=404)

#             if not image_data:
#                 return JsonResponse({"error": "No image data received"}, status=400)

#             # --- Create folder paths ---
#             annotated_dir = os.path.join(settings.MEDIA_ROOT, "Annotations", "annotated", str(road_api), str(category), str(subCategory))
#             json_dir = os.path.join(settings.MEDIA_ROOT, "Annotations", "json", str(road_api), str(category), str(subCategory))
#             os.makedirs(annotated_dir, exist_ok=True)
#             os.makedirs(json_dir, exist_ok=True)

#             # --- Copy raw image to JSON folder ---
#             raw_dest_path = os.path.join(json_dir, image_name)
#             shutil.copy2(src_image_path, raw_dest_path)

#             # --- Save annotated image ---
#             annotated_path_canvas = os.path.join(annotated_dir, f"{os.path.splitext(image_name)[0]}_canvas.png")
#             image_bytes = image_data.split(",")[1]
#             with open(annotated_path_canvas, "wb") as f:
#                 f.write(base64.b64decode(image_bytes))

#             # --- Save JSON ---
#             json_path = os.path.join(json_dir, f"{os.path.splitext(image_name)[0]}_annotated.json")
#             with open(json_path, "w") as f:
#                 json.dump({"image": image_name, "annotations": annotations}, f, indent=4)

#             # --- Return URLs for front-end ---
#             return JsonResponse({
#                 "message": "Annotations saved successfully.",
#                 "raw_image": f"{settings.MEDIA_URL}Annotations/json/{road_api}/{category}/{subCategory}/{image_name}",
#                 "json_file": f"{settings.MEDIA_URL}Annotations/json/{road_api}/{category}/{subCategory}/{os.path.basename(json_path)}",
#                 "annotated_image_canvas": f"{settings.MEDIA_URL}Annotations/annotated/{road_api}/{category}/{subCategory}/{os.path.basename(annotated_path_canvas)}"
#             })

#         except Exception as e:
#             return JsonResponse({"error": str(e)}, status=500)

#     return JsonResponse({"error": "Invalid request method."}, status=400)
