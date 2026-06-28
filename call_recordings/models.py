from django.db import models


class CallRecording(models.Model):
    """A single VAPI call, parsed from an 'end-of-call-report' webhook event."""

    caller_name = models.CharField(max_length=255, null=True, blank=True)
    caller_number = models.CharField(max_length=32, null=True, blank=True)
    assistant_name = models.CharField(max_length=255, null=True, blank=True)
    audio_url = models.URLField(max_length=1000, null=True, blank=True)
    call_date = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.IntegerField(null=True, blank=True)
    outcome = models.CharField(max_length=64, null=True, blank=True)
    sentiment = models.CharField(max_length=32, null=True, blank=True)
    ai_summary = models.TextField(null=True, blank=True)
    transcript = models.TextField(null=True, blank=True)
    lead_score = models.CharField(max_length=32, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-call_date", "-created_at"]
        indexes = [
            models.Index(fields=["-call_date"]),
            models.Index(fields=["outcome"]),
            models.Index(fields=["assistant_name"]),
            models.Index(fields=["caller_name"]),
            models.Index(fields=["-created_at"]),
        ]

    def __str__(self):
        return f"{self.caller_name or 'Unknown'} - {self.call_date or self.created_at}"
