from django.urls import path, include

urlpatterns = [
    path("", include("call_recordings.urls")),
    path("", include("stats.urls")),
    path("", include("cars_availablity_check.urls")),
]
