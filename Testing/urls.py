from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('ra_testing.urls')),
    path('survey_dashboard/',include(('survey_dashboard.urls', 'survey_dashboard'), namespace='survey_dashboard')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
