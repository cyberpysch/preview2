from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import F
import json

from ..models import Account, CoinTransaction


@login_required
@require_POST
def deposit_coins(request):

    try:
        data = json.loads(request.body)
        username = data.get("username")
        amount = int(data.get("amount"))

        if amount <= 0:
            return JsonResponse({"success": False, "message": "Invalid amount"}, status=400)

    except:
        return JsonResponse({"success": False, "message": "Invalid request"}, status=400)

    try:
        initiator_account = request.user.account
        target_account = Account.objects.select_related("parent", "user").get(user__username=username)

    except Account.DoesNotExist:
        return JsonResponse({"success": False, "message": "Target not found"}, status=404)

    # -------------------------------
    # 🔒 STEP 1: Validate Tree Ownership
    # -------------------------------

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

    # -------------------------------
    # 🔁 STEP 2: Determine Sender
    # -------------------------------

    sender = target_account.parent

    if sender is None:
        return JsonResponse(
            {"success": False, "message": "Cannot deposit to root account"},
            status=400
        )

    # -------------------------------
    # 💰 STEP 3: Atomic Transaction
    # -------------------------------

    with transaction.atomic():

        # Lock rows
        sender = Account.objects.select_for_update().get(pk=sender.pk)
        receiver = Account.objects.select_for_update().get(pk=target_account.pk)

        if sender.coins < amount:
            return JsonResponse(
                {"success": False, "message": f"Insufficient balance in {sender.user.username}'s account"},
                status=400
            )

        # Deduct from immediate parent
        sender.coins = F("coins") - amount
        sender.save()

        # Add to receiver
        receiver.coins = F("coins") + amount
        receiver.save()

        # Log transaction
        CoinTransaction.objects.create(
            sender=sender,
            receiver=receiver,
            amount=amount
        )

    return JsonResponse({"success": True, "message": "Deposit successful"})
