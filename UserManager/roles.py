from django.db import models

class Role(models.TextChoices):
    SUPERADMIN = "Superadmin"
    SUBADMIN = "Subadmin"
    ADMIN = "Admin"
    MINIADMIN = "Miniadmin"
    MASTER = "Master"
    SUPER = "Super"
    AGENT = "Agent"
    CLIENT = "Client"

ROLE_LEVEL = {
    "Superadmin": 100,
    "Subadmin": 90,
    "Admin": 80,
    "Miniadmin": 70,
    "Master": 60,
    "Super": 50,
    "Agent": 40,
    "Client": 30,
}

NUMERIC_FIELDS = [
    "match_share",
    "casino_share",
    "match_commission",
    "session_commission",
    "casino_commission",
]