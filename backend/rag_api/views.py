import logging
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, render
from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.generics import CreateAPIView, ListAPIView
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Conversation, Document
from .rag_service.document_processor import DocumentProcessor
from .rag_service.service import AIServices
from .serializers import (
    ConversationSerializer,
    DocumentSerializer,
    DocumentUploadSerializer,
    HistorySerializer,
    QuestionSerializer,
    UserRegistrationSerializer,
    UserSerializer,
)

logger = logging.getLogger(__name__)


class RegisterView(APIView):
  permission_classes = [permissions.AllowAny]

  def post(self, request):
    serializer = UserRegistrationSerializer(data=request.data)

    if serializer.is_valid():
      user = serializer.save()
      refresh = RefreshToken.for_user(user)

      return Response(
          {
              "user": UserSerializer(user).data,
              "token": {
                  "refresh": str(refresh),
                  "access": str(refresh.access),
              },
          },
          status=status.HTTP_201_CREATED,
      )

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
  permission_classes = [permissions.AllowAny]

  def post(self, request):
    username = request.data.get("username")
    password = request.data.get("password")

    if username and password:
      user = authenticate(username=username, password=password)

      if user:
        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "user": UserSerializer(user).data,
                "token": {
                    "refresh": str(refresh),
                    "access": str(refresh.access),
                },
            },
            status=status.HTTP_200_OK,
        )

    return Response(
        {"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED
    )