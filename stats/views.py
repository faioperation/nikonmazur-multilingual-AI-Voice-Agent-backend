from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from api.permissions import IsViewerOrAbove

from . import services
from .serializers import RecentCallSerializer


class DashboardOverviewView(APIView):
    """GET /api/v1/stats/overview/ — headline cards, activity and outcomes."""

    permission_classes = [IsViewerOrAbove]

    def get(self, request, *args, **kwargs):
        data = services.get_overview()
        data["recent_calls"] = RecentCallSerializer(data["recent_calls"], many=True).data
        return Response(data)


class CallAnalyticsView(APIView):
    """GET /api/v1/stats/analytics/?filter=today — time-series analytics."""

    permission_classes = [IsViewerOrAbove]

    def get(self, request, *args, **kwargs):
        filter_name = request.query_params.get("filter", "today")
        if filter_name not in services.ANALYTICS_FILTERS:
            return Response(
                {
                    "detail": "Invalid filter.",
                    "allowed": list(services.ANALYTICS_FILTERS),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(services.get_analytics(filter_name))


class AISummariesView(APIView):
    """GET /api/v1/stats/ai-summaries/ — summary cards, opportunities, agents."""

    permission_classes = [IsViewerOrAbove]

    def get(self, request, *args, **kwargs):
        return Response(services.get_ai_summaries())
