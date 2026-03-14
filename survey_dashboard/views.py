from django.http import JsonResponse
from django.shortcuts import render
from .models import Trip, Survey, SurveyTrip  # Import your models

def dashboard(request):
    trips_data = SurveyTrip.objects.all().order_by('id')
    surveys_data = Survey.objects.all()
    assign_data = Trip.objects.all()

    context = {
        'trips': trips_data,
        'surveys': surveys_data,
        'assign': assign_data
    }

    return render(request, 'survey_dashboard/dashboard.html', context)

def submit_trip(request):
    if request.method == "POST":
        try:
            SurveyTrip.objects.create(
                trip_id=request.POST.get("trip_id"),
                surveyor_name=request.POST.get("surveyor_name"),
                driver_name=request.POST.get("driver_name"),
                location=request.POST.get("location"),
                date=request.POST.get("date"),
                vehicle_number=request.POST.get("vehicle_number"),
            )
            return JsonResponse({"success": True, "message": "Trip added successfully!"})
        except Exception as e:
            return JsonResponse({"success": False, "message": f"Failed to add trip: {str(e)}"})

    return JsonResponse({"success": False, "message": "Invalid request."})

def before_survey(request):
    trips_data =  Trip.objects.all() 
    context = {'trips': trips_data}
    return render(request, 'survey_dashboard/before_survey.html', context)

def during_survey(request):
    surveys_data = Survey.objects.all()
    context = {'surveys': surveys_data}
    return render(request, 'survey_dashboard/during_survey.html', context)

def assign_trip(request):
    assign_data = Trip.objects.all()
    context = {'assign': assign_data}
    return render(request, 'survey_dashboard/assign_trip.html', context)

def trip_list(request):
    assign_data = SurveyTrip.objects.all().order_by('id')
    context = {'assign': assign_data}
    return render(request, 'survey_dashboard/trip_list.html', context)



from rest_framework import viewsets, status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.shortcuts import render
from .models import Trip, TripBill, SurveyTrip, Survey
from .serializers import TripSerializer, SurveyTripSerializer, SurveySerializer
import logging

logger = logging.getLogger(__name__)


def form(request):
    return render(request, 'bill.html')


# ---------------- Trip ViewSet ----------------
class TripViewSet(viewsets.ModelViewSet):
    queryset = Trip.objects.all()
    serializer_class = TripSerializer
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        logger.debug(f"Create request data: {request.data}")
        logger.debug(f"Create request FILES: {request.FILES}")
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        trip = serializer.save()

        bill_images = request.FILES.getlist('bill_images')
        logger.debug(f"Bill images during creation: {bill_images}")
        
        for image in bill_images:
            try:
                bill = TripBill.objects.create(trip=trip, image=image)
                logger.debug(f"Created bill with image: {bill.image}")
            except Exception as e:
                logger.error(f"Error saving bill image: {e}")

        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def partial_update(self, request, *args, **kwargs):
        logger.debug(f"Partial update data: {request.data}")
        logger.debug(f"Partial update FILES: {request.FILES}")

        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        bill_images = request.FILES.getlist('bill_images')
        logger.debug(f"New bill images: {bill_images}")
        
        for image in bill_images:
            try:
                bill = TripBill.objects.create(trip=instance, image=image)
                logger.debug(f"Added bill image: {bill.image}")
            except Exception as e:
                logger.error(f"Error adding bill image: {e}")

        return Response(serializer.data, status=status.HTTP_200_OK)


# ---------------- SurveyTrip ViewSet ----------------
class SurveyTripViewSet(viewsets.ModelViewSet):
    queryset = SurveyTrip.objects.all()
    serializer_class = SurveyTripSerializer
    permission_classes = [AllowAny]


# ---------------- Survey ViewSet ----------------
class SurveyViewSet(viewsets.ModelViewSet):
    queryset = Survey.objects.all()
    serializer_class = SurveySerializer
    permission_classes = [AllowAny]
