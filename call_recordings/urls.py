from django.urls import path
from .views import VapiWebhookView, CallRecordingListView, CallRecordingDetailView

urlpatterns = [
    path(
        "call-recordings/", CallRecordingListView.as_view(), name="call-recording-list"
    ),
    path(
        "call-recordings/<int:pk>/",
        CallRecordingDetailView.as_view(),
        name="call-recording-detail",
    ),
    path("webhook/call-logs/", VapiWebhookView.as_view(), name="vapi-webhook"),
]
