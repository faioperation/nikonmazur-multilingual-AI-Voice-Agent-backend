from django.urls import path

from .views import AISummariesView, CallAnalyticsView, DashboardOverviewView

urlpatterns = [
    path("stats/overview/", DashboardOverviewView.as_view(), name="stats-overview"),
    path("stats/analytics/", CallAnalyticsView.as_view(), name="stats-analytics"),
    path(
        "stats/ai-summaries/",
        AISummariesView.as_view(),
        name="stats-ai-summaries",
    ),
]
