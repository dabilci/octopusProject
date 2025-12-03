from django.contrib import admin
from .models import Provider

# Register your models here.

@admin.register(Provider)
class admin_provider(admin.ModelAdmin):
    list_display = ("user","first_name","last_name","email","phone","fcm_token","company_name","country","city","tax_number","authorized_phone","authorized_email","services")
    
