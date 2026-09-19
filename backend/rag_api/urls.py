from django.urls import include, path

urlpatterns = [
    path('', include('rag_api.rag_service.urls')),
]
