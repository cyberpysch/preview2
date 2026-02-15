from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from rest_framework.authtoken.models import Token

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_auth_token(sender, instance=None, created=False, **kwargs):
    if created:
        Token.objects.create(user=instance)


from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.forms.models import model_to_dict
from .models import AuditLog, Account
from .middlerware import get_current_user
from django.apps import apps


EXCLUDED_MODELS = ["AuditLog"]  # prevent recursion


@receiver(pre_save)
def capture_old_values(sender, instance, **kwargs):
    if sender.__name__ in EXCLUDED_MODELS:
        return

    if instance.pk:
        try:
            instance._old_instance = sender.objects.get(pk=instance.pk)
        except sender.DoesNotExist:
            instance._old_instance = None


@receiver(post_save)
def log_model_changes(sender, instance, created, **kwargs):
    if sender.__name__ in EXCLUDED_MODELS:
        return

    user = get_current_user()
    if not user or not user.is_authenticated:
        return

    action = "CREATE" if created else "UPDATE"

    old_instance = getattr(instance, "_old_instance", None)

    for field in instance._meta.fields:
        field_name = field.name

        old_value = None
        if old_instance:
            old_value = getattr(old_instance, field_name)

        new_value = getattr(instance, field_name)

        if created or old_value != new_value:
            affected_account = None

            if isinstance(instance, Account):
                affected_account = instance
            elif hasattr(instance, "account"):
                affected_account = instance.account

            AuditLog.objects.create(
                model_name=sender.__name__,
                object_id=str(instance.pk),
                affected_account=affected_account,
                action=action,
                changed_by=user,
                field_name=field_name,
                old_value=str(old_value) if old_value else "",
                new_value=str(new_value) if new_value else "",
            )
