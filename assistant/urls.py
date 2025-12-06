from django.contrib import admin
from django.urls import path
from . import views


urlpatterns = [
    path('api/v1/assistant/tasks', views.list_tasks),
    path('api/v1/assistant/requests/<int:id>/assign', views.assign_request),
    path('api/v1/assistant/requests/<int:id>/status', views.update_request_status),
    path('api/v1/assistant/providers/search', views.search_providers),
    path('api/v1/assistant/requests/<int:id>/notes', views.add_request_note),
]