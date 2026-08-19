from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Document, Conversation


class UserRegistrationSerializer(serializers.ModelSerializer):  # CORRIGÉ : Nom de la classe (Registration)
    password = serializers.CharField(write_only=True, min_length=8)  # CORRIGÉ : min_length (et non mon_length)
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ('username', 'email', 'password', 'password_confirm', 'first_name')

    def validate(self, data):
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError("Passwords don't match")
        return data

    def create(self, validated_data):
        validated_data.pop('password_confirm')  # CORRIGÉ : password_confirm (et non password_confim)
        user = User.objects.create_user(**validated_data)
        return user  


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        # CORRIGÉ : On ne renvoie jamais le mot de passe dans un sérialiseur de lecture/profil
        fields = ('id', 'username', 'email', 'first_name', 'last_name')


class DocumentUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = ('file', 'title')  

   
    def validate_file(self, value):
        if value.size > 50 * 1024 * 1024:
            raise serializers.ValidationError("File size cannot exceed 50MB")

        allowed_extensions = ['.txt', '.pdf', '.docx'] 
        file_extension = '.' + value.name.split('.')[-1].lower()

        if file_extension not in allowed_extensions:
            raise serializers.ValidationError("File type not supported")

        return value


class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = ('id', 'title', 'file_type', 'file_size', 'processed', 'created_at')


class QuestionSerializer(serializers.Serializer):  
    document_id = serializers.IntegerField()  
    question = serializers.CharField(max_length=1000)


class ConversationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Conversation
        fields = ('id', 'question', 'response', 'response_time', 'created_at')


class HistorySerializer(serializers.ModelSerializer):
    
    document_title = serializers.CharField(source='document.title', read_only=True)

    class Meta:
        model = Conversation
        fields = ('id', 'document_title', 'question', 'response', 'created_at')  