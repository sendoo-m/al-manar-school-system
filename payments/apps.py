# في payments/apps.py - إزالة الاستعلامات من ready()

from django.apps import AppConfig

class PaymentsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'payments'
    verbose_name = 'المدفوعات والأقساط'
    
    def ready(self):
        # إزالة أي استعلامات قاعدة بيانات من هنا
        # import payments.signals  # إذا كان موجود
        pass
