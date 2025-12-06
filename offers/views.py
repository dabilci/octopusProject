from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
import json

from .models import Offer
from requests.models import ServiceRequest, RequestHistory
from provider.models import Provider
from client.models import Client
from assistant.models import Assistant


def is_assistant_or_admin(user):
    if user.is_superuser:
        return True
    return Assistant.objects.filter(user=user).exists()


# =============================================================================
# 1. POST /api/v1/offers
# Asistan: Bir talep için yeni teklif oluşturur
# =============================================================================
@csrf_exempt
@login_required
def create_offer(request):
    if request.method != "POST":
        return JsonResponse({"error": "Sadece POST kabul edilir"}, status=405)
    
    # Asistan kontrolü
    if not is_assistant_or_admin(request.user):
        return JsonResponse({
            "success": False,
            "error": "Bu işlem için yetkiniz yok"
        }, status=403)
    
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "Geçersiz JSON"}, status=400)
    
    # Zorunlu alanlar
    request_id = data.get('request_id')
    provider_id = data.get('provider_id')
    price = data.get('price')
    description = data.get('description', '')
    
    if not request_id:
        return JsonResponse({"success": False, "error": "request_id zorunludur"}, status=400)
    if not provider_id:
        return JsonResponse({"success": False, "error": "provider_id zorunludur"}, status=400)
    if not price:
        return JsonResponse({"success": False, "error": "price zorunludur"}, status=400)
    
    # Request var mı?
    try:
        service_request = ServiceRequest.objects.get(id=request_id)
    except ServiceRequest.DoesNotExist:
        return JsonResponse({"success": False, "error": "Talep bulunamadı"}, status=404)
    
    # Provider var mı?
    try:
        provider = Provider.objects.get(id=provider_id)
    except Provider.DoesNotExist:
        return JsonResponse({"success": False, "error": "Provider bulunamadı"}, status=404)
    
    # Teklif oluştur
    offer = Offer.objects.create(
        request=service_request,
        provider=provider,
        created_by=request.user,
        price=price,
        description=description,
        status='PENDING'
    )
    
    return JsonResponse({
        "success": True,
        "message": "Teklif oluşturuldu",
        "offer": {
            "id": offer.id,
            "request_id": service_request.id,
            "provider": {
                "id": provider.id,
                "company_name": provider.company_name,
            },
            "price": str(offer.price),
            "description": offer.description,
            "status": offer.status,
            "created_at": offer.created_at.isoformat(),
        }
    }, status=201)










































