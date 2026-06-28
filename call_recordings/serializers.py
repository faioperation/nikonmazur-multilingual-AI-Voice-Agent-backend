from rest_framework import serializers
from .models import CallRecording


class CallRecordingSerializer(serializers.ModelSerializer):
    class Meta:
        model = CallRecording
        fields = [
            "id",
            "caller_name",
            "caller_number",
            "assistant_name",
            "audio_url",
            "call_date",
            "duration_seconds",
            "outcome",
            "sentiment",
            "ai_summary",
            "transcript",
            "lead_score",
            "created_at",
        ]
