from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase


class MessageViewTests(APITestCase):
    def test_message_endpoint_returns_api_status(self):
        response = self.client.get(reverse("message"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {"message": "Bizora API is running."})
