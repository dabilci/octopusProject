from django.contrib import admin
from .models import Category, ServiceRequest, RequestHistory, RequestFeedback


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['id', 'name']
    search_fields = ['name']


@admin.register(ServiceRequest)
class ServiceRequestAdmin(admin.ModelAdmin):
    list_display = ['id', 'client', 'category', 'status', 'assistant', 'provider', 'created_at']
    list_filter = ['status', 'category']
    search_fields = ['client__first_name', 'client__last_name', 'description']


@admin.register(RequestHistory)
class RequestHistoryAdmin(admin.ModelAdmin):
    list_display = ['request', 'old_status', 'new_status', 'changed_by', 'changed_at']
    list_filter = ['new_status']


@admin.register(RequestFeedback)
class RequestFeedbackAdmin(admin.ModelAdmin):
    list_display = ['request', 'rating', 'created_at']
    list_filter = ['rating']