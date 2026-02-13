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

    # Money (NO FLOATS)
    coins = models.IntegerField(default=0)

    match_share = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    casino_share = models.DecimalField(max_digits=5, decimal_places=2, default=0)

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
