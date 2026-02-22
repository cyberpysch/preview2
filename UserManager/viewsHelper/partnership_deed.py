from decimal import Decimal
from ..roles import NUMERIC_FIELDS , ROLE_LEVEL
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from ..models import Account
from django.shortcuts import get_object_or_404

class FullPartnershipDeedAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, username):
        try:
            target = Account.objects.select_related("parent", "user").get(
                user__username=username
            )
        except Account.DoesNotExist:
            return Response({"error": "User not found"}, status=404)

        logged_account = request.user.account

        # 🔐 Role hierarchy check
        if ROLE_LEVEL[logged_account.role] < ROLE_LEVEL[target.role]:
            return Response({"error": "Permission denied"}, status=403)

        # 🔁 Build vertical chain
        chain = []
        current = target

        while current:
            chain.append(current)
            current = current.parent

        chain.reverse()  # Superadmin → Target

        if ROLE_LEVEL[logged_account.role] < 100:
            max_role_level_to_show = ROLE_LEVEL[logged_account.role] #+ 10
        else:
            max_role_level_to_show = ROLE_LEVEL[logged_account.role]

        filtered_chain = [
        acc for acc in chain
        if ROLE_LEVEL[acc.role] <= max_role_level_to_show
    ]

        response_data = []

        for i in range(len(filtered_chain)):
            account = filtered_chain[i]

            level_data = {
                "username": account.user.username,
                "role": account.role,
            }

            for field in NUMERIC_FIELDS:
                current_value = getattr(account, field) or 0
                is_client_share_field = (
                    target.role == "Client" and
                    field in ["match_share", "casino_share"]
                )
                effective_length = len(filtered_chain)
                if is_client_share_field:
                    effective_length = len(filtered_chain) - 1
                if is_client_share_field and i == len(filtered_chain) - 1:
                    continue
                # Last level keeps full value
                if i == effective_length - 1:
                    level_data[field] = float(current_value)
                else:
                    child_value = getattr(filtered_chain[i + 1], field) or 0
                    if field in ["match_share", "casino_share"]:
                        if i == len(filtered_chain) - 1:
                            level_data[field] = float(current_value)
                        else:
                            child_value = getattr(filtered_chain[i + 1], field) or 0
                            level_data[field] = float(current_value - child_value)
                    else:
                        level_data[field] = float(current_value)
                        #level_data[field] = float(current_value - child_value)

            response_data.append(level_data)

        return Response(response_data)
def compute_partnership_deed(account):
    """
    Compute partnership deed for an account, including
    client-agent share merging logic.
    Returns list of dicts similar to API response.
    """

    from decimal import Decimal

    # If stored deed exists, use it first
    if account.partnership_deed:
        deed_data = account.partnership_deed
        deed_map = {d["username"]: d.copy() for d in deed_data}

        # Special case: if account is client, add client share to agent share
        if account.role.lower() == "client" and account.parent:
            agent_username = account.parent.user.username
            client_username = account.user.username

            if agent_username in deed_map and client_username in deed_map:
                deed_map[agent_username]["match_share"] += deed_map[client_username]["match_share"]
                deed_map[agent_username]["casino_share"] += deed_map[client_username]["casino_share"]
                deed_map[client_username]["match_share"] = 0
                deed_map[client_username]["casino_share"] = 0

        return list(deed_map.values())

    # If no stored deed, compute static chain shares
    chain = []
    current = account
    while current:
        chain.append(current)
        current = current.parent
    chain.reverse()

    response_data = []
    for i, acc in enumerate(chain):
        match_share = acc.match_share
        casino_share = acc.casino_share
        if i < len(chain) - 1:
            match_share -= chain[i + 1].match_share
            casino_share -= chain[i + 1].casino_share

        response_data.append({
            "username": acc.user.username,
            "role": acc.role,
            "match_share": float(match_share),
            "casino_share": float(casino_share),
            "match_commission": float(acc.match_commission or 0),
            "session_commission": float(acc.session_commission or 0),
            "casino_commission": float(acc.casino_commission or 0),
            "commission_type": acc.commission_type,
            "share_type": acc.share_type,
        })

    # Client-agent logic for static data as well:
    usernames = [d["username"] for d in response_data]
    for d in response_data:
        if d["role"].lower() == "client" and account.parent:
            agent_index = None
            client_index = None
            try:
                agent_index = usernames.index(account.parent.user.username)
                client_index = usernames.index(account.user.username)
            except ValueError:
                pass

            if agent_index is not None and client_index is not None:
                response_data[agent_index]["match_share"] += response_data[client_index]["match_share"]
                response_data[agent_index]["casino_share"] += response_data[client_index]["casino_share"]
                response_data[client_index]["match_share"] = 0
                response_data[client_index]["casino_share"] = 0
                break  # Only once

    return response_data

class IsolatedBranchDeedAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, username):
        target = get_object_or_404(Account.objects.select_related("parent", "user"), user__username=username)
        logged_account = request.user.account

        if ROLE_LEVEL[logged_account.role] < ROLE_LEVEL[target.role]:
            return Response({"error": "Permission denied"}, status=403)

        response_data = compute_partnership_deed(target)
        print(response_data)
        return Response(response_data)