import logging

from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.filters import SearchFilter

from .models import CallRecording
from .parsers import parse_end_of_call_report
from .serializers import CallRecordingSerializer

logger = logging.getLogger(__name__)

# VAPI sends many event types; we only persist completed calls.
SAVED_EVENT_TYPES = {"end-of-call-report"}


def _extract_event_type(payload):
    """VAPI wraps the event under payload["message"]["type"]."""
    if not isinstance(payload, dict):
        return "unknown"
    return payload.get("message", {}).get("type") or payload.get("type") or "unknown"


class VapiWebhookView(APIView):
    """Receive VAPI webhook events and persist end-of-call reports."""

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        payload = request.data
        event_type = _extract_event_type(payload)

        if event_type not in SAVED_EVENT_TYPES:
            return Response(
                {"success": True, "event_type": event_type, "stored": False},
                status=status.HTTP_200_OK,
            )

        fields = parse_end_of_call_report(payload)
        recording = CallRecording.objects.create(**fields)
        logger.info("Stored CallRecording %s from VAPI webhook", recording.pk)

        return Response(
            {"success": True, "event_type": event_type, "stored": True, "id": recording.pk},
            status=status.HTTP_201_CREATED,
        )


class CallRecordingListView(generics.ListAPIView):
    """List all call recordings (newest first), searchable by caller."""

    queryset = CallRecording.objects.all().order_by("-created_at")
    serializer_class = CallRecordingSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [SearchFilter]
    search_fields = ["caller_name", "caller_number"]


class CallRecordingDetailView(generics.RetrieveAPIView):
    """Retrieve a single call recording; returns 404 if not found."""

    queryset = CallRecording.objects.all()
    serializer_class = CallRecordingSerializer
    permission_classes = [IsAuthenticated]
