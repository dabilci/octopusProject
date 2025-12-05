import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from client.models import Client
from .models import Category, ServiceRequest, RequestHistory, RequestFeedback


@csrf_exempt
@login_required
def requests(request):
    # Giriş yapmış kullanıcının Client profilini bul
    try:
        client = Client.objects.get(user=request.user)
    except Client.DoesNotExist:
        return JsonResponse({"success": False, "error": "Client profili bulunamadı"}, status=404)
    
    # GET: Talepleri listele + Kategorileri döndür
    if request.method == "GET":
        # Kategoriler
        categories = list(Category.objects.all().values('id', 'name', 'description'))
        
        # Müşterinin talepleri
        status_filter = request.GET.get('status')  # ?status=DRAFT gibi filtre
        
        queryset = ServiceRequest.objects.filter(client=client)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        requests_list = []
        for req in queryset.order_by('-created_at'):
            requests_list.append({
                "id": req.id,
                "category": {
                    "id": req.category.id,
                    "name": req.category.name
                },
                "description": req.description,
                "budget": str(req.budget),
                "status": req.status,
                "created_at": req.created_at.isoformat(),
                "updated_at": req.updated_at.isoformat(),
            })
        
        return JsonResponse({
            "success": True,
            "categories": categories,
            "requests": requests_list
        })
    
    # POST: Yeni talep oluştur
    elif request.method == "POST":
        try:
            data = json.loads(request.body)
            
            # Zorunlu alanlar
            required_fields = ['category_id', 'description', 'budget']
            for field in required_fields:
                if not data.get(field):
                    return JsonResponse({
                        "success": False,
                        "error": f"{field} alanı zorunludur"
                    }, status=400)
            
            # Kategori var mı?
            try:
                category = Category.objects.get(id=data['category_id'])
            except Category.DoesNotExist:
                return JsonResponse({
                    "success": False,
                    "error": "Geçersiz kategori"
                }, status=400)
            
            # Talep oluştur
            service_request = ServiceRequest.objects.create(
                client=client,
                category=category,
                description=data['description'],
                budget=data['budget'],
                status='DRAFT'
            )
            
            # Tarihçeye ekle
            RequestHistory.objects.create(
                request=service_request,
                old_status=None,
                new_status='DRAFT',
                changed_by=request.user,
                note="Talep oluşturuldu"
            )
            
            return JsonResponse({
                "success": True,
                "message": "Talep başarıyla oluşturuldu",
                "request": {
                    "id": service_request.id,
                    "category": category.name,
                    "description": service_request.description,
                    "budget": str(service_request.budget),
                    "status": service_request.status,
                    "created_at": service_request.created_at.isoformat()
                }
            }, status=201)
            
        except json.JSONDecodeError:
            return JsonResponse({"success": False, "error": "Geçersiz JSON"}, status=400)
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=500)
    
    return JsonResponse({"error": "Sadece GET veya POST"}, status=405)


@csrf_exempt
@login_required
def request_detail(request, id):
    # Client kontrolü
    try:
        client = Client.objects.get(user=request.user)
    except Client.DoesNotExist:
        return JsonResponse({"success": False, "error": "Client profili bulunamadı"}, status=404)
    
    # Talep var mı ve bu müşteriye mi ait?
    try:
        service_request = ServiceRequest.objects.get(id=id, client=client)
    except ServiceRequest.DoesNotExist:
        return JsonResponse({"success": False, "error": "Talep bulunamadı"}, status=404)
    
    if request.method == "GET":
        # Tarihçe
        history = list(service_request.history.order_by('-changed_at').values(
            'old_status', 'new_status', 'changed_at', 'note'
        ))
        
        return JsonResponse({
            "success": True,
            "request": {
                "id": service_request.id,
                "category": {
                    "id": service_request.category.id,
                    "name": service_request.category.name
                },
                "description": service_request.description,
                "budget": str(service_request.budget),
                "status": service_request.status,
                "file": request.build_absolute_uri(service_request.file.url) if service_request.file else None,
                "assistant": service_request.assistant.username if service_request.assistant else None,
                "provider": service_request.provider.company_name if service_request.provider else None,
                "created_at": service_request.created_at.isoformat(),
                "updated_at": service_request.updated_at.isoformat(),
            },
            "history": history
        })
    
    return JsonResponse({"error": "Sadece GET"}, status=405)


@csrf_exempt
@login_required
def cancel_request(request, id):
    # Client kontrolü
    try:
        client = Client.objects.get(user=request.user)
    except Client.DoesNotExist:
        return JsonResponse({"success": False, "error": "Client profili bulunamadı"}, status=404)
    
    # Talep var mı ve bu müşteriye mi ait?
    try:
        service_request = ServiceRequest.objects.get(id=id, client=client)
    except ServiceRequest.DoesNotExist:
        return JsonResponse({"success": False, "error": "Talep bulunamadı"}, status=404)
    
    if request.method == "POST":
        # Sadece belirli durumlarda iptal edilebilir
        cancellable_statuses = ['DRAFT', 'PENDING_ASSISTANT', 'IN_REVIEW']
        
        if service_request.status not in cancellable_statuses:
            return JsonResponse({
                "success": False,
                "error": "Bu talep artık iptal edilemez"
            }, status=400)
        
        old_status = service_request.status
        service_request.status = 'CANCELLED'
        service_request.save()
        
        # Tarihçeye ekle
        RequestHistory.objects.create(
            request=service_request,
            old_status=old_status,
            new_status='CANCELLED',
            changed_by=request.user,
            note="Müşteri tarafından iptal edildi"
        )
        
        return JsonResponse({
            "success": True,
            "message": "Talep iptal edildi"
        })
    
    return JsonResponse({"error": "Sadece POST"}, status=405)


@csrf_exempt
@login_required
def feedback_request(request, id):
    # Client kontrolü
    try:
        client = Client.objects.get(user=request.user)
    except Client.DoesNotExist:
        return JsonResponse({"success": False, "error": "Client profili bulunamadı"}, status=404)
    
    # Talep var mı ve bu müşteriye mi ait?
    try:
        service_request = ServiceRequest.objects.get(id=id, client=client)
    except ServiceRequest.DoesNotExist:
        return JsonResponse({"success": False, "error": "Talep bulunamadı"}, status=404)
    
    if request.method == "POST":
        # Sadece tamamlanmış taleplere feedback verilebilir
        if service_request.status != 'COMPLETED':
            return JsonResponse({
                "success": False,
                "error": "Sadece tamamlanmış taleplere puan verilebilir"
            }, status=400)
        
        # Zaten feedback var mı?
        if hasattr(service_request, 'feedback'):
            return JsonResponse({
                "success": False,
                "error": "Bu talebe zaten puan verilmiş"
            }, status=400)
        
        try:
            data = json.loads(request.body)
            
            rating = data.get('rating')
            comment = data.get('comment', '')
            
            if not rating or rating < 1 or rating > 5:
                return JsonResponse({
                    "success": False,
                    "error": "Rating 1-5 arasında olmalıdır"
                }, status=400)
            
            feedback = RequestFeedback.objects.create(
                request=service_request,
                rating=rating,
                comment=comment
            )
            
            return JsonResponse({
                "success": True,
                "message": "Değerlendirmeniz kaydedildi",
                "feedback": {
                    "rating": feedback.rating,
                    "comment": feedback.comment
                }
            })
            
        except json.JSONDecodeError:
            return JsonResponse({"success": False, "error": "Geçersiz JSON"}, status=400)
    
    return JsonResponse({"error": "Sadece POST"}, status=405)