"""Aggregation logic for the dashboard stats endpoints.

Every metric is computed in the database via aggregate()/annotate() so the
dashboard stays fast even with thousands of CallRecording rows. Calls are
grouped by ``call_date`` (the moment the call actually happened); rows with a
null ``call_date`` are naturally excluded by the range filters.
"""

import re
from datetime import datetime, time, timedelta

from django.db.models import Avg, Count, Max, Sum
from django.db.models.functions import (
    ExtractHour,
    ExtractWeekDay,
    TruncDate,
)
from django.utils import timezone

from call_recordings.models import CallRecording

_WEEKDAY_LABELS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]

ANALYTICS_FILTERS = ("today", "yesterday", "last_7_days", "last_30_days", "this_month")

OUTCOME_CHOICES = (
    ("buy", "Buy"),
    ("leasing", "Leasing Request"),
    ("test drive", "Test Drive"),
    ("reserve", "Reserve"),
    ("callback", "Callback"),
    ("enquiry", "Enquiry"),
)
_OUTCOME_LABELS = dict(OUTCOME_CHOICES)


OPPORTUNITY_OUTCOMES = ("buy", "test drive", "leasing")


def _start_of_day(d):
    """Return a timezone-aware datetime at 00:00 of the given local date."""
    return timezone.make_aware(datetime.combine(d, time.min))


def _week_bounds(today):
    """Monday-start (ISO) week containing ``today`` as a [start, end) date pair."""
    week_start = today - timedelta(days=today.weekday())  # Mon=0..Sun=6
    return week_start, week_start + timedelta(days=7)


def _format_duration(seconds):
    """Format a duration in seconds as ``"3m 42s"``."""
    seconds = int(round(seconds or 0))
    return f"{seconds // 60}m {seconds % 60}s"


_PEAK_RANGES = [
    (0, "12:00 AM - 03:59 AM"),
    (4, "04:00 AM - 07:59 AM"),
    (8, "08:00 AM - 11:59 AM"),
    (12, "12:00 PM - 03:59 PM"),
    (16, "04:00 PM - 07:59 PM"),
    (20, "08:00 PM - 11:59 PM"),
]


def _outcome_counts(queryset):
    """One grouped query -> ``{stored_outcome: count}`` for the queryset.

    Returned raw so a single query can feed both the breakdown and any
    individual outcome card (e.g. test drives).
    """
    return {
        row["outcome"]: row["count"]
        for row in queryset.values("outcome").annotate(count=Count("id"))
    }


def _outcome_breakdown(counts):
    """Count + percentage for every canonical outcome, in fixed order.

    Always returns all six outcomes (zero-filled) so charts render the same
    structure regardless of the data. ``counts`` is the dict from
    :func:`_outcome_counts`; percentages are relative to the known outcomes.
    """
    total = sum(counts.get(value, 0) for value, _ in OUTCOME_CHOICES)
    return [
        {
            "name": label,
            "count": counts.get(value, 0),
            "percentage": round(counts.get(value, 0) * 100 / total) if total else 0,
        }
        for value, label in OUTCOME_CHOICES
    ]


def get_overview():
    """Build the full payload for the dashboard overview endpoint.

    Optimised to four queries: one weekday-grouped query covers today's totals,
    this-week's totals and the activity chart; the all-time outcome query feeds
    both the breakdown and the test-drive card.
    """
    today = timezone.localdate()
    week_start_date, week_end_date = _week_bounds(today)

    week_qs = CallRecording.objects.filter(
        call_date__gte=_start_of_day(week_start_date),
        call_date__lt=_start_of_day(week_end_date),
    )

    week_rows = {
        row["weekday"]: row
        for row in week_qs.annotate(weekday=ExtractWeekDay("call_date"))
        .values("weekday")
        .annotate(count=Count("id"), seconds=Sum("duration_seconds"))
    }
    today_weekday = (today.weekday() + 1) % 7 + 1
    today_row = week_rows.get(today_weekday, {})

    week_calls = sum(row["count"] for row in week_rows.values())
    week_seconds = sum((row["seconds"] or 0) for row in week_rows.values())

    month_avg = CallRecording.objects.filter(
        call_date__gte=_start_of_day(today.replace(day=1))
    ).aggregate(avg=Avg("duration_seconds"))["avg"]

    all_outcomes = _outcome_counts(CallRecording.objects.all())

    return {
        "cards": {
            "calls_today": today_row.get("count", 0),
            "calls_this_week": week_calls,
            "minutes_today": round((today_row.get("seconds") or 0) / 60),
            "minutes_this_week": round(week_seconds / 60),
            "average_duration": _format_duration(month_avg),
            "test_drive_count": all_outcomes.get("test drive", 0),
        },
        "call_activity": [
            {"day": label, "count": week_rows.get(index + 1, {}).get("count", 0)}
            for index, label in enumerate(_WEEKDAY_LABELS)
        ],
        "call_outcomes": _outcome_breakdown(all_outcomes),
        "recent_calls": CallRecording.objects.all()[:5],
    }


