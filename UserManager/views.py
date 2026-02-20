from django.shortcuts import render ,redirect
from django.http import HttpResponse
from django.contrib.auth import authenticate, login
from UserManager.models import User
from rest_framework import status
from UserManager.serializers import *
from rest_framework.permissions import IsAuthenticated ,AllowAny , IsAdminUser
from rest_framework.authtoken.models import Token
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.renderers import TemplateHTMLRenderer
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib.auth import get_user_model
from django.http import JsonResponse, HttpResponseForbidden
from django.views import View
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
import json
from .viewsHelper.deposit import *
import json
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Account, User , CoinTransaction
from .viewsHelper.withdraw import *
from .viewsHelper.statement import *
from django.db.models import Max
from .viewsHelper.logging import *
from .viewsHelper.partnership_deed import *
from .viewsHelper.status_api import *
from django.contrib.auth import logout
from .viewsHelper.reset_password import *
User = get_user_model()

ROLE_PREFIX = {
    'Subadmin': 'SUB',
    'Admin': 'AD',
    'Miniadmin': 'MADMIN',
    'Master': 'MA',
    'Super': 'SA',
    'Agent': 'A',
    'Client': 'C',
}

@login_required
def get_edit_profile_form(request):
    """Returns the partial HTML for the edit form"""
    username = request.GET.get('username')
    target_acc = get_object_or_404(Account, user__username=username)
    # Send roles to the template so labels like "SUPER match share" are dynamic
    context = {
        'target_role': target_acc.role,
        'parent_role': target_acc.parent.role if target_acc.parent else 'COMPANY',
        'target_acc': target_acc,
        'parent_username': target_acc.parent.user.username if target_acc.parent else 'COMPANY',
        'parent_share': target_acc.parent.match_share if target_acc.parent else 0,
        "parent_acc": target_acc.parent if target_acc.parent else None,
    }
    return render(request, 'usermanagement/partials/editprofile.html', context)


def get_account_data(request, username):
    account = get_object_or_404(Account, user__username=username)
    parent = account.parent

    data = {
        "username": account.user.username,
        "is_active": "true" if account.user.is_active else "false",
        "share_type": account.share_type,

        # RIGHT COLUMN: Target User Data
        "match_share": float(account.match_share),
        "match_comm_type": "bet_by_bet" if account.commission_type == "BET_BY_BET" else "no_commission",
        "match_commission": float(account.match_commission),
        "session_commission": float(account.session_commission),
        "casino_share": float(account.casino_share),
        "casino_commission": float(account.casino_commission),

        # LEFT COLUMN: Parent Data (Read-only)
        "parent_match_share": float(parent.refrence_match_share) if parent else 0,
        "parent_comm_type": parent.get_commission_type_display() if parent else "N/A",
        "parent_match_comm": float(parent.match_commission) if parent else 0,
        "parent_sess_comm": float(parent.session_commission) if parent else 0,
        "parent_casino_share": float(parent.casino_share) if parent else 0,
        "parent_casino_comm": float(parent.casino_commission) if parent else 0,
    }
    return JsonResponse(data)

from decimal import Decimal, InvalidOperation
@login_required
def api_edit_user(request, username):
    if request.method not in ['POST', 'PATCH']:
        return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)

    SHARE_FIELDS = ['match_share','casino_share','match_commission','session_commission','casino_commission','coins']

    # Helper to safely parse floats
    def safe_float(value):
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0

    # Recursively checks if any descendant has BET_BY_BET
    def any_descendant_has_bet_by_bet(account):
        for child in account.children.all():
            if child.commission_type == 'BET_BY_BET':
                return True
            if any_descendant_has_bet_by_bet(child):
                return True
        return False

    # Recursively set NO_COMMISSION for all descendants
    def cascade_no_commission(account):
        for child in account.children.all():
            if child.commission_type == 'BET_BY_BET':
                child.commission_type = 'NO_COMMISSION'
                child.match_commission = 0
                child.session_commission = 0
                child.casino_commission = 0
                child.save()
            cascade_no_commission(child)

    try:
        account = get_object_or_404(Account, user__username=username)
        data = json.loads(request.body)
        user = account.user
        parent = account.parent        
        
        # Update refrence_match_share before the atomic transaction
        value = data.get("parent_match_share")
        if parent and value is not None:
            try:
                if parent.share_type == "CHANGE":
                    if float(data.get("parent_match_share")) + float(data.get("match_share")) > parent.match_share:
                        return JsonResponse({
                            "status": "error",
                            "message": (
                                f"Total match share (my match share + user match share) cannot exceed {parent.match_share}. "
                            )
                        }, status=400)
                print("Updating parent's refrence_match_share to:",account.parent.refrence_match_share, parent.user.username, value)
                g_parent = parent.parent.refrence_match_share
                if g_parent:
                    updated_g_m_share = parent.parent.refrence_match_share + parent.parent.match_share - (Decimal(str(data.get("parent_match_share", 0))) + Decimal(str(data.get("match_share", 0))))
                    parent.parent.refrence_match_share = updated_g_m_share
                    parent.parent.save(update_fields=['refrence_match_share'])
                    parent.parent.refresh_from_db(fields=['refrence_match_share'])
                account.parent.refrence_match_share = Decimal(value)
                parent.save(update_fields=['refrence_match_share'])
                parent.refresh_from_db(fields=['refrence_match_share'])
            except Exception as e:
                return JsonResponse({"status": "error", "message": f"Failed to update refrence_match_share: {str(e)}"}, status=400)

        with transaction.atomic():
            # --- Update is_active ---
            if 'is_active' in data:
                user.is_active = str(data.get('is_active')).lower() in ['true', '1', 'yes']
                user.save(update_fields=['is_active'])

            # --- Validate child share constraints ---
            for field in ['match_share', 'casino_share']:
                if field in data:
                    new_share = safe_float(data.get(field))
                    if account.role == "Agent":
                        setattr(account, field, new_share)
                    else:
                        violating_child = account.children.order_by(f'-{field}').first()
                        if violating_child and new_share < getattr(violating_child, field):
                            return JsonResponse({
                                "status": "error",
                                "message": (
                                    f"Cannot set {field} to {new_share}. "
                                    f"Child user has higher value ({getattr(violating_child, field)})."
                                )
                            }, status=400)
                        setattr(account, field, new_share)

            # --- Validate parent share constraints ---
            for field in SHARE_FIELDS:
                if field in data:
                    new_value = safe_float(data.get(field))
                    if parent and new_value > getattr(parent, field):
                        return JsonResponse({
                            "status": "error",
                            "message": (
                                f"Cannot set {field.replace('_', ' ')} to {new_value}. "
                                f"Parent user '{parent.user.username}' "
                                f"has lower value ({getattr(parent, field)})."
                            )
                        }, status=400)

            # --- Agent: propagate match_share / casino_share to clients ---
            if account.role == "Agent":
                update_fields = {}
                if 'match_share' in data:
                    update_fields['match_share'] = account.match_share
                if 'casino_share' in data:
                    update_fields['casino_share'] = account.casino_share
                if update_fields:
                    account.children.update(**update_fields)

            # --- Update share_type ---
            account.share_type = data.get('share_type', account.share_type)

            # --- Commission Logic ---
            old_commission = account.commission_type
            comm_val = data.get('match_comm_type')
            new_commission = old_commission
            if comm_val:
                new_commission = "BET_BY_BET" if comm_val == "bet_by_bet" else "NO_COMMISSION"

            # --- Handle NO_COMMISSION downgrade ---
            if new_commission == "NO_COMMISSION":
                if account.role == "Agent":
                    # Cascade to all clients
                    pass
                else:
                    # Upper levels → block if any descendant has BET_BY_BET
                    if any_descendant_has_bet_by_bet(account):
                        return JsonResponse({
                            "status": "error",
                            "message": (
                                "Cannot set commission to NO_COMMISSION because one or more "
                                "descendants have BET_BY_BET commission. "
                                "Please update all descendants first."
                            )
                        }, status=400)

            # Apply new commission
            account.commission_type = new_commission

            # Set commission fields
            if account.commission_type == "NO_COMMISSION":
                account.match_commission = 0
                account.session_commission = 0
                account.casino_commission = 0
            else:
                account.match_commission = safe_float(data.get('match_commission', account.match_commission))
                account.session_commission = safe_float(data.get('session_commission', account.session_commission))
                account.casino_commission = safe_float(data.get('casino_commission', account.casino_commission))

            # --- Save account ---
            account.save()

        return JsonResponse({"status": "success", "message": f"Account for {username} updated"})

    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=400)


@login_required
def get_upline_users(request, role):
    """
    Return users who can act as immediate parent for `role`
    """
    accounts = Account.objects.filter(role__iexact=role)
    print("inside upline users")
    data = [
        {
            "username": acc.user.username,
            "role": acc.role
        }
        for acc in accounts
    ]
    print(data)
    return JsonResponse(data, safe=False)
def get_all_descendants(account):
    descendants = []
    children = Account.objects.filter(parent=account).select_related('user')
    for child in children:
        descendants.append(child)
        descendants.extend(get_all_descendants(child))
    return descendants
@login_required
def get_downline_data(request, role_name):
    print(role_name)
    try:
        # 1. Get current user's account
        user_account = Account.objects.get(user=request.user)
        
        # 2. Match role case-insensitively (Subadmin vs subadmin)
        # Use __iexact to avoid capitalization issues
        all_descendants = get_all_descendants(user_account)
        accounts = [acc for acc in all_descendants if acc.role.lower() == role_name.lower()]

        for data in accounts:
            print(data.user.username , data.role,data.coins, data.match_share, data.match_commission,data.session_commission,data.casino_share,data.casino_commission)
        my_level = ROLE_LEVEL.get(user_account.role, 0)
        target_level = ROLE_LEVEL.get(role_name.capitalize(), 0)
        print(accounts)
        print("My level:", my_level, "Target level:", target_level, accounts, role_name.capitalize())
        return render(request, "usermanagement/partials/agent_table.html", {
            "target_role": role_name.capitalize(),
            "accounts": accounts,
            "target_level": target_level,
            "my_level": my_level,
            
        })
    except Exception as e:
        # This will show the actual error in your server console
        print(f"Error in get_downline_data: {e}")
        return HttpResponse("Internal Server Error", status=500)
