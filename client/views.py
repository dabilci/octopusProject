from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.contrib.auth import authenticate
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from .models import Client
import json
from django.contrib.auth.hashers import make_password, check_password
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from .models import Client
import json



# Create your views here.

@csrf_exempt
def register_client(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            
            required_fields = [
                'first_name', 'last_name', 'email', 'password', 'gender',
                'birth_date', 'address', 'passport_first_name', 'passport_last_name',
                'passport_number', 'passport_expiry_date', 'passport_country'
            ]
            
            for field in required_fields:
                if not data.get(field):
                    return JsonResponse({
                        "success": False,
                        "error": f"{field} alani zorunludur"
                    }, status=400)
            
            # Email zaten var mı?
            if User.objects.filter(email=data['email']).exists():
                return JsonResponse({
                    "success": False,
                    "error": "Bu email adresi zaten kayitli"
                }, status=400)
            
            # Önce User oluştur (şifre burada)
            user = User.objects.create_user(
                username=data['email'],  # username olarak email kullan
                email=data['email'],
                password=data['password']  # Django otomatik hashler
            )
            
            # Sonra Client oluştur ve User'a bağla
            client = Client.objects.create(
                user=user,
                first_name=data['first_name'],
                last_name=data['last_name'],
                email=data['email'],
                gender=data['gender'],
                birth_date=data['birth_date'],
                address=data['address'],
                passport_first_name=data['passport_first_name'],
                passport_last_name=data['passport_last_name'],
                passport_number=data['passport_number'],
                passport_expiry_date=data['passport_expiry_date'],
                passport_country=data['passport_country']
            )
            
            return JsonResponse({
                "success": True,
                "user": {
                    "id": client.id,
                    "email": client.email,
                    "first_name": client.first_name,
                    "last_name": client.last_name,
                    "role": "CLIENT"
                }
            }, status=201)
            
        except json.JSONDecodeError:
            return JsonResponse({"success": False, "error": "Geçersiz JSON"}, status=400)
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=500)
    
    return JsonResponse({"error": "Sadece POST"}, status=405)


@csrf_exempt
def verify_email(request):
    if request.method == "POST":
        return JsonResponse({
            "message": "Email verified successfully"
        })


@csrf_exempt
@login_required
def get_profile(request):
    # Giriş yapmış User'a bağlı Client'ı bul
    try:
        client = Client.objects.get(user=request.user)
    except Client.DoesNotExist:
        return JsonResponse({"success": False, "error": "Client profili bulunamadı"}, status=404)

    if request.method == "GET":
        data = {
            "id": client.id,
            "role": "CLIENT",
            "email": client.email,
            "first_name": client.first_name,
            "last_name": client.last_name,
            "gender": client.gender,
            "birth_date": str(client.birth_date) if client.birth_date else None,
            "address": client.address,
            "profile_photo": request.build_absolute_uri(client.profile_photo.url) if client.profile_photo else None,
            "passport": {
                "first_name": client.passport_first_name,
                "last_name": client.passport_last_name,
                "number": client.passport_number,
                "expiry_date": str(client.passport_expiry_date) if client.passport_expiry_date else None,
                "country": client.passport_country,
            },
        }
        return JsonResponse({"success": True, "user": data})

    elif request.method == "PUT":
        try:
            payload = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"success": False, "error": "Geçersiz JSON"}, status=400)

        allowed_fields = [
            "first_name", "last_name", "gender", "birth_date", "address",
            "passport_first_name", "passport_last_name", "passport_number",
            "passport_expiry_date", "passport_country",
        ]

        updated = False
        for field in allowed_fields:
            if field in payload:
                setattr(client, field, payload[field])
                updated = True

        if not updated:
            return JsonResponse({"success": False, "error": "Güncellenecek alan bulunamadı"}, status=400)

        client.save()
        return JsonResponse({"success": True, "message": "Profil güncellendi"})

    return JsonResponse({"error": "Sadece GET veya PUT"}, status=405)


@csrf_exempt
@login_required
def update_fcm_token(request):
    if request.method != "PUT":
        return JsonResponse({"error": "Sadece PUT kabul edilir"}, status=405)

    try:
        client = Client.objects.get(user=request.user)
    except Client.DoesNotExist:
        return JsonResponse({"success": False, "error": "Client profili bulunamadı"}, status=404)

    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "Geçersiz JSON"}, status=400)

    token_value = payload.get("fcm_token")
    if not token_value:
        return JsonResponse({"success": False, "error": "fcm_token alanı zorunludur"}, status=400)

    client.fcm_token = token_value
    client.save()

    return JsonResponse({"success": True, "message": "FCM token kaydedildi"})

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
            
            # User'a bağlı Client'ı bul
            try:
                client = Client.objects.get(user=auth_user)
            except Client.DoesNotExist:
                return JsonResponse({
                    "success": False,
                    "error": "Client profili bulunamadı"
                }, status=404)
            
            return JsonResponse({
                "success": True,
                "user": {
                    "id": client.id,
                    "email": client.email,
                    "first_name": client.first_name,
                    "last_name": client.last_name,
                    "role": "CLIENT"
                }
            })
            
        except json.JSONDecodeError:
            return JsonResponse({"success": False, "error": "Geçersiz JSON"}, status=400)
    
    return JsonResponse({"error": "Sadece POST"}, status=405)