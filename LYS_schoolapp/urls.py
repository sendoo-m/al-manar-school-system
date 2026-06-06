"""
URL configuration for LYS_schoolapp project.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),

    # الصفحة الرئيسية
    path('', include('home.urls')),

    # التطبيقات الأساسية
    path('students/', include('students.urls')),
    path('report/', include('report.urls')),
    path('account/', include('account.urls')),
    path('settings/', include('school_settings.urls')),
    path('payments/', include('payments.urls', namespace='payments')),

    # المخزن والخزينة
    path('inventory/', include('books_inventory.urls')),
    path('treasury/', include('treasury_management.urls')),

    # توحيد جميع مسارات تسجيل الخروج
    path('logout/', RedirectView.as_view(url='/home-logout/'), name='logout'),
    path('accounts/logout/', RedirectView.as_view(url='/home-logout/'), name='accounts_logout'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# # LYS_schoolapp/urls.py - المُحدث
# from django.contrib import admin
# from django.urls import path, include
# from django.conf import settings
# from django.conf.urls.static import static
# from django.views.generic import RedirectView

# urlpatterns = [
#     path('admin/', admin.site.urls),
#     path('', include('home.urls')),  # الصفحة الرئيسية
#     path('students/', include('students.urls')),  # تطبيق الطلاب
#     path('report/', include('report.urls')),  # تطبيق التقارير
#     path('account/', include('account.urls')),  # تطبيق الحسابات
#     path('settings/', include('school_settings.urls')),  # إعدادات المدرسة
#     path('payments/', include('payments.urls', namespace='payments')),  # تطبيق المدفوعات
#     path('inventory/', include('books_inventory.urls')),  # إضافة تطبيق المخزن
#     path('treasury/', include('treasury_management.urls')),  # إضافة تطبيق إدارة الخزينة
    
#     # ✅ توحيد جميع مسارات تسجيل الخروج في home
#     path('logout/', RedirectView.as_view(url='/home-logout/'), name='logout'),
#     path('accounts/logout/', RedirectView.as_view(url='/home-logout/'), name='accounts_logout'),
# ]

# if settings.DEBUG:
#     urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
#     urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
