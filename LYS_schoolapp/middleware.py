# LYS_schoolapp/middleware.py
from django.utils import translation


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

# from django.utils import translation


# class AdminEnglishSiteArabicMiddleware:
#     """
#     يجعل لوحة تحكم Django Admin باللغة الإنجليزية
#     وباقي الموقع باللغة العربية.
#     """

#     def __init__(self, get_response):
#         self.get_response = get_response

#     def __call__(self, request):
#         if request.path.startswith('/admin/'):
#             translation.activate('en')
#             request.LANGUAGE_CODE = 'en'
#         else:
#             translation.activate('ar')
#             request.LANGUAGE_CODE = 'ar'

#         response = self.get_response(request)
#         translation.deactivate()
#         return response