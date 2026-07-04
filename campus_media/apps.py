from django.apps import AppConfig


class CampusMediaConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "campus_media"

    def ready(self):
        import campus_media.signals
