from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import *

app_name = 'survey_dashboard'
# Router for API endpoints
router = DefaultRouter()
router.register(r'trips', TripViewSet, basename='trip')
router.register(r'surveytrips', SurveyTripViewSet, basename='surveytrip')
router.register(r'surveys', SurveyViewSet, basename='survey')

urlpatterns = [
    # API routes
    path('api/', include(router.urls)),
    path('', dashboard, name='dashboard'),
    path('submit-trip/', submit_trip, name="submit_trip"),
    path('before-survey/', before_survey, name="before_survey"),
    path('during-survey/', during_survey, name="during_survey"),
    path('assign-trip/', assign_trip, name="assign_trip"),
    path('trip-list/', trip_list, name="trip_list"),
]