def _filter_range(filter_name, today):
    """Return the [start, end) date pair covered by an analytics filter."""
    if filter_name == "today":
        return today, today + timedelta(days=1)
    if filter_name == "yesterday":
        return today - timedelta(days=1), today
    if filter_name == "last_7_days":
        return today - timedelta(days=6), today + timedelta(days=1)
    if filter_name == "last_30_days":
        return today - timedelta(days=29), today + timedelta(days=1)
    return today.replace(day=1), today + timedelta(days=1)


def filtered_queryset(filter_name):
    """Single source of truth for analytics date filtering.

    Builds the CallRecording queryset for a named filter once; every analytics
    widget reuses the returned queryset so a filter change updates all of them
    consistently. Also returns the [start, end) date range so callers can build
    matching day labels without re-deriving the dates.
    """
    today = timezone.localdate()
    start_date, end_date = _filter_range(filter_name, today)
    queryset = CallRecording.objects.filter(
        call_date__gte=_start_of_day(start_date),
        call_date__lt=_start_of_day(end_date),
    )
    return queryset, start_date, end_date


def get_analytics(filter_name):
    """Build the analytics payload for a validated filter name.

    Three queries total: the daily series (count + minutes per day), the outcome
    counts, and the peak-hour grouping. The summary is derived from the daily
    series in memory, so it costs no additional query.
    """
    queryset, start_date, end_date = filtered_queryset(filter_name)

    calls_per_day, minutes_per_day, total_calls, total_seconds = _daily_series(
        queryset, start_date, end_date, filter_name
    )

    return {
        "filter": filter_name,
        "summary": {
            "total_calls": total_calls,
            "total_minutes": round(total_seconds / 60),
            "average_duration": _format_duration(
                total_seconds / total_calls if total_calls else 0
            ),
        },
        "calls_per_day": calls_per_day,
        "minutes_per_day": minutes_per_day,
        "outcome_breakdown": _outcome_breakdown(_outcome_counts(queryset)),
        "peak_call_hours": _peak_hours(queryset),
    }


def _daily_series(queryset, start_date, end_date, filter_name):
    """One bucket per calendar day in the range, zero-filled.

    Labels adapt to the filter: weekday names for ``last_7_days``, otherwise a
    short ``"Jun 28"`` date label. Also returns the range totals so the caller
    can build the summary without another query.
    """
    rows = {
        row["day"]: row
        for row in queryset.annotate(day=TruncDate("call_date"))
        .values("day")
        .annotate(count=Count("id"), seconds=Sum("duration_seconds"))
    }

    calls, minutes = [], []
    total_calls, total_seconds = 0, 0
    day = start_date
    while day < end_date:
        row = rows.get(day)
        count = row["count"] if row else 0
        seconds = (row["seconds"] if row else 0) or 0
        total_calls += count
        total_seconds += seconds
        if filter_name == "last_7_days":
            label = _WEEKDAY_LABELS[(day.weekday() + 1) % 7]
        else:
            label = day.strftime("%b %d").replace(" 0", " ")
        calls.append({"label": label, "count": count})
        minutes.append({"label": label, "minutes": round(seconds / 60)})
        day += timedelta(days=1)
    return calls, minutes, total_calls, total_seconds


