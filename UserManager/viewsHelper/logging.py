# views.py

from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from django.http import JsonResponse
from ..models import Account, AuditLog
from ..utils.utils import get_all_children

def account_operations(request, username):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Unauthorized"}, status=403)

    selected_account = get_object_or_404(
        Account,
        user__username=username
    )

    logged_in_account = request.user.account

    # Permission check
    allowed_accounts = [logged_in_account] + get_all_children(logged_in_account)

    if selected_account not in allowed_accounts:
        return JsonResponse({"error": "Permission denied"}, status=403)

    logs = AuditLog.objects.filter(
        affected_account=selected_account
    ).select_related(
        "changed_by",
        "affected_account"
    ).order_by("-created_at")

    paginator = Paginator(logs, 20)  # 20 logs per page
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        "usermanagement/partials/account_operations.html",
        {
            "page_obj": page_obj,
            "selected_account": selected_account,
        }
    )
