from django.contrib import admin
from django.urls import path
from . import views


urlpatterns = [
    path('api/v1/requests', views.requests),
    path('api/v1/requests/<int:id>', views.request_detail),
    path('api/v1/requests/<int:id>/cancel', views.cancel_request),
    path('api/v1/requests/<int:id>/feedback', views.feedback_request),
]