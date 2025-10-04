from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('home.urls')),  # الصفحة الرئيسية
    path('students/', include('students.urls')),  # تطبيق الطلاب
    path('report/', include('report.urls')),  # تطبيق التقارير
    path('account/', include('account.urls')),  # تطبيق الحسابات
    path('settings/', include('school_settings.urls')),  # إعدادات المدرسة
    path('payments/', include('payments.urls', namespace='payments')),  # تطبيق المدفوعات
    path('inventory/', include('books_inventory.urls')),  # إضافة تطبيق المخزن
    path('treasury/', include('treasury_management.urls')),  # إضافة تطبيق إدارة الخزينة
    path('logout/', auth_views.LogoutView.as_view(template_name='account/logout.html'), name='logout'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)