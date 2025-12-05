from django.db import models
from django.contrib.auth.models import User
# Create your models here.

# Client (Müşteri)
class Client(models.Model):
    GENDER = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    ]
    
    # Kişisel
    user = models.ForeignKey(User,on_delete=models.CASCADE)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    gender = models.CharField(max_length=1, choices=GENDER)
    birth_date = models.DateField()
    address = models.TextField()
    profile_photo = models.ImageField(upload_to='clients/',null=True,blank=True)
    fcm_token = models.CharField(max_length=255, blank=True, null=True)

    #dogrulama kodu
    email_verification_code = models.CharField(max_length=6, null=True, blank=True)
    email_verified = models.BooleanField(default=False)
    verification_code_created_at = models.DateTimeField(null=True, blank=True)
    
    # Pasaport
    passport_first_name = models.CharField(max_length=100)
    passport_last_name = models.CharField(max_length=100)
    passport_number = models.CharField(max_length=50)
    passport_expiry_date = models.DateField()
    passport_country = models.CharField(max_length=100)
