# from rest_framework.response import Response
# from rest_framework.views import APIView

# from .services import get_all_cars

# class CarAvailableAPIView(APIView):

#     def _response(self):
#         return Response(get_all_cars())

#     def get(self, request):
#         return self._response()

#     def post(self, request):
#         return self._response()


from django.http import HttpResponse
from rest_framework.views import APIView

from .services import get_all_cars


class CarAvailableAPIView(APIView):

    authentication_classes = []
    permission_classes = []

    def post(self, request):
        return HttpResponse(
            get_all_cars(),
            content_type="text/plain; charset=utf-8",
        )
