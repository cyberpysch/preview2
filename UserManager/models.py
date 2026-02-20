from django.contrib.auth.models import AbstractUser
from django.conf import settings
from .manager import UserManager
from django.db.models import Q
from django.db import models
from .roles import Role


class User(AbstractUser):
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.CLIENT,
        db_index=True
    )
    objects = UserManager()

    def __str__(self):
        return self.username

class Account(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="account"
    )

    parent = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="children"
    )

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        db_index=True
    )
    reference = models.CharField(max_length=150, null=True, default="")
    # Money (NO FLOATS)
    coins = models.IntegerField(default=0)

    match_share = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    casino_share = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    refrence_match_share = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    COMMISSION_TYPE = [
        ("BET_BY_BET", "Bet by Bet"),
        ("NO_COMMISSION", "No Commission"),
    ]

    commission_type = models.CharField(
        max_length=20,
        choices=COMMISSION_TYPE
    )

    match_commission = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    session_commission = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    casino_commission = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    share_type = models.CharField(
        max_length=20,
        choices=[
            ("CHANGE", "CHANGE"),
            ("FIXED", "FIXED"),
        ],
        default="FIXED"
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    location = models.CharField(max_length=30, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    is_enabled_by_parent = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(match_share__gte=0, match_share__lte=100),
                name="match_share_0_100"
            ),
            models.CheckConstraint(
                condition=Q(casino_share__gte=0, casino_share__lte=100),
                name="casino_share_0_100"
            ),
        ]

    def __str__(self):
        return f"{self.user.username} ({self.role})"
    
    @property
    def is_effectively_active(self):
        return self.user.is_active and self.is_enabled_by_parent

class CoinTransaction(models.Model):
    sender = models.ForeignKey(
        Account,
        related_name="sent_transactions",
        on_delete=models.PROTECT
    )
    receiver = models.ForeignKey(
        Account,
        related_name="received_transactions",
        on_delete=models.PROTECT
    )
    amount = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.sender} → {self.receiver} : {self.amount}"

class AuditLog(models.Model):
    model_name = models.CharField(max_length=100)
    object_id = models.CharField(max_length=100)

    affected_account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        related_name="audit_logs",
        null=True,
        blank=True
    )

    action = models.CharField(max_length=20)  # CREATE / UPDATE / DELETE

    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="performed_actions"
    )

    field_name = models.CharField(max_length=100)
    old_value = models.TextField(null=True, blank=True)
    new_value = models.TextField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
    def save(self, *args, **kwargs):
        if self.pk:
            raise Exception("Audit logs cannot be modified.")
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        raise Exception("Audit logs cannot be deleted.")
