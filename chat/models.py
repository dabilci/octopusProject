from django.db import models
from django.contrib.auth.models import User
from requests.models import ServiceRequest


class Conversation(models.Model):
    TYPE_CHOICES = [
        ('CLIENT_ASSISTANT', 'Client - Assistant'),
        ('ASSISTANT_PROVIDER', 'Assistant - Provider'),
    ]
    
    request = models.ForeignKey(ServiceRequest, on_delete=models.CASCADE, related_name='conversations')
    conversation_type = models.CharField(max_length=30, choices=TYPE_CHOICES)
    participants = models.ManyToManyField(User, related_name='conversations')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Conversation #{self.id} - Request #{self.request.id}"


class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='sent_messages')
    content = models.TextField(blank=True, null=True)
    file = models.FileField(upload_to='chat_files/', blank=True, null=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    
    def __str__(self):
        return f"Message by {self.sender} at {self.created_at}"