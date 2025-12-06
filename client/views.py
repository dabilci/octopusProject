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
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import random
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import authenticate
from django.contrib.auth import login as auth_login

api_key = "910cbd974644203847a785c08da62079"



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

            # 6 haneli doğrulama kodu oluştur
            verification_code = str(random.randint(100000, 999999))
            client.email_verification_code = verification_code
            client.verification_code_created_at = timezone.now()
            client.save()

            # Email gönder
            send_email(
                subject="Email Doğrulama Kodu - AssistAll",
                mesaj=f"""
                <h2>Merhaba {client.first_name},</h2>
                <p>Email doğrulama kodunuz: <strong>{verification_code}</strong></p>
                <p>Bu kod 3 dakika geçerlidir.</p>
                """,
                reciever=client.email
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
        try:
            data = json.loads(request.body)
            email = data.get('email')
            code = data.get('code')
            
            if not email or not code:
                return JsonResponse({
                    "success": False,
                    "error": "Email ve kod gerekli"
                }, status=400)
            
            # Client'ı bul
            try:
                client = Client.objects.get(email=email)
            except Client.DoesNotExist:
                return JsonResponse({
                    "success": False,
                    "error": "Kullanıcı bulunamadı"
                }, status=404)
            
            # Zaten doğrulanmış mı?
            if client.email_verified:
                return JsonResponse({
                    "success": False,
                    "error": "Email zaten doğrulanmış"
                }, status=400)
            
            # Kod süresi dolmuş mu? (3 dakika)
            if client.verification_code_created_at:
                expire_time = client.verification_code_created_at + timedelta(minutes=3)
                if timezone.now() > expire_time:
                    return JsonResponse({
                        "success": False,
                        "error": "Doğrulama kodu süresi dolmuş. Yeni kod isteyin."
                    }, status=400)
            
            # Kod doğru mu?
            if client.email_verification_code != code:
                return JsonResponse({
                    "success": False,
                    "error": "Doğrulama kodu hatalı"
                }, status=400)
            
            # Doğrula
            client.email_verified = True
            client.email_verification_code = None
            client.save()
            
            return JsonResponse({
                "success": True,
                "message": "Email başarıyla doğrulandı"
            })
            
        except json.JSONDecodeError:
            return JsonResponse({"success": False, "error": "Geçersiz JSON"}, status=400)
    
    return JsonResponse({"error": "Sadece POST"}, status=405)

@csrf_exempt
def resend_verification_code(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            email = data.get('email')
            
            if not email:
                return JsonResponse({"success": False, "error": "Email gerekli"}, status=400)
            
            try:
                client = Client.objects.get(email=email)
            except Client.DoesNotExist:
                return JsonResponse({"success": False, "error": "Kullanıcı bulunamadı"}, status=404)
            
            if client.email_verified:
                return JsonResponse({"success": False, "error": "Email zaten doğrulanmış"}, status=400)
            
            # Yeni kod oluştur
            verification_code = str(random.randint(100000, 999999))
            client.email_verification_code = verification_code
            client.verification_code_created_at = timezone.now()
            client.save()
            
            send_email(
                subject="Yeni Doğrulama Kodu - AssistAll",
                mesaj=f"""
                <h2>Merhaba {client.first_name},</h2>
                <p>Yeni email doğrulama kodunuz: <strong>{verification_code}</strong></p>
                <p>Bu kod 3 dakika geçerlidir.</p>
                """,
                reciever=client.email
            )
            
            return JsonResponse({"success": True, "message": "Yeni doğrulama kodu gönderildi"})
            
        except json.JSONDecodeError:
            return JsonResponse({"success": False, "error": "Geçersiz JSON"}, status=400)
    
    return JsonResponse({"error": "Sadece POST"}, status=405)


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
            
            # ✅ SESSION BAŞLAT
            auth_login(request, auth_user)
            
            # Kullanıcının rolünü belirle
            from assistant.models import Assistant
            from provider.models import Provider
            
            # Assistant mı?
            assistant = Assistant.objects.filter(user=auth_user).first()
            if assistant:
                return JsonResponse({
                    "success": True,
                    "user": {
                        "id": assistant.id,
                        "email": assistant.email,
                        "first_name": assistant.first_name,
                        "last_name": assistant.last_name,
                        "role": "ASSISTANT"
                    }
                })
            
            # Provider mı?
            provider = Provider.objects.filter(user=auth_user).first()
            if provider:
                return JsonResponse({
                    "success": True,
                    "user": {
                        "id": provider.id,
                        "email": provider.email,
                        "first_name": provider.first_name,
                        "last_name": provider.last_name,
                        "role": "PROVIDER"
                    }
                })
            
            # Client mı?
            client = Client.objects.filter(user=auth_user).first()
            if client:
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
            
            # Hiçbiri değilse (sadece superuser olabilir)
            if auth_user.is_superuser:
                return JsonResponse({
                    "success": True,
                    "user": {
                        "id": auth_user.id,
                        "email": auth_user.email,
                        "first_name": auth_user.first_name or auth_user.username,
                        "last_name": auth_user.last_name or "",
                        "role": "ADMIN"
                    }
                })
            
            return JsonResponse({
                "success": False,
                "error": "Kullanıcı profili bulunamadı"
            }, status=404)
            
        except json.JSONDecodeError:
            return JsonResponse({"success": False, "error": "Geçersiz JSON"}, status=400)
    
    return JsonResponse({"error": "Sadece POST"}, status=405)


def send_email(subject, mesaj, reciever):
    sender = "info@asistall.com"
    password = "@Asistall.com34"

    email = MIMEMultipart()
    email["From"] = sender
    email["Subject"] = subject
    email["To"] = reciever
    email.attach(MIMEText(mesaj, 'html'))
    with smtplib.SMTP("smtp.asistall.com", 587) as smtp:
        smtp.ehlo()
        smtp.login(sender, password)
        mail_liste = [reciever]
        smtp.sendmail(sender, mail_liste, email.as_string())