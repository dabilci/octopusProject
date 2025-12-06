# AssistAll Backend API Spesifikasyonları

## 1. Kimlik Doğrulama & Kullanıcılar (Auth & Users)

Projede 4 farklı rol bulunmaktadır: **Client (Bireysel/Kurumsal)**, **Provider (Hizmet Veren)**, **Assistant**, **Admin**.

| Method | Endpoint                         | Açıklama                                                      |
| :----- | :------------------------------- | :------------------------------------------------------------ |
| `POST` | `/api/v1/auth/register/client`   | Müşteri kaydı. (Bireysel veya Kurumsal seçimli)               |
| `POST` | `/api/v1/auth/register/provider` | Hizmet veren kaydı. (Vergi no, belge yükleme alanları içerir) |
| `POST` | `/api/v1/auth/login`             | Tüm roller için giriş (JWT Token döner).                      |
| `POST` | `/api/v1/auth/refresh-token`     | Token yenileme.                                               |
| `POST` | `/api/v1/auth/verify-email`      | E-posta doğrulama kodu kontrolü.                              |***
| `GET`  | `/api/v1/users/me`               | Giriş yapmış kullanıcının profil detayları.                   |
| `PUT`  | `/api/v1/users/me`               | Profil güncelleme (Avatar, Telefon vb.).                      |
| `PUT`  | `/api/v1/users/me/fcm-token`     | Bildirimler için cihaz token'ı kaydetme.                      |

---

## 2. Talep Yönetimi (Service Requests - Workflow Core)

Müşterinin talep oluşturduğu ve asistanın süreci yönettiği ana modüldür. Durum makinesi (State Machine) burada çalışır.

**Statüler:** `DRAFT`, `PENDING_ASSISTANT`, `IN_REVIEW`, `OFFER_READY`, `PAYMENT_LOCKED`, `IN_PROGRESS`, `COMPLETED`, `CANCELLED`.

| Method | Endpoint                         | Açıklama                                                   |
| :----- | :------------------------------- | :--------------------------------------------------------- |
| `POST` | `/api/v1/requests`               | Yeni talep oluştur (Kategori, Açıklama, Dosya, Bütçe).     |
| `GET`  | `/api/v1/requests`               | Müşterinin kendi taleplerini listelemesi (Filtre: Status). |
| `GET`  | `/api/v1/requests/{id}`          | Talep detayı ve tarihçesi.                                 |
| `POST` | `/api/v1/requests/{id}/cancel`   | Talebi iptal et.                                           |
| `POST` | `/api/v1/requests/{id}/feedback` | Tamamlanan işe puan ve yorum ver.                          |

---

## 3. Asistan Paneli (Assistant Endpoints)

Sadece `ROLE_ASSISTANT` ve `ROLE_ADMIN` erişebilir.

| Method | Endpoint                                 | Açıklama                                                  |
| :----- | :--------------------------------------- | :-------------------------------------------------------- |
| `GET`  | `/api/v1/assistant/tasks`                | Havuzdaki atanmamış veya asistana atanmış işleri listele. |
| `POST` | `/api/v1/assistant/requests/{id}/assign` | İşi kendine veya başkasına ata.                           |
| `GET` | `/api/v1/assistant/requests/{id}/assign` | Tüm asistanları listele
| `PUT`  | `/api/v1/assistant/requests/{id}/status` | Talep durumunu güncelle (Örn: In Review).                 |
| `GET`  | `/api/v1/assistant/providers/search`     | Talebe uygun hizmet verenleri ara/filtrele.               |
| `POST` | `/api/v1/assistant/requests/{id}/notes`  | Talebe sadece asistanların göreceği iç not ekle.          |

---

## 4. Teklif Yönetimi (Offers)

Asistanın hizmet verenlerden toplayıp müşteriye sunduğu teklifler.

| Method | Endpoint                              | Açıklama                                                                     |
| :----- | :------------------------------------ | :--------------------------------------------------------------------------- |
| `POST` | `/api/v1/offers`                      | Asistan: Bir talep için yeni teklif oluşturur (Fiyat, Provider ID).          |
| `GET`  | `/api/v1/requests/{requestId}/offers` | Müşteri: Talebe gelen teklifleri görür.                                      |
| `POST` | `/api/v1/offers/{id}/accept`          | Müşteri: Teklifi kabul eder -> **Ödeme ekranına yönlendirir / Bloke koyar.** |
| `POST` | `/api/v1/offers/{id}/reject`          | Müşteri: Teklifi reddeder.                                                   |

---

## 5. Cüzdan & Ödeme (Wallet & Escrow)

"Tutarın bloke edilmesi" ve iş bitiminde serbest bırakılması süreçleri.

| Method | Endpoint                            | Açıklama                                                       |
| :----- | :---------------------------------- | :------------------------------------------------------------- |
| `GET`  | `/api/v1/wallet/balance`            | Kullanıcı bakiyesi.                                            |
| `GET`  | `/api/v1/wallet/transactions`       | İşlem geçmişi.                                                 |
| `POST` | `/api/v1/payment/initialize`        | Ödeme başlat (Kredi Kartı / 3D Secure).                        |
| `POST` | `/api/v1/payment/webhook`           | Ödeme sağlayıcıdan (Stripe/Iyzico) gelen callback.             |
| `POST` | `/api/v1/payment/{offerId}/release` | **Admin/Asistan:** İş tamamlanınca parayı Hizmet Verene aktar. |

---

## 6. Mesajlaşma (Chat)

Müşteri-Asistan ve Asistan-Hizmet Veren iletişimi.

| Method | Endpoint                              | Açıklama                                                          |
| :----- | :------------------------------------ | :---------------------------------------------------------------- |
| `GET`  | `/api/v1/conversations`               | Kullanıcının sohbet listesi.                                      |
| `GET`  | `/api/v1/conversations/{id}/messages` | Mesaj geçmişi (Pagination ile).                                   |
| `POST` | `/api/v1/conversations/{id}/messages` | Yeni mesaj gönder (Text veya Dosya).                              |
| `POST` | `/api/v1/conversations/start`         | Yeni bir konu/sohbet başlat (Genelde talep üzerinden tetiklenir). |

---

## 7. Admin Paneli

Üst düzey yönetim ve denetim.

| Method | Endpoint                               | Açıklama                                       |
| :----- | :------------------------------------- | :--------------------------------------------- |
| `GET`  | `/api/v1/admin/providers/pending`      | Onay bekleyen hizmet veren başvuruları.        |
| `POST` | `/api/v1/admin/providers/{id}/approve` | Hizmet vereni onayla.                          |
| `GET`  | `/api/v1/admin/audit-logs`             | Sistemdeki tüm kritik işlemlerin (Log) dökümü. |
| `GET`  | `/api/v1/admin/reports/financial`      | Gelir, Komisyon ve Hakediş raporları.          |
| `GET`  | `/api/v1/admin/assistants/performance` | Asistan performans metrikleri.                 |

---
