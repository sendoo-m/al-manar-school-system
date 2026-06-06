from django.core.cache import cache
import logging

from .models import (
    SystemSettings,
    NotificationSettings,
    ReportSettings,
    SecuritySettings,
)

logger = logging.getLogger(__name__)

SYSTEM_SETTINGS_CACHE_KEY = 'school_settings:system_settings'
NOTIFICATION_SETTINGS_CACHE_KEY = 'school_settings:notification_settings'
REPORT_SETTINGS_CACHE_KEY = 'school_settings:report_settings'
SECURITY_SETTINGS_CACHE_KEY = 'school_settings:security_settings'

CACHE_TIMEOUT = 3600


def get_system_settings():
    """الحصول على إعدادات النظام مع التخزين المؤقت"""
    settings_obj = cache.get(SYSTEM_SETTINGS_CACHE_KEY)

    if settings_obj is None:
        try:
            settings_obj = SystemSettings.get_current_settings()
            cache.set(SYSTEM_SETTINGS_CACHE_KEY, settings_obj, CACHE_TIMEOUT)
        except Exception as e:
            logger.error(f"خطأ في تحميل إعدادات النظام: {e}")
            settings_obj = None

    return settings_obj


def get_notification_settings():
    """الحصول على إعدادات التنبيهات مع التخزين المؤقت"""
    settings_obj = cache.get(NOTIFICATION_SETTINGS_CACHE_KEY)

    if settings_obj is None:
        try:
            settings_obj = NotificationSettings.get_current_settings()
            cache.set(NOTIFICATION_SETTINGS_CACHE_KEY, settings_obj, CACHE_TIMEOUT)
        except Exception as e:
            logger.error(f"خطأ في تحميل إعدادات التنبيهات: {e}")
            settings_obj = None

    return settings_obj


def get_report_settings():
    """الحصول على إعدادات التقارير مع التخزين المؤقت"""
    settings_obj = cache.get(REPORT_SETTINGS_CACHE_KEY)

    if settings_obj is None:
        try:
            settings_obj = ReportSettings.get_current_settings()
            cache.set(REPORT_SETTINGS_CACHE_KEY, settings_obj, CACHE_TIMEOUT)
        except Exception as e:
            logger.error(f"خطأ في تحميل إعدادات التقارير: {e}")
            settings_obj = None

    return settings_obj


def get_security_settings():
    """الحصول على إعدادات الأمان مع التخزين المؤقت"""
    settings_obj = cache.get(SECURITY_SETTINGS_CACHE_KEY)

    if settings_obj is None:
        try:
            settings_obj = SecuritySettings.get_current_settings()
            cache.set(SECURITY_SETTINGS_CACHE_KEY, settings_obj, CACHE_TIMEOUT)
        except Exception as e:
            logger.error(f"خطأ في تحميل إعدادات الأمان: {e}")
            settings_obj = None

    return settings_obj


def clear_settings_cache():
    """مسح كاش إعدادات النظام"""
    cache.delete_many([
        SYSTEM_SETTINGS_CACHE_KEY,
        NOTIFICATION_SETTINGS_CACHE_KEY,
        REPORT_SETTINGS_CACHE_KEY,
        SECURITY_SETTINGS_CACHE_KEY,
    ])
