from rest_framework import serializers
from .models import Survey, SurveyTrip, Trip, TripBill
from cloudinary.utils import cloudinary_url
import logging

logger = logging.getLogger(__name__)


class SurveyTripSerializer(serializers.ModelSerializer):
    class Meta:
        model = SurveyTrip
        fields = [
            'id', 'trip_id', 'surveyor_name', 'driver_name', 
            'location', 'date', 'vehicle_number', 
            'created_at', 'updated_at'
        ]


class TripBillSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = TripBill
        fields = ['id', 'image']

    def get_image(self, obj):
        try:
            if obj.image:
                public_id = getattr(obj.image, "public_id", None)
                if public_id:
                    url, _ = cloudinary_url(public_id, secure=True)
                    return url
                return obj.image.url  # fallback if `cloudinary_url` fails
        except Exception as e:
            logger.error(f"Error fetching image URL: {e}")
        return None


class TripSerializer(serializers.ModelSerializer):
    bills = TripBillSerializer(many=True, read_only=True)
    bill_images = serializers.ListField(
        child=serializers.FileField(),
        write_only=True,
        required=False
    )

    class Meta:
        model = Trip
        fields = [
            'id', 'surveyor_name', 'driver_name', 'start_odometer_reading', 
            'vehicle_number', 'start_date', 'start_location',
            'end_odometer_reading', 'end_location', 'end_date',
            'bills', 'bill_images'
        ]


class SurveySerializer(serializers.ModelSerializer):
    class Meta:
        model = Survey
        fields = [
            'id', 'date', 'start_time', 'survey_location', 'start_odometer',
            'camera_position', 'reason_for_not_starting', 'vehicle_number',
            'end_time', 'end_odometer'
        ]
