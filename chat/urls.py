from django.urls import path
from . import views


urlpatterns = [
    path('api/v1/conversations', views.list_conversations),
    path('api/v1/conversations/start', views.start_conversation),
    path('api/v1/conversations/<int:id>/messages', views.conversation_messages),
]