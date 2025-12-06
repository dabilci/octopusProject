from django.urls import path
from . import views


urlpatterns = [
    path('api/v1/offers', views.create_offer),
    path('api/v1/requests/<int:request_id>/offers', views.list_offers),
    path('api/v1/offers/<int:id>/accept', views.accept_offer),
    path('api/v1/offers/<int:id>/reject', views.reject_offer),
]