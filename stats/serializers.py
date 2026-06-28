from rest_framework import serializers

from call_recordings.models import CallRecording


class RecentCallSerializer(serializers.ModelSerializer):
    """Trimmed CallRecording view for the overview's "Recent Calls" list."""

    class Meta:
        model = CallRecording
        fields = [
            "caller_name",
            "caller_number",
            "assistant_name",
            "outcome",
            "sentiment",
            "duration_seconds",
            "call_date",
        ]
