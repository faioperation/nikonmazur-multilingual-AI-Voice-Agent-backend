from django.urls import path
from .views import CarAvailableAPIView

urlpatterns = [
    path("car_available/", CarAvailableAPIView.as_view()),
]
