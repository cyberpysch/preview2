from decimal import Decimal
from ..roles import NUMERIC_FIELDS , ROLE_LEVEL
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from ..models import Account


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
            max_role_level_to_show = ROLE_LEVEL[logged_account.role] + 10
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

                # Last level keeps full value
                if i == len(filtered_chain) - 1:
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