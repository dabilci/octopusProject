from django.db import models
from django.contrib.auth.models import User
from requests.models import ServiceRequest


class RequestNote(models.Model):
    """
    Asistanların taleplere ekleyeceği iç notlar.
    Sadece asistanlar ve adminler görebilir.
    """

    request = models.ForeignKey(ServiceRequest, on_delete=models.CASCADE, related_name='notes')
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='request_notes')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Note by {self.author} on Request #{self.request.id}"


class Assistant(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='assistant_profile')
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.first_name} {self.last_name}"