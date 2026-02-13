from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.core.paginator import Paginator
from ..models import Account, CoinTransaction


@login_required
def account_statement(request):

    username = request.GET.get("username")
    page_number = request.GET.get("page", 1)

    if not username:
        return JsonResponse(
            {"success": False, "message": "Username is required"},
            status=400
        )

    try:
        page_number = int(page_number)
    except ValueError:
        page_number = 1

    try:
        initiator_account = request.user.account
        target_account = Account.objects.select_related("parent", "user").get(
            user__username=username
        )
    except Account.DoesNotExist:
        return JsonResponse(
            {"success": False, "message": "Account not found"},
            status=404
        )

    # ---------------------------------------
    #  STEP 1 — Validate Subtree Ownership
    # ---------------------------------------

    current = target_account
    is_allowed = False

    while current is not None:
        if current == initiator_account:
            is_allowed = True
            break
        current = current.parent

    if not is_allowed:
        return JsonResponse(
            {"success": False, "message": "Not allowed to view this statement"},
            status=403
        )

    # ---------------------------------------
    #  STEP 2 — Fetch All Related Transactions (ASC for balance calc)
    # ---------------------------------------

    transactions = CoinTransaction.objects.filter(
        Q(sender=target_account) | Q(receiver=target_account)
    ).order_by("created_at")

    # ---------------------------------------
    #  STEP 3 — Build Running Ledger
    # ---------------------------------------

    balance = 0
    statement_rows = []

    for txn in transactions:

        prev_balance = balance

        if txn.receiver == target_account:
            balance += txn.amount
            cr = txn.amount
            dr = 0
        else:
            balance -= txn.amount
            cr = 0
            dr = txn.amount

        statement_rows.append({
            "datetime": txn.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "description": f"{txn.sender.user.username} transferred {txn.amount} coins to {txn.receiver.user.username}",
            "prev_balance": prev_balance,
            "cr": cr,
            "dr": dr,
            "comm_plus": 0,
            "comm_minus": 0,
            "current_balance": balance,
        })

    # ---------------------------------------
    #  STEP 4 — Reverse for Newest First
    # ---------------------------------------

    statement_rows.reverse()

    # ---------------------------------------
    #  STEP 5 — Pagination (25 per page)
    # ---------------------------------------

    paginator = Paginator(statement_rows, 25)
    page_obj = paginator.get_page(page_number)

    return JsonResponse({
        "success": True,
        "page": page_obj.number,
        "total_pages": paginator.num_pages,
        "total_records": paginator.count,
        "results": list(page_obj.object_list),
    })