"""


YEDEKLEME KISMI :



# =============================================================================
# 2. GET /api/v1/requests/{requestId}/offers
# Müşteri: Talebe gelen teklifleri görür
# =============================================================================
@csrf_exempt
@login_required
def list_offers(request, request_id):
    if request.method != "GET":
        return JsonResponse({"error": "Sadece GET kabul edilir"}, status=405)
    
    # Client kontrolü
    try:
        client = Client.objects.get(user=request.user)
    except Client.DoesNotExist:
        # Asistan da görebilir
        if not is_assistant_or_admin(request.user):
            return JsonResponse({"success": False, "error": "Yetkiniz yok"}, status=403)
        client = None
    
    # Talep var mı?
    try:
        service_request = ServiceRequest.objects.get(id=request_id)
    except ServiceRequest.DoesNotExist:
        return JsonResponse({"success": False, "error": "Talep bulunamadı"}, status=404)
    
    # Client ise kendi talebi mi kontrol et
    if client and service_request.client != client:
        return JsonResponse({"success": False, "error": "Bu talep size ait değil"}, status=403)
    
    # Teklifleri listele
    offers = Offer.objects.filter(request=service_request).order_by('-created_at')
    
    result = []
    for offer in offers:
        result.append({
            "id": offer.id,
            "provider": {
                "id": offer.provider.id,
                "company_name": offer.provider.company_name,
                "city": offer.provider.city,
                "country": offer.provider.country,
            },
            "price": str(offer.price),
            "description": offer.description,
            "status": offer.status,
            "created_at": offer.created_at.isoformat(),
        })
    
    return JsonResponse({
        "success": True,
        "count": len(result),
        "offers": result
    })


# =============================================================================
# 3. POST /api/v1/offers/{id}/accept
# Müşteri: Teklifi kabul eder
# =============================================================================
@csrf_exempt
@login_required
def accept_offer(request, id):
    if request.method != "POST":
        return JsonResponse({"error": "Sadece POST kabul edilir"}, status=405)
    
    # Client kontrolü
    try:
        client = Client.objects.get(user=request.user)
    except Client.DoesNotExist:
        return JsonResponse({"success": False, "error": "Client profili bulunamadı"}, status=404)
    
    # Teklif var mı?
    try:
        offer = Offer.objects.get(id=id)
    except Offer.DoesNotExist:
        return JsonResponse({"success": False, "error": "Teklif bulunamadı"}, status=404)
    
    # Bu teklif müşterinin talebine mi ait?
    if offer.request.client != client:
        return JsonResponse({"success": False, "error": "Bu teklif size ait değil"}, status=403)
    
    # Teklif zaten işlenmiş mi?
    if offer.status != 'PENDING':
        return JsonResponse({
            "success": False,
            "error": f"Bu teklif zaten {offer.status} durumunda"
        }, status=400)
    
    # Teklifi kabul et
    offer.status = 'ACCEPTED'
    offer.save()
    
    # Diğer teklifleri reddet
    Offer.objects.filter(request=offer.request).exclude(id=offer.id).update(status='REJECTED')
    
    # Request'i güncelle - provider ata ve status değiştir
    service_request = offer.request
    old_status = service_request.status
    service_request.provider = offer.provider
    service_request.status = 'PAYMENT_LOCKED'
    service_request.save()
    
    # History kaydı
    RequestHistory.objects.create(
        request=service_request,
        old_status=old_status,
        new_status='PAYMENT_LOCKED',
        changed_by=request.user,
        note=f"Teklif kabul edildi. Provider: {offer.provider.company_name}, Fiyat: {offer.price} TL"
    )
    
    return JsonResponse({
        "success": True,
        "message": "Teklif kabul edildi. Ödeme ekranına yönlendiriliyorsunuz.",
        "offer": {
            "id": offer.id,
            "price": str(offer.price),
            "provider": offer.provider.company_name,
        },
        "request": {
            "id": service_request.id,
            "status": service_request.status,
        }
    })


# =============================================================================
# 4. POST /api/v1/offers/{id}/reject
# Müşteri: Teklifi reddeder
# =============================================================================
@csrf_exempt
@login_required
def reject_offer(request, id):
    if request.method != "POST":
        return JsonResponse({"error": "Sadece POST kabul edilir"}, status=405)
    
    # Client kontrolü
    try:
        client = Client.objects.get(user=request.user)
    except Client.DoesNotExist:
        return JsonResponse({"success": False, "error": "Client profili bulunamadı"}, status=404)
    
    # Teklif var mı?
    try:
        offer = Offer.objects.get(id=id)
    except Offer.DoesNotExist:
        return JsonResponse({"success": False, "error": "Teklif bulunamadı"}, status=404)
    
    # Bu teklif müşterinin talebine mi ait?
    if offer.request.client != client:
        return JsonResponse({"success": False, "error": "Bu teklif size ait değil"}, status=403)
    
    # Teklif zaten işlenmiş mi?
    if offer.status != 'PENDING':
        return JsonResponse({
            "success": False,
            "error": f"Bu teklif zaten {offer.status} durumunda"
        }, status=400)
    
    # Teklifi reddet
    offer.status = 'REJECTED'
    offer.save()
    
    return JsonResponse({
        "success": True,
        "message": "Teklif reddedildi"
    })






"""