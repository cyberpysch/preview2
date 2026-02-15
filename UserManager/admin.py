from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Account , AuditLog

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
@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "model_name",
        "object_id",
        "action",
        "field_name",
        "changed_by",
        "affected_account",
    )

    list_filter = (
        "model_name",
        "action",
        "changed_by",
        "created_at",
    )

    search_fields = (
        "object_id",
        "field_name",
        "old_value",
        "new_value",
        "changed_by__username",
        "affected_account__user__username",
    )

    ordering = ("-created_at",)

    readonly_fields = [field.name for field in AuditLog._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
