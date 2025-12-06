from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.contrib.auth.models import User
from django_ratelimit.decorators import ratelimit
import json
import bleach
import magic

from .models import Conversation, Message
from requests.models import ServiceRequest


# =============================================================================
# GÜVENLİK SABİTLERİ
# =============================================================================
ALLOWED_FILE_TYPES = {
    'image/jpeg': ['.jpg', '.jpeg'],
    'image/png': ['.png'],
    'image/gif': ['.gif'],
    'application/pdf': ['.pdf'],
    'application/msword': ['.doc'],
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
MAX_MESSAGE_LENGTH = 5000
ALLOWED_HTML_TAGS = []  # Hiçbir HTML tag'i izin verme


# =============================================================================
# GÜVENLİK FONKSİYONLARI
# =============================================================================
def sanitize_message(content):
    """XSS saldırılarını engelle - HTML tag'lerini temizle"""
    if not content:
        return content
    return bleach.clean(content, tags=ALLOWED_HTML_TAGS, strip=True)


def validate_file(file):
    """Dosya güvenlik kontrolü"""
    errors = []
    
    # 1. Boyut kontrolü
    if file.size > MAX_FILE_SIZE:
        errors.append("Dosya 10MB'dan büyük olamaz")
        return errors
    
    # 2. MIME type kontrolü (dosya içeriğinden)
    file_content = file.read(2048)
    file.seek(0)  # Dosyayı başa sar
    
    try:
        mime = magic.Magic(mime=True)
        detected_type = mime.from_buffer(file_content)
    except:
        detected_type = file.content_type
    
    if detected_type not in ALLOWED_FILE_TYPES:
        errors.append("Bu dosya tipi desteklenmiyor. Sadece JPEG, PNG, GIF, PDF, DOC, DOCX kabul edilir.")
        return errors
    
    # 3. Uzantı kontrolü
    file_ext = '.' + file.name.split('.')[-1].lower() if '.' in file.name else ''
    allowed_extensions = ALLOWED_FILE_TYPES.get(detected_type, [])
    
    if file_ext not in allowed_extensions:
        errors.append("Dosya uzantısı içerikle uyuşmuyor")
        return errors
    
    # 4. Path traversal kontrolü
    dangerous_chars = ['..', '/', '\\', '\x00']
    for char in dangerous_chars:
        if char in file.name:
            errors.append("Dosya adı geçersiz karakterler içeriyor")
            return errors
    
    return errors


# =============================================================================
# RATE LIMIT AŞILDIĞINDA
# =============================================================================
def ratelimited_error(request, exception):
    return JsonResponse({
        "success": False,
        "error": "Çok fazla istek gönderdiniz. Lütfen biraz bekleyin."
    }, status=429)


# =============================================================================
# 1. GET /api/v1/conversations
# Kullanıcının sohbet listesi
# =============================================================================
@csrf_exempt
@login_required
@ratelimit(key='user', rate='60/m', method='GET', block=True)
def list_conversations(request):
    if request.method != "GET":
        return JsonResponse({"error": "Sadece GET kabul edilir"}, status=405)
    
    conversations = Conversation.objects.filter(participants=request.user).order_by('-updated_at')
    
    result = []
    for conv in conversations:
        last_message = conv.messages.order_by('-created_at').first()
        unread_count = conv.messages.filter(is_read=False).exclude(sender=request.user).count()
        other_participants = conv.participants.exclude(id=request.user.id)
        
        result.append({
            "id": conv.id,
            "request_id": conv.request.id,
            "conversation_type": conv.conversation_type,
            "participants": [
                {"id": p.id, "username": p.username}
                for p in other_participants
            ],
            "last_message": {
                "content": last_message.content[:100] if last_message and last_message.content else None,
                "sender": last_message.sender.username if last_message and last_message.sender else None,
                "created_at": last_message.created_at.isoformat() if last_message else None,
                "has_file": bool(last_message.file) if last_message else False,
            } if last_message else None,
            "unread_count": unread_count,
            "updated_at": conv.updated_at.isoformat(),
        })
    
    return JsonResponse({
        "success": True,
        "count": len(result),
        "conversations": result
    })


# =============================================================================
# 2-3. GET/POST /api/v1/conversations/{id}/messages
# GET: Mesaj geçmişi | POST: Yeni mesaj gönder
# =============================================================================
@csrf_exempt
@login_required
@ratelimit(key='user', rate='30/m', method='POST', block=True)
@ratelimit(key='user', rate='60/m', method='GET', block=True)
def conversation_messages(request, id):
    # Sohbet var mı?
    try:
        conversation = Conversation.objects.get(id=id)
    except Conversation.DoesNotExist:
        return JsonResponse({"success": False, "error": "Sohbet bulunamadı"}, status=404)
    
    # Yetkisiz erişim kontrolü
    if request.user not in conversation.participants.all():
        print(f"[SECURITY] Unauthorized access attempt: User {request.user.id} tried to access conversation {id}")
        return JsonResponse({"success": False, "error": "Bu sohbete erişiminiz yok"}, status=403)
    
    # =========================================================================
    # GET: Mesajları listele
    # =========================================================================
    if request.method == "GET":
        messages = conversation.messages.order_by('-created_at')
        
        page = request.GET.get('page', 1)
        per_page = min(int(request.GET.get('per_page', 20)), 50)  # Max 50
        
        paginator = Paginator(messages, per_page)
        page_obj = paginator.get_page(page)
        
        result = []
        for msg in page_obj:
            result.append({
                "id": msg.id,
                "sender": {
                    "id": msg.sender.id if msg.sender else None,
                    "username": msg.sender.username if msg.sender else "Deleted User",
                    "is_me": msg.sender == request.user if msg.sender else False,
                },
                "content": msg.content,
                "file": request.build_absolute_uri(msg.file.url) if msg.file else None,
                "file_name": msg.file.name.split('/')[-1] if msg.file else None,
                "is_read": msg.is_read,
                "created_at": msg.created_at.isoformat(),
            })
        
        # Mesajları okundu olarak işaretle
        conversation.messages.filter(is_read=False).exclude(sender=request.user).update(is_read=True)
        
        return JsonResponse({
            "success": True,
            "messages": result,
            "pagination": {
                "current_page": page_obj.number,
                "total_pages": paginator.num_pages,
                "total_messages": paginator.count,
                "has_next": page_obj.has_next(),
                "has_previous": page_obj.has_previous(),
            }
        })
    
    # =========================================================================
    # POST: Mesaj gönder
    # =========================================================================
    elif request.method == "POST":
        content = None
        file = None
        
        # Dosya var mı kontrol et
        if request.FILES.get('file'):
            file = request.FILES['file']
            content = request.POST.get('content', '')
            
            # Dosya validasyonu
            file_errors = validate_file(file)
            if file_errors:
                return JsonResponse({
                    "success": False,
                    "error": file_errors[0]
                }, status=400)
        else:
            # JSON body
            try:
                data = json.loads(request.body)
            except json.JSONDecodeError:
                return JsonResponse({"success": False, "error": "Geçersiz JSON"}, status=400)
            
            content = data.get('content')
            
            if not content:
                return JsonResponse({"success": False, "error": "content alanı zorunludur"}, status=400)
        
        # Mesaj uzunluğu kontrolü
        if content and len(content) > MAX_MESSAGE_LENGTH:
            return JsonResponse({
                "success": False,
                "error": f"Mesaj {MAX_MESSAGE_LENGTH} karakterden uzun olamaz"
            }, status=400)
        
        # XSS temizliği
        if content:
            content = sanitize_message(content)
        
        # Mesaj oluştur
        message = Message.objects.create(
            conversation=conversation,
            sender=request.user,
            content=content,
            file=file
        )
        
        conversation.save()
        
        return JsonResponse({
            "success": True,
            "message": {
                "id": message.id,
                "content": message.content,
                "file": request.build_absolute_uri(message.file.url) if message.file else None,
                "file_name": message.file.name.split('/')[-1] if message.file else None,
                "created_at": message.created_at.isoformat(),
            }
        }, status=201)
    
    return JsonResponse({"error": "Sadece GET veya POST kabul edilir"}, status=405)


# =============================================================================
# 4. POST /api/v1/conversations/start
# Yeni sohbet başlat
# =============================================================================
@csrf_exempt
@login_required
@ratelimit(key='user', rate='10/m', method='POST', block=True)
def start_conversation(request):
    if request.method != "POST":
        return JsonResponse({"error": "Sadece POST kabul edilir"}, status=405)
    
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "Geçersiz JSON"}, status=400)
    
    request_id = data.get('request_id')
    conversation_type = data.get('type')
    target_user_id = data.get('target_user_id')
    
    # Zorunlu alan kontrolleri
    if not request_id:
        return JsonResponse({"success": False, "error": "request_id zorunludur"}, status=400)
    if not conversation_type:
        return JsonResponse({"success": False, "error": "type zorunludur"}, status=400)
    if conversation_type not in ['CLIENT_ASSISTANT', 'ASSISTANT_PROVIDER']:
        return JsonResponse({"success": False, "error": "Geçersiz conversation type"}, status=400)
    if not target_user_id:
        return JsonResponse({"success": False, "error": "target_user_id zorunludur"}, status=400)
    
    # Talep var mı?
    try:
        service_request = ServiceRequest.objects.get(id=request_id)
    except ServiceRequest.DoesNotExist:
        return JsonResponse({"success": False, "error": "Talep bulunamadı"}, status=404)
    
    # Hedef kullanıcı var mı?
    try:
        target_user = User.objects.get(id=target_user_id)
    except User.DoesNotExist:
        return JsonResponse({"success": False, "error": "Hedef kullanıcı bulunamadı"}, status=404)
    
    # Kendisiyle sohbet açamaz
    if target_user == request.user:
        return JsonResponse({"success": False, "error": "Kendinizle sohbet başlatamazsınız"}, status=400)
    
    # Aynı sohbet var mı?
    existing = Conversation.objects.filter(
        request=service_request,
        conversation_type=conversation_type,
        participants=request.user
    ).filter(participants=target_user).first()
    
    if existing:
        return JsonResponse({
            "success": True,
            "message": "Mevcut sohbet bulundu",
            "conversation": {
                "id": existing.id,
                "request_id": existing.request.id,
                "conversation_type": existing.conversation_type,
            }
        })
    
    # Yeni sohbet oluştur
    conversation = Conversation.objects.create(
        request=service_request,
        conversation_type=conversation_type
    )
    conversation.participants.add(request.user, target_user)
    
    return JsonResponse({
        "success": True,
        "message": "Sohbet başlatıldı",
        "conversation": {
            "id": conversation.id,
            "request_id": conversation.request.id,
            "conversation_type": conversation.conversation_type,
        }
    }, status=201)