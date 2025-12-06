from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.contrib.auth.models import User
from django.db.models import Q
import json

from requests.models import ServiceRequest, RequestHistory
from provider.models import Provider
from .models import RequestNote


def is_assistant_or_admin(user):
    if user.is_superuser:
        return True
    # Assistant modeline bağlı mı kontrol et
    from .models import Assistant
    return Assistant.objects.filter(user=user).exists()


def assistant_required(view_func):
    """
    Sadece asistan veya admin erişebilir decorator'ı.
    """
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({
                "success": False,
                "error": "Giriş yapmanız gerekiyor"
            }, status=401)
        
        if not is_assistant_or_admin(request.user):
            return JsonResponse({
                "success": False,
                "error": "Bu işlem için yetkiniz yok"
            }, status=403)
        
        return view_func(request, *args, **kwargs)
    return wrapper


# =============================================================================
# 1. GET /api/v1/assistant/tasks
# Havuzdaki atanmamış veya asistana atanmış işleri listele
# =============================================================================
@csrf_exempt
@assistant_required
def list_tasks(request):
    if request.method != "GET":
        return JsonResponse({"error": "Sadece GET kabul edilir"}, status=405)
    
    # Query parametreleri
    status_filter = request.GET.get('status')
    assigned_to_me = request.GET.get('assigned_to_me', 'false').lower() == 'true'
    
    # Atanmamış (assistant=None) VEYA bu asistana atanmış işler
    if assigned_to_me:
        tasks = ServiceRequest.objects.filter(assistant=request.user)
    else:
        # Havuzdaki tüm işler: atanmamış veya bu asistana atanmış
        tasks = ServiceRequest.objects.filter(
            Q(assistant__isnull=True) | Q(assistant=request.user)
        )
    
    # Status filtresi
    if status_filter:
        tasks = tasks.filter(status=status_filter)
    
    # Sadece asistan bekleyen veya review'da olan işleri göster
    tasks = tasks.filter(
        status__in=['PENDING_ASSISTANT', 'IN_REVIEW', 'OFFER_READY']
    ).order_by('-created_at')
    
    result = []
    for task in tasks:
        result.append({
            "id": task.id,
            "client": {
                "id": task.client.id,
                "first_name": task.client.first_name,
                "last_name": task.client.last_name,
                "email": task.client.email,
            },
            "category": {
                "id": task.category.id,
                "name": task.category.name,
            },
            "description": task.description,
            "budget": str(task.budget),
            "status": task.status,
            "assistant": {
                "id": task.assistant.id,
                "username": task.assistant.username,
            } if task.assistant else None,
            "provider": {
                "id": task.provider.id,
                "company_name": task.provider.company_name,
            } if task.provider else None,
            "created_at": task.created_at.isoformat(),
            "updated_at": task.updated_at.isoformat(),
        })
    
    return JsonResponse({
        "success": True,
        "count": len(result),
        "tasks": result
    })


# =============================================================================
# 2. POST /api/v1/assistant/requests/{id}/assign
# İşi kendine veya başkasına ata
# =============================================================================
@csrf_exempt
@assistant_required
def assign_request(request, id):

    # GET: Atanabilecek asistan listesini döndür
    if request.method == "GET":
        from .models import Assistant
        
        assistants = Assistant.objects.all()
        
        result = []
        for asst in assistants:
            result.append({
                "id": asst.id,
                "first_name": asst.first_name,
                "last_name": asst.last_name,
                "email": asst.email,
            })
        
        return JsonResponse({
            "success": True,
            "count": len(result),
            "assistants": result
        })


    #POST kontrolü

    if request.method != "POST":
        return JsonResponse({"error": "Sadece POST kabul edilir"}, status=405)
    
    # Talebi bul
    try:
        service_request = ServiceRequest.objects.get(id=id)
    except ServiceRequest.DoesNotExist:
        return JsonResponse({
            "success": False,
            "error": "Talep bulunamadı"
        }, status=404)
    
    # Body'den assistant_id al (opsiyonel - yoksa kendine ata)
    try:
        data = json.loads(request.body) if request.body else {}
    except json.JSONDecodeError:
        data = {}
    
    assistant_id = data.get('assistant_id')
    
    if assistant_id:
        # Başka bir asistana ata (Assistant ID üzerinden)
        from .models import Assistant
        try:
            target_assistant_profile = Assistant.objects.get(id=assistant_id)
            target_assistant = target_assistant_profile.user
        except Assistant.DoesNotExist:
            return JsonResponse({
                "success": False,
                "error": "Asistan bulunamadı"
            }, status=404)
    else:
        # Kendine ata
        target_assistant = request.user
    
    old_assistant = service_request.assistant
    service_request.assistant = target_assistant
    
    # Eğer durum PENDING_ASSISTANT ise IN_REVIEW'a çek
    old_status = service_request.status
    if service_request.status == 'PENDING_ASSISTANT':
        service_request.status = 'IN_REVIEW'
    
    service_request.save()
    
    # History kaydı
    if old_status != service_request.status:
        RequestHistory.objects.create(
            request=service_request,
            old_status=old_status,
            new_status=service_request.status,
            changed_by=request.user,
            note=f"İş {target_assistant.username} kullanıcısına atandı"
        )
    
    return JsonResponse({
        "success": True,
        "message": f"Talep {target_assistant.username} kullanıcısına atandı",
        "request": {
            "id": service_request.id,
            "status": service_request.status,
            "assistant": {
                "id": target_assistant.id,
                "username": target_assistant.username,
            }
        }
    })


