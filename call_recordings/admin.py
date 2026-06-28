from django.contrib import admin
from .models import CallRecording


@admin.register(CallRecording)
class CallRecordingAdmin(admin.ModelAdmin):
    list_display = (
        "caller_name",
        "caller_number",
        "assistant_name",
        "outcome",
        "lead_score",
        "sentiment",
        "duration_seconds",
        "call_date",
    )
    list_filter = ("outcome", "lead_score", "sentiment", "assistant_name")
    search_fields = ("caller_name", "caller_number", "transcript", "ai_summary")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("-call_date",)
