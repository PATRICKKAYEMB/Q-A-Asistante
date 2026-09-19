import logging
import os
import shutil
from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, render
from drf_spectacular.utils import extend_schema
from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.generics import CreateAPIView, ListAPIView
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Conversation, Document
from .rag_service.document_processor import DocumentProcessor
from .rag_service.service import AIServices
from .models import Conversation
from .serializers import (
    ConversationSerializer,
    DocumentSerializer,
    DocumentUploadSerializer,
    HistorySerializer,
    LoginSerializer,
    QuestionSerializer,
    UserRegistrationSerializer,
    UserSerializer,
)

logger = logging.getLogger(__name__)


class RegisterView(APIView):
  permission_classes = [permissions.AllowAny]
  serializer_class = UserRegistrationSerializer

  @extend_schema(request=UserRegistrationSerializer)
  def post(self, request):
    serializer = UserRegistrationSerializer(data=request.data)

    if serializer.is_valid():
      user = serializer.save()
      refresh = RefreshToken.for_user(user)

      access_token = refresh.access_token
      return Response(
          {
              "user": UserSerializer(user).data,
              "token": {
                  "refresh": str(refresh),
                  "access": str(access_token),
              },
          },
          status=status.HTTP_201_CREATED,
      )

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
  permission_classes = [permissions.AllowAny]
  serializer_class = LoginSerializer

  @extend_schema(request=LoginSerializer)
  def post(self, request):
    serializer = LoginSerializer(data=request.data)
    if not serializer.is_valid():
      return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    email = serializer.validated_data.get('email')
    password = serializer.validated_data.get('password')

    user = User.objects.filter(email=email).first()

    if user and user.check_password(password):
      refresh = RefreshToken.for_user(user)
      access_token = refresh.access_token
      return Response(
          {
              "user": UserSerializer(user).data,
              "token": {
                  "refresh": str(refresh),
                  "access": str(access_token),
              },
          },
          status=status.HTTP_200_OK,
      )

    return Response(
        {"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED
    )


class DocumentCreateView(APIView):
  permission_classes = [permissions.IsAuthenticated]
  serializer_class = DocumentUploadSerializer
  parser_classes = (MultiPartParser, FormParser)

  @extend_schema(
      request={
          'multipart/form-data': {
              'type': 'object',
              'properties': {
                  'title': {'type': 'string', 'description': 'Document title'},
                  'file': {'type': 'string', 'format': 'binary'},
              },
              'required': ['title', 'file'],
          }
      },
      responses={201: DocumentSerializer},
  )
  def post(self, request):
    serializer = DocumentUploadSerializer(data=request.data)

    if serializer.is_valid():
      file = serializer.validated_data['file']
      title = serializer.validated_data.get('title')
      file_type = file.name.split('.')[-1].lower()

      document = Document.objects.create(
          user=request.user,
          file=file,
          title=title,
          file_size=file.size,
          file_type=file_type,
      )

      try:
        processor = DocumentProcessor()
        processor.document_process(document)
        return Response(
            DocumentSerializer(document).data,
            status=status.HTTP_201_CREATED,
        )
      except Exception:
        document.delete()
        logger.exception("Error while processing uploaded document")
        return Response(
            {'error': 'erreur lors de l\'enregistrement', 'details': str(__import__('traceback').format_exc())},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
  
class DocumentListView(ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = DocumentSerializer

    def get_queryset(self):
        return Document.objects.filter(user=self.request.user)


class DocumentDeleteView(APIView):
  permission_classes = [permissions.IsAuthenticated]

  def delete(self, request, document_id):
    document = get_object_or_404(Document, user=self.request.user, id=document_id)

    try:
      if document.vector_store_id:
        vector_store_path = os.path.join(
            settings.CHROMA_PERSIST_DIRECTORY,
            document.vector_store_id,
        )

        if os.path.exists(vector_store_path):
          shutil.rmtree(vector_store_path)

      document.delete()
      return Response(status=status.HTTP_204_NO_CONTENT)

    except Exception as e:
      logger.error(f"Error deleting document: {str(e)}")
      return Response(
          {'error': 'Failed to delete document'},
          status=status.HTTP_500_INTERNAL_SERVER_ERROR,
      )


class QAView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = QuestionSerializer

    @extend_schema(request=QuestionSerializer)
    def post(self, request):
        serializer = QuestionSerializer(data=request.data)

        if serializer.is_valid():
            document_id = serializer.validated_data['document_id']
            question = serializer.validated_data['question']

            document = get_object_or_404(
                Document,
                user=request.user,
                id=document_id,
                processed=True,
            )

            try:
                ai_service = AIServices()
                results = ai_service.answer_question(document, question)

                qa_conversation = Conversation.objects.create(
                    document=document,
                    user=request.user,
                    question=question,
                    response=results['answer'],
                    response_time=results.get('response_time', 0.0),
                )

                return Response(
                    ConversationSerializer(qa_conversation).data,
                    status=status.HTTP_200_OK,
                )

            except Exception as e:
                logger.error(f'Error generating answer: {str(e)}')
                return Response(
                    {'error': 'Failed generating answer'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)