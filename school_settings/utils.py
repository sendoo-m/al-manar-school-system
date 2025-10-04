from .models import SystemSettings, NotificationSettings, ReportSettings, SecuritySettings
from django.core.cache import cache

# دالة للحصول على إعدادات النظام مع التخزين المؤقت
def get_system_settings():
    settings = cache.get('system_settings')
    if not settings:
        settings = SystemSettings.get_current_settings()
        cache.set('system_settings', settings, 3600)  # حفظ لمدة ساعة
    return settings

def get_notification_settings():
    settings = cache.get('notification_settings')
    if not settings:
        settings = NotificationSettings.get_current_settings()
        cache.set('notification_settings', settings, 3600)
    return settings

def get_report_settings():
    settings = cache.get('report_settings')
    if not settings:
        settings = ReportSettings.get_current_settings()
        cache.set('report_settings', settings, 3600)
    return settings

def get_security_settings():
    settings = cache.get('security_settings')
    if not settings:
        settings = SecuritySettings.get_current_settings()
        cache.set('security_settings', settings, 3600)
    return settings

# دالة لمسح التخزين المؤقت عند تحديث الإعدادات
def clear_settings_cache():
    cache.delete_many([
        'system_settings', 
        'notification_settings', 
        'report_settings', 
        'security_settings'
    ])
