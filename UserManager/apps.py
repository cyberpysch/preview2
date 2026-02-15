from django.apps import AppConfig

class UsermanagerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'UserManager'

    def ready(self):
        import UserManager.signals

def ready(self):
    import UserManager.signals