# =============================================================================
# 3. PUT /api/v1/assistant/requests/{id}/status
# Talep durumunu güncelle (Örn: In Review)
# =============================================================================
@csrf_exempt
@assistant_required
def update_request_status(request, id):
    if request.method != "PUT":
        return JsonResponse({"error": "Sadece PUT kabul edilir"}, status=405)
    
    # Talebi bul
    try:
        service_request = ServiceRequest.objects.get(id=id)
    except ServiceRequest.DoesNotExist:
        return JsonResponse({
            "success": False,
            "error": "Talep bulunamadı"
        }, status=404)
    
    # Body'den yeni status al
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({
            "success": False,
            "error": "Geçersiz JSON"
        }, status=400)
    
    new_status = data.get('status')
    note = data.get('note', '')
    
    if not new_status:
        return JsonResponse({
            "success": False,
            "error": "status alanı zorunludur"
        }, status=400)
    
    # Geçerli status kontrolü
    valid_statuses = [choice[0] for choice in ServiceRequest.STATUS_CHOICES]
    if new_status not in valid_statuses:
        return JsonResponse({
            "success": False,
            "error": f"Geçersiz status. Geçerli değerler: {valid_statuses}"
        }, status=400)
    
    old_status = service_request.status
    
    # Aynı status ise güncelleme yapma
    if old_status == new_status:
        return JsonResponse({
            "success": False,
            "error": "Talep zaten bu durumda"
        }, status=400)
    
    service_request.status = new_status
    service_request.save()
    
    # History kaydı
    RequestHistory.objects.create(
        request=service_request,
        old_status=old_status,
        new_status=new_status,
        changed_by=request.user,
        note=note
    )
    
    return JsonResponse({
        "success": True,
        "message": f"Talep durumu {old_status} -> {new_status} olarak güncellendi",
        "request": {
            "id": service_request.id,
            "status": service_request.status,
            "updated_at": service_request.updated_at.isoformat(),
        }
    })


# =============================================================================
# 4. GET /api/v1/assistant/providers/search
# Talebe uygun hizmet verenleri ara/filtrele
# =============================================================================
@csrf_exempt
@assistant_required
def search_providers(request):
    if request.method != "GET":
        return JsonResponse({"error": "Sadece GET kabul edilir"}, status=405)
    
    # Query parametreleri
    query = request.GET.get('q', '')
    country = request.GET.get('country')
    city = request.GET.get('city')
    service = request.GET.get('service')
    
    providers = Provider.objects.all()
    
    # Genel arama (isim, şirket adı, email)
    if query:
        providers = providers.filter(
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(company_name__icontains=query) |
            Q(email__icontains=query)
        )
    
    # Ülke filtresi
    if country:
        providers = providers.filter(country__icontains=country)
    
    # Şehir filtresi
    if city:
        providers = providers.filter(city__icontains=city)
    
    # Hizmet filtresi
    if service:
        providers = providers.filter(services__icontains=service)
    
    # Sadece email doğrulanmış provider'ları göster
    providers = providers.filter(email_verified=True)
    
    result = []
    for provider in providers:
        result.append({
            "id": provider.id,
            "first_name": provider.first_name,
            "last_name": provider.last_name,
            "email": provider.email,
            "phone": provider.phone,
            "company_name": provider.company_name,
            "country": provider.country,
            "city": provider.city,
            "services": provider.services,
        })
    
    return JsonResponse({
        "success": True,
        "count": len(result),
        "providers": result
    })


# =============================================================================
# 5. POST /api/v1/assistant/requests/{id}/notes
# Talebe sadece asistanların göreceği iç not ekle
# =============================================================================
@csrf_exempt
@assistant_required
def add_request_note(request, id):
    if request.method == "POST":
        # Talebi bul
        try:
            service_request = ServiceRequest.objects.get(id=id)
        except ServiceRequest.DoesNotExist:
            return JsonResponse({
                "success": False,
                "error": "Talep bulunamadı"
            }, status=404)
        
        # Body'den not içeriğini al
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({
                "success": False,
                "error": "Geçersiz JSON"
            }, status=400)
        
        content = data.get('content')
        
        if not content:
            return JsonResponse({
                "success": False,
                "error": "content alanı zorunludur"
            }, status=400)
        
        # Notu oluştur
        note = RequestNote.objects.create(
            request=service_request,
            author=request.user,
            content=content
        )
        
        return JsonResponse({
            "success": True,
            "message": "Not eklendi",
            "note": {
                "id": note.id,
                "content": note.content,
                "author": {
                    "id": note.author.id,
                    "username": note.author.username,
                },
                "created_at": note.created_at.isoformat(),
            }
        }, status=201)
    
    elif request.method == "GET":
        # Talepteki tüm notları listele
        try:
            service_request = ServiceRequest.objects.get(id=id)
        except ServiceRequest.DoesNotExist:
            return JsonResponse({
                "success": False,
                "error": "Talep bulunamadı"
            }, status=404)
        
        notes = RequestNote.objects.filter(request=service_request).order_by('-created_at')
        
        result = []
        for note in notes:
            result.append({
                "id": note.id,
                "content": note.content,
                "author": {
                    "id": note.author.id if note.author else None,
                    "username": note.author.username if note.author else "Deleted User",
                },
                "created_at": note.created_at.isoformat(),
                "updated_at": note.updated_at.isoformat(),
            })
        
        return JsonResponse({
            "success": True,
            "count": len(result),
            "notes": result
        })
    
    return JsonResponse({"error": "Sadece GET veya POST kabul edilir"}, status=405)
