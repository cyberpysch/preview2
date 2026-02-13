from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import F
import json

from ..models import Account, CoinTransaction


@login_required
@require_POST
def withdraw_coins(request):

    try:
        data = json.loads(request.body)
        username = data.get("username")
        amount = int(data.get("amount"))

        if amount <= 0:
            return JsonResponse(
                {"success": False, "message": "Invalid amount"},
                status=400
            )

    except Exception:
        return JsonResponse(
            {"success": False, "message": "Invalid request"},
            status=400
        )

    try:
        initiator_account = request.user.account
        target_account = Account.objects.select_related("parent", "user").get(
            user__username=username
        )

    except Account.DoesNotExist:
        return JsonResponse(
            {"success": False, "message": "Target not found"},
            status=404
        )

    # ---------------------------------------
    # 🔒 STEP 1 — Validate Tree Ownership
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
            {"success": False, "message": "Target not in your hierarchy"},
            status=403
        )

    # ---------------------------------------
    # 🔁 STEP 2 — Identify Financial Parties
    # ---------------------------------------

    sender = target_account
    receiver = target_account.parent  # Immediate parent

    # Root handling intentionally not blocked here (as per your design)

    # ---------------------------------------
    # 💰 STEP 3 — Atomic Withdraw
    # ---------------------------------------

    with transaction.atomic():

        # Lock rows to prevent race condition
        sender = Account.objects.select_for_update().get(pk=sender.pk)
        receiver = Account.objects.select_for_update().get(pk=receiver.pk)

        if sender.coins < amount:
            return JsonResponse(
                {"success": False, "message": "Insufficient balance"},
                status=400
            )

        # Deduct from child
        sender.coins = F("coins") - amount
        sender.save()

        # Add to immediate parent
        receiver.coins = F("coins") + amount
        receiver.save()

        # Log transaction
        CoinTransaction.objects.create(
            sender=sender,
            receiver=receiver,
            amount=amount
        )

    return JsonResponse(
        {"success": True, "message": "Withdraw successful"}
    )
