from django.contrib import admin
from .models import Client

# Register your models here.

@admin.register(Client)
class admin_kullanici(admin.ModelAdmin):
    list_display = ("user","first_name","last_name","email","gender","birth_date","address","profile_photo","fcm_token","passport_first_name","passport_last_name","passport_number","passport_expiry_date","passport_country")
    