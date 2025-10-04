from django.apps import AppConfig

class SchoolSettingsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'school_settings'
    verbose_name = 'إعدادات المدرسة'
    
    def ready(self):
        import school_settings.signals
