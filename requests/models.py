from django.db import models
from django.contrib.auth.models import User
from client.models import Client
from provider.models import Provider


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(null=True, blank=True)
    
    def __str__(self):
        return self.name


class ServiceRequest(models.Model):
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('PENDING_ASSISTANT', 'Pending Assistant'),
        ('IN_REVIEW', 'In Review'),
        ('OFFER_READY', 'Offer Ready'),
        ('PAYMENT_LOCKED', 'Payment Locked'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    # Kim oluşturdu
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='requests')
    
    # Hangi asistana atandı
    assistant = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_requests')
    
    # Hangi provider'a gidecek
    provider = models.ForeignKey(Provider, on_delete=models.SET_NULL, null=True, blank=True, related_name='requests')
    
    # Talep detayları
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='requests')
    description = models.TextField()
    file = models.FileField(upload_to='requests/', null=True, blank=True)
    budget = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Durum
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    
    # Tarihler
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.client} - {self.category.name} ({self.status})"


class RequestHistory(models.Model):
    request = models.ForeignKey(ServiceRequest, on_delete=models.CASCADE, related_name='history')
    old_status = models.CharField(max_length=20, null=True, blank=True)
    new_status = models.CharField(max_length=20)
    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    changed_at = models.DateTimeField(auto_now_add=True)
    note = models.TextField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.request.id}: {self.old_status} → {self.new_status}"
    
    class Meta:
        verbose_name_plural = "Request Histories"


class RequestFeedback(models.Model):
    request = models.OneToOneField(ServiceRequest, on_delete=models.CASCADE, related_name='feedback')
    rating = models.IntegerField()  # 1-5
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.request.id} - {self.rating}/5"