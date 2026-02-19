from rest_framework.permissions import IsAuthenticated
from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db import transaction
from django.contrib.auth import get_user_model
from ..serializers import UserStatusSerializer


User = get_user_model()

def update_descendants_status(account, enabled):
    for child in account.children.select_related("user").all():
        child.is_enabled_by_parent = enabled
        child.save(update_fields=["is_enabled_by_parent"])
        update_descendants_status(child, enabled)

class UserStatusAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        serializer = UserStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            user = User.objects.get(username=serializer.validated_data["username"])
            account = user.account
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=404)

        new_status = serializer.validated_data["is_active"]
        if new_status:  # trying to activate
            if account.parent and not account.parent.is_effectively_active:
                return Response(
                    {"error": "Cannot activate user while parent is inactive"},
                    status=400
                )
        # Update personal status
        user.is_active = new_status
        user.save(update_fields=["is_active"])

        # Update hierarchy effect
        update_descendants_status(account, new_status)

        action = "activated" if new_status else "deactivated"

        return Response({"message": f"User {action} successfully"})

def statement_partial(request):
    return render(request, "usermanagement/partials/statement_partial.html")
