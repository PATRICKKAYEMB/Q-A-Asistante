from django.urls import path

from ..views import (
    DocumentCreateView,
    DocumentDeleteView,
    DocumentListView,
    LoginView,
    QAView,
    RegisterView,
)

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('documents/', DocumentListView.as_view(), name='documents-list'),
    path('documents/create/', DocumentCreateView.as_view(), name='documents-create'),
    path('documents/<int:document_id>/delete/', DocumentDeleteView.as_view(), name='documents-delete'),
    path('qa/', QAView.as_view(), name='qa'),
]
