from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from .models import Provider
import json
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from .models import Provider
import json

@csrf_exempt
def login(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            email = data.get('email')
            password = data.get('password')
            
            if not email or not password:
                return JsonResponse({
                    "success": False,
                    "error": "Email ve şifre gerekli"
                }, status=400)
            
            # Email ile User'ı bul
            user = User.objects.filter(email=email).first()

            if user is None:
                return JsonResponse({"error": "Kullanıcı bulunamadı"}, status=404)
            
            # Django'nun authenticate fonksiyonu (şifreyi kontrol eder)
            auth_user = authenticate(username=user.username, password=password)
            
            if auth_user is None:
                return JsonResponse({
                    "success": False,
                    "error": "Şifre hatalı"
                }, status=401)
            
            # User'a bağlı Provider'ı bul
            try:
                provider = Provider.objects.get(user=auth_user)
            except Provider.DoesNotExist:
                return JsonResponse({
                    "success": False,
                    "error": "Provider profili bulunamadı"
                }, status=404)
            
            return JsonResponse({
                "success": True,
                "user": {
                    "id": provider.id,
                    "email": provider.email,
                    "first_name": provider.first_name,
                    "last_name": provider.last_name,
                    "company_name": provider.company_name,
                    "role": "PROVIDER"
                }
            })
            
        except json.JSONDecodeError:
            return JsonResponse({"success": False, "error": "Geçersiz JSON"}, status=400)
    
    return JsonResponse({"error": "Sadece POST"}, status=405)

@csrf_exempt
def register_provider(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            
            required_fields = [
                'first_name', 'last_name', 'email', 'password', 'phone',
                'company_name', 'country', 'city', 'tax_number',
                'authorized_phone', 'authorized_email', 'services'
            ]
            
            for field in required_fields:
                if not data.get(field):
                    return JsonResponse({
                        "success": False,
                        "error": f"{field} alanı zorunludur"
                    }, status=400)
            
            # Email zaten var mı?
            if User.objects.filter(email=data['email']).exists():
                return JsonResponse({
                    "success": False,
                    "error": "Bu email adresi zaten kayıtlı"
                }, status=400)
            
            # Önce User oluştur (şifre burada)
            user = User.objects.create_user(
                username=data['email'],
                email=data['email'],
                password=data['password']
            )
            
            # Sonra Provider oluştur ve User'a bağla
            provider = Provider.objects.create(
                user=user,
                first_name=data['first_name'],
                last_name=data['last_name'],
                email=data['email'],
                phone=data['phone'],
                company_name=data['company_name'],
                country=data['country'],
                city=data['city'],
                tax_number=data['tax_number'],
                authorized_phone=data['authorized_phone'],
                authorized_email=data['authorized_email'],
                services=data['services'],
                fcm_token=data.get('fcm_token')
            )
            
            return JsonResponse({
                "success": True,
                "user": {
                    "id": provider.id,
                    "email": provider.email,
                    "company_name": provider.company_name,
                    "role": "PROVIDER"
                }
            }, status=201)
            
        except json.JSONDecodeError:
            return JsonResponse({"success": False, "error": "Geçersiz JSON"}, status=400)
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=500)
    
    return JsonResponse({"error": "Sadece POST"}, status=405)



@csrf_exempt
@login_required
def get_profile(request):
    # Giriş yapmış User'a bağlı Provider'ı bul
    try:
        provider = Provider.objects.get(user=request.user)
    except Provider.DoesNotExist:
        return JsonResponse({"success": False, "error": "Provider profili bulunamadı"}, status=404)

    if request.method == "GET":
        data = {
            "id": provider.id,
            "role": "PROVIDER",
            "email": provider.email,
            "first_name": provider.first_name,
            "last_name": provider.last_name,
            "phone": provider.phone,
            "company_name": provider.company_name,
            "country": provider.country,
            "city": provider.city,
            "tax_number": provider.tax_number,
            "authorized_phone": provider.authorized_phone,
            "authorized_email": provider.authorized_email,
            "services": provider.services,
        }
        return JsonResponse({"success": True, "user": data})

    elif request.method == "PUT":
        try:
            payload = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"success": False, "error": "Geçersiz JSON"}, status=400)

        allowed_fields = [
            "first_name", "last_name", "phone", "company_name", "country",
            "city", "tax_number", "authorized_phone", "authorized_email", "services",
        ]

        updated = False
        for field in allowed_fields:
            if field in payload:
                setattr(provider, field, payload[field])
                updated = True

        if not updated:
            return JsonResponse({"success": False, "error": "Güncellenecek alan bulunamadı"}, status=400)

        provider.save()
        return JsonResponse({"success": True, "message": "Profil güncellendi"})

    return JsonResponse({"error": "Sadece GET veya PUT"}, status=405)


@csrf_exempt
@login_required
def update_fcm_token(request):
    if request.method != "PUT":
        return JsonResponse({"error": "Sadece PUT kabul edilir"}, status=405)

    try:
        provider = Provider.objects.get(user=request.user)
    except Provider.DoesNotExist:
        return JsonResponse({"success": False, "error": "Provider profili bulunamadı"}, status=404)

    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "Geçersiz JSON"}, status=400)

    token_value = payload.get("fcm_token")
    if not token_value:
        return JsonResponse({"success": False, "error": "fcm_token alanı zorunludur"}, status=400)

    provider.fcm_token = token_value
    provider.save()

    return JsonResponse({"success": True, "message": "FCM token kaydedildi"})


@csrf_exempt
def verify_email(request):
    if request.method == "POST":
        return JsonResponse({
            "message": "Email verified successfully"
        })
