from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Account

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    fieldsets = BaseUserAdmin.fieldsets + (
        ("Role", {"fields": ("role",)}),
    )
    list_display = ("username", "email", "role", "is_staff")

@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = (
        "user", "role", "parent", "coins",
        "share_type", "match_share", "casino_share",
        "commission_type","match_commission",
        "session_commission","casino_commission"
        )
    search_fields = ("user__username",)