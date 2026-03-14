from django.db import models
from cloudinary.models import CloudinaryField

class SurveyTrip(models.Model):
    trip_id = models.CharField(max_length=50, unique=True)
    surveyor_name = models.CharField(max_length=100)
    driver_name = models.CharField(max_length=100)
    location = models.CharField(max_length=200)
    date = models.DateField()
    vehicle_number = models.CharField(max_length=50)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Trip {self.trip_id} - {self.date}"

    class Meta:
        ordering = ['-date']


class Trip(models.Model):
    surveyor_name = models.CharField(max_length=100)
    driver_name = models.CharField(max_length=100)
    start_odometer_reading = models.PositiveIntegerField()
    vehicle_number = models.CharField(max_length=50)
    start_date = models.DateField()
    start_location = models.CharField(max_length=255)

    end_odometer_reading = models.PositiveIntegerField(null=True, blank=True)
    end_location = models.CharField(max_length=255, null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.driver_name} - {self.vehicle_number} - {self.start_date}"


class TripBill(models.Model):
    trip = models.ForeignKey(Trip, related_name='bills', on_delete=models.CASCADE)
    image = CloudinaryField('image')

    def __str__(self):
        return f"Bill for {self.trip}"


class Survey(models.Model):
    date = models.DateField()
    start_time = models.TimeField()
    survey_location = models.CharField(max_length=255)
    start_odometer = models.PositiveIntegerField()
    camera_position = models.CharField(
        max_length=10,
        choices=[('front', 'Front'), ('back', 'Back')]
    )
    reason_for_not_starting = models.TextField(blank=True, null=True)
    vehicle_number = models.CharField(max_length=50)

    end_time = models.TimeField(null=True, blank=True)
    end_odometer = models.PositiveIntegerField(null=True, blank=True)

    def __str__(self):
        return f"Survey for {self.vehicle_number} on {self.date}"
