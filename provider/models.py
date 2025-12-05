from django.db import models
from django.contrib.auth.models import User

# Create your models here.

class Provider(models.Model):
    user = models.ForeignKey(User,on_delete=models.CASCADE)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20)
    fcm_token = models.CharField(max_length=255, blank=True, null=True)
    
    company_name = models.CharField(max_length=200)
    country = models.CharField(max_length=100)
    city = models.CharField(max_length=100)
    tax_number = models.CharField(max_length=50)

    email_verification_code = models.CharField(max_length=6, null=True, blank=True)
    email_verified = models.BooleanField(default=False)
    verification_code_created_at = models.DateTimeField(null=True, blank=True)
    
    authorized_phone = models.CharField(max_length=20)
    authorized_email = models.EmailField()
    services = models.TextField() 