import json
from django.http import JsonResponse
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import update_session_auth_hash

class SimplePasswordResetView(LoginRequiredMixin, View):

    def post(self, request):
        try:
            data = json.loads(request.body)
            new_password = data.get("new_password")

            if not new_password:
                return JsonResponse({"error": "Password required"}, status=400)

            user = request.user
            user.set_password(new_password)
            user.save()

            update_session_auth_hash(request, user)  # Keep user logged in

            return JsonResponse({"success": True})

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
