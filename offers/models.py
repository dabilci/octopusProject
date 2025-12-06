from django.db import models
from django.contrib.auth.models import User
from requests.models import ServiceRequest
from provider.models import Provider


class Offer(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('ACCEPTED', 'Accepted'),
        ('REJECTED', 'Rejected'),
    ]
    
    # Hangi talep için
    request = models.ForeignKey(ServiceRequest, on_delete=models.CASCADE, related_name='offers')
    
    # Hangi provider'dan
    provider = models.ForeignKey(Provider, on_delete=models.CASCADE, related_name='offers')
    
    # Kim oluşturdu (asistan)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_offers')
    
    # Teklif detayları
    price = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True, null=True)
    
    # Durum
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    
    # Tarihler
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Offer #{self.id} - {self.provider.company_name} - {self.price} TL"