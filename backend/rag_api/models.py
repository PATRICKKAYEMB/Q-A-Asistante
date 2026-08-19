from django.db import models
from django.contrib.auth.models import User

class Document(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='documents')
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to='documents/')
    file_type = models.CharField(max_length=10)
    file_size = models.IntegerField()
    processed = models.BooleanField(default=False)
    vector_store_id = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class Conversation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='conversations')
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='conversations')
    question = models.TextField()
    response = models.TextField()
    is_user = models.BooleanField(default=False)
    response_time = models.FloatField(null=True, blank=True) 
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Conversation sur {self.document.title}"