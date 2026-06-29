from rest_framework.response import Response
from rest_framework.views import APIView

from .services import check_availability


import logging

logger = logging.getLogger(__name__)


class CarAvailableAPIView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        import logging

        logger = logging.getLogger(__name__)
        # logger.info("VAPI RAW BODY: %s", request.data)

        tool_call_list = request.data.get("message", {}).get("toolCallList", [])

        results = []

        for tool_call in tool_call_list:
            tool_call_id = tool_call.get("id", "")
            arguments = tool_call.get("function", {}).get("arguments", {})
            model = arguments.get("model", "")

            result = check_availability(model)

            results.append(
                {
                    "toolCallId": tool_call_id,
                    "result": result,
                }
            )

        if not results:
            model = request.data.get("model", "")
            results.append(
                {
                    "toolCallId": request.data.get("toolCallId", "unknown"),
                    "result": check_availability(model),
                }
            )

        return Response({"results": results})