def _peak_hours(queryset):
    """Calls grouped into 4-hour windows, ordered by count descending.

    Hour grouping is done in the database; collapsing the 24 hourly rows into
    six 4-hour buckets is a trivial in-memory fold.
    """
    counts = [0] * len(_PEAK_RANGES)
    for row in (
        queryset.annotate(hour=ExtractHour("call_date"))
        .values("hour")
        .annotate(count=Count("id"))
    ):
        counts[row["hour"] // 4] += row["count"]

    result = [
        {"label": label, "count": counts[index]}
        for index, (_, label) in enumerate(_PEAK_RANGES)
    ]
    result.sort(key=lambda bucket: bucket["count"], reverse=True)
    return result


def _highlight(text, limit=90):
    """Pull a short highlight (~half a line) out of an ``ai_summary``.

    Returns the first sentence, or a truncated snippet if that sentence is long.
    """
    if not text:
        return ""
    text = " ".join(text.split())
    sentence = re.split(r"(?<=[.!?])\s+", text, maxsplit=1)[0]
    if len(sentence) <= limit:
        return sentence
    return text[:limit].rstrip() + "…"


def _summary_card(title, queryset):
    """Total calls + per-outcome counts for a date-bounded queryset.

    One grouped query (via :func:`_outcome_counts`) yields every outcome count
    and the total, so a card costs a single database hit.
    """
    counts = _outcome_counts(queryset)
    return {
        "title": title,
        "total_calls": sum(counts.values()),
        "outcomes": [
            {"name": label, "count": counts.get(value, 0)}
            for value, label in OUTCOME_CHOICES
        ],
    }


def _opportunity_list(queryset, limit=5):
    """Latest ``limit`` calls as ``{caller_name, outcome, highlight}`` rows."""
    rows = queryset.order_by("-call_date", "-created_at").values(
        "caller_name", "outcome", "ai_summary"
    )[:limit]
    return [
        {
            "caller_name": row["caller_name"] or "Unknown Caller",
            "outcome": _OUTCOME_LABELS.get(row["outcome"], row["outcome"]),
            "highlight": _highlight(row["ai_summary"]),
        }
        for row in rows
    ]


def _calls_needing_attention(limit=5):
    """Latest negative-sentiment enquiries as ``{caller_name, highlight}`` rows."""
    rows = (
        CallRecording.objects.filter(outcome="enquiry", sentiment__iexact="negative")
        .order_by("-call_date", "-created_at")
        .values("caller_name", "ai_summary")[:limit]
    )
    return [
        {
            "caller_name": row["caller_name"] or "Unknown Caller",
            "highlight": _highlight(row["ai_summary"]),
        }
        for row in rows
    ]


def _best_performing_agent():
    """Assistant with the most calls; ties broken by most recent activity."""
    row = (
        CallRecording.objects.exclude(assistant_name__isnull=True)
        .exclude(assistant_name="")
        .values("assistant_name")
        .annotate(
            total_calls=Count("id"),
            avg=Avg("duration_seconds"),
            latest=Max("call_date"),
        )
        .order_by("-total_calls", "-latest")
        .first()
    )
    if not row:
        return {"assistant_name": None, "total_calls": 0, "average_duration": "0m 0s"}
    return {
        "assistant_name": row["assistant_name"],
        "total_calls": row["total_calls"],
        "average_duration": _format_duration(row["avg"]),
    }


def get_ai_summaries():
    """Build the full payload for the AI Summaries dashboard endpoint."""
    today = timezone.localdate()
    week_start_date, week_end_date = _week_bounds(today)

    today_qs = CallRecording.objects.filter(
        call_date__gte=_start_of_day(today),
        call_date__lt=_start_of_day(today + timedelta(days=1)),
    )
    week_qs = CallRecording.objects.filter(
        call_date__gte=_start_of_day(week_start_date),
        call_date__lt=_start_of_day(week_end_date),
    )
    month_qs = CallRecording.objects.filter(
        call_date__gte=_start_of_day(today.replace(day=1))
    )

    return {
        "today_summary": _summary_card("Today", today_qs),
        "this_week_summary": _summary_card("This Week", week_qs),
        "this_month_summary": _summary_card("This Month", month_qs),
        "top_opportunities": _opportunity_list(
            CallRecording.objects.filter(outcome__in=OPPORTUNITY_OUTCOMES)
        ),
        "calls_needing_attention": _calls_needing_attention(),
        "best_performing_agent": _best_performing_agent(),
    }
