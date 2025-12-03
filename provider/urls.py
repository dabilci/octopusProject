from django.contrib import admin
from django.urls import path
from . import views


urlpatterns = [
    path('api/v1/auth/register/provider', views.register_provider),
    path('api/v1/auth/login', views.login),
    path('api/v1/auth/verify-email', views.verify_email),
    path('api/v1/users/me', views.get_profile),
    path('api/v1/users/me/fcm-token', views.update_fcm_token),
]