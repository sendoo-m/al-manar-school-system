# LYS_schoolapp/middleware.py
from django.utils import translation
import time
from django.conf import settings
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.urls import reverse, NoReverseMatch



class AdminEnglishSiteArabicMiddleware:
    """
    يجعل لوحة Django Admin باللغة الإنجليزية
    وباقي الموقع باللغة العربية.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith('/admin/'):
            language = 'en'
        else:
            language = 'ar'

        translation.activate(language)
        request.LANGUAGE_CODE = language

        response = self.get_response(request)

        response.setdefault('Content-Language', language)
        translation.deactivate()

        return response
    

class SessionIdleTimeoutMiddleware:
    """
    Middleware يراقب خمول المستخدم ويسجّل خروجه تلقائياً
    بعد انتهاء مدة SESSION_IDLE_TIMEOUT
    """

    EXEMPT_URLS = {
        'account:login',
        'account:signup',
        'account:heartbeat',
    }

    def __init__(self, get_response):
        self.get_response = get_response
        self.idle_timeout = getattr(settings, 'SESSION_IDLE_TIMEOUT', 60 * 30)

    def __call__(self, request):
        user = getattr(request, 'user', None)
        if user is None or not user.is_authenticated:
            return self.get_response(request)

        if self._is_exempt(request):
            return self.get_response(request)

        last_activity = request.session.get('last_activity')

        if last_activity:
            elapsed = time.time() - last_activity
            if elapsed > self.idle_timeout:
                logout(request)
                try:
                    login_url = reverse('account:login')
                except NoReverseMatch:
                    login_url = '/account/login/'
                return redirect(f'{login_url}?next={request.path}&reason=idle')

        request.session['last_activity'] = time.time()
        return self.get_response(request)

    def _is_exempt(self, request):
        for url_name in self.EXEMPT_URLS:
            try:
                if request.path == reverse(url_name):
                    return True
            except NoReverseMatch:
                continue
        return False  
