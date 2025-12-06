from django.http import JsonResponse
from django.urls import reverse

LOGIN_PATHS = {
    "/api/v1/auth/login",
    "/accounts/login",
    "/accounts/login/",
}

class SessionExpiredMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # 1) login_required redirect’i (302 → login URL)
        location = response.get("Location", "")
        if response.status_code == 302 and any(loc in location for loc in LOGIN_PATHS):
            return JsonResponse({
                "success": False,
                "error": "session_expired",
                "message": "Oturum süreniz dolmuştur. Lütfen tekrar giriş yapınız."
            }, status=401)

        # 2) 401/403 ama login endpoint’i DEĞİL
        if response.status_code in [401, 403] \
        and not request.user.is_authenticated \
        and not any(request.path.startswith(p) for p in LOGIN_PATHS):
            return JsonResponse({
                "success": False,
                "error": "session_expired",
                "message": "Oturum süreniz dolmuştur. Lütfen tekrar giriş yapınız."
            }, status=401)

        return response