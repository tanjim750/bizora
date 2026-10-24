from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from app.serializers import MessageSerializer


class MessageView(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        serializer = MessageSerializer({'message': 'Bizora API is running.'})
        return Response(serializer.data)
