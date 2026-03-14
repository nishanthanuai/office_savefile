from django.contrib import admin
from .models import Survey, SurveyTrip, Trip, TripBill

@admin.register(Survey)
class SurveyAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'date', 'start_time', 'end_time',
        'survey_location', 'camera_position',
        'start_odometer', 'end_odometer',
        'vehicle_number', 'reason_for_not_starting'
    )
    search_fields = ('survey_location', 'vehicle_number')
    list_filter = ('date',)
    # Add fields you want to be able to edit directly in the form
    fields = ('date', 'start_time', 'end_time', 'survey_location', 'camera_position', 
              'start_odometer', 'end_odometer', 'vehicle_number', 'reason_for_not_starting')

@admin.register(SurveyTrip)
class SurveyTripAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'trip_id', 'surveyor_name', 'driver_name',
        'location', 'date', 'vehicle_number'
    )
    search_fields = ('surveyor_name', 'driver_name', 'trip_id')
    list_filter = ('date',)
    fields = ('trip_id', 'surveyor_name', 'driver_name', 'location', 'date', 'vehicle_number')

@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'surveyor_name', 'driver_name',
        'vehicle_number', 'start_date', 'end_date',
        'start_odometer_reading', 'end_odometer_reading'
    )
    search_fields = ('surveyor_name', 'driver_name', 'vehicle_number')
    list_filter = ('start_date', 'end_date')
    # Make sure that all relevant fields are displayed in the form
    fields = (
        'surveyor_name', 'driver_name', 'vehicle_number', 'start_date', 'start_location',
        'start_odometer_reading', 'end_odometer_reading', 'end_location', 'end_date'
    )

@admin.register(TripBill)
class TripBillAdmin(admin.ModelAdmin):
    list_display = ('id', 'trip', 'image')
    search_fields = ('trip__vehicle_number',)
    # Fields visible for entry in the admin form
    fields = ('trip', 'image')