@login_required
def dashboard_view(request):
    user = request.user
    user_role = user.role
    user_level = ROLE_LEVEL.get(user_role, 0)

    # Get downline roles with lower role levels
    downline_roles = [
        role for role, level in ROLE_LEVEL.items()
        if level < user_level
    ]

    # Fetch Account linked to this user
    try:
        account = Account.objects.get(user=user)
    except Account.DoesNotExist:
        account = None

    # Fetch number of members (children) under this user in Account model
    members_count = 0
    if account:
        members_count = account.children.count()

    # Example logic to calculate shares/commissions — adjust according to your actual logic!
    my_share = account.match_share if account else 0
    company_share = 100 - my_share if account else 0  # assuming company share is remainder

    match_commission = account.match_commission if account else 0
    session_commission = account.session_commission if account else 0



    context = {
        "role": user_role,
        "downline_roles": downline_roles,
        "coins": account.coins if account else 0,
        "members_count": members_count,
        "my_share": account.match_share,
        "company_share": company_share if company_share else 0,
        "match_commission": match_commission,
        "session_commission": session_commission,
      
    }
    print(context)
    return render(request, "usermanagement/dashboard.html", context)

def generate_username(role):
    #role = request.GET.get("role")

    if not role:
        return Response(
            {"error": "Role is required"},
            status=400
        )

    prefix = ROLE_PREFIX.get(role)

    if not prefix:
        return Response(
            {"error": "Invalid role"},
            status=400
        )

    total_users = User.objects.count()
    next_number = total_users + 1

    generated_username = f"{prefix}{next_number}"

    return generated_username
import random
import string

def generate_alphanumeric_8():
    chars = string.ascii_letters + string.digits
    return ''.join(random.choices(chars, k=8))
# Create your views here.
class LoginAPIView(APIView):
    """
    DRF API endpoint for login.
    Returns auth token on successful login.
    """
    renderer_classes = [TemplateHTMLRenderer]
    template_name = "usermanagement/login.html"
    def get(self, request):
        # Just render the login page
        return Response()
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        username = serializer.validated_data["username"]
        password = serializer.validated_data["password"]

        user = authenticate(request, username=username, password=password)

        if user:
            # Get or create token
            login(request, user)
            token, created = Token.objects.get_or_create(user=user)
            return redirect("dashboard")
        return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)

@login_required
def get_registration_form(request):
    current_user = request.user
    print("Current user:", current_user.username, "Role:", current_user.role)
    current_user_role = current_user.role
    try:
        current_account = Account.objects.get(user=current_user)
    except Account.DoesNotExist:
        current_account = None
    role = request.GET.get("role", "").strip()
    parent_username = request.GET.get("parent", "").strip()

    parent_account = None

    if parent_username:
        try:
            parent_user = User.objects.get(username=parent_username)
            parent_account = Account.objects.get(user=parent_user)
        except (User.DoesNotExist, Account.DoesNotExist):
            parent_account = None
    generated_username=generate_username(role=role)
    password = generate_alphanumeric_8()
    context = {
        "target_role": role or "User",
        "parent_username": parent_username if parent_username else current_user.username,
        "generated_username": generated_username,
        "password": password,
        # Parent info (safe defaults)
        "parent_role": parent_account.role if parent_account else current_user_role,
        "parent_coins": parent_account.coins if parent_account else  (current_account.coins if current_account else 0),

        "my_match_share": parent_account.match_share if parent_account else current_account.match_share if current_account else 0,
        "my_match_comm": parent_account.match_commission if parent_account else current_account.match_commission if current_account else 0,
        "my_casino_share": parent_account.casino_share if parent_account else current_account.casino_share if current_account else 0,
        "my_casino_comm": parent_account.casino_commission if parent_account else current_account.casino_commission if current_account else 0,
        "my_session_comm": parent_account.session_commission if parent_account else current_account.session_commission if current_account else 0,
        "my_comm_type": "Bet by bet",
    }

    return render(
        request,
        "usermanagement/partials/registration_form.html",
        context
    )


@login_required
def get_creator_limits(request, username):
    try:
        acc = Account.objects.get(user__username=username)
        return Response({
            "coins": acc.coins,
            "match_share": acc.match_share,
            "comm_type": "Bet by bet",
            "match_comm": acc.match_commission,
            "session_comm": acc.session_commission,
            "casino_share": acc.casino_share,
            "casino_comm": acc.casino_commission,
        })
    except Account.DoesNotExist:
        return Response({"error": "Not found"}, status=404)

class UserCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]  # Only logged-in users can create

    def post(self, request):
        serializer = UserCreateSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response({
                "message": "User created successfully",
                "username": user.username,
                "role": user.role
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
def logout_view(request):
    logout(request)
    return redirect('login')  
