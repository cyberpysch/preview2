from rest_framework import serializers
from UserManager.models import User, Account, CoinTransaction
from UserManager.roles import ROLE_LEVEL, Role
from django.db import transaction

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

class UserCreateSerializer(serializers.Serializer):
    '''
    {
  "username": "agent_john",
  "password": "strongpassword123",
  "role": "Agent",
  "parent_username": "superadmin", 
  "coins": 1000.00,
  "match_share": 10.00,
  "casino_share": 5.00,
  "commission_type": "BET_BY_BET",
  "match_commission": 2.00,
  "session_commission": 1.00,
  "casino_commission": 2
}

    '''
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True)
    role = serializers.ChoiceField(choices=Role.choices)
    name = serializers.CharField(max_length=100, required=False, allow_blank=True)
    reference = serializers.CharField(max_length=150, required=False, allow_blank=True)
    parent_username = serializers.CharField(
        max_length=150, required=False, allow_null=True
    )
    coins = serializers.DecimalField(max_digits=20, decimal_places=2, default=0)
    match_share = serializers.DecimalField(max_digits=5, decimal_places=2, default=0)
    casino_share = serializers.DecimalField(max_digits=5, decimal_places=2, default=0)
    commission_type = serializers.ChoiceField(
        choices=Account.COMMISSION_TYPE
    )
    share_type = serializers.ChoiceField(
    choices=Account._meta.get_field("share_type").choices,
    default="FIXED"
)
    match_commission = serializers.DecimalField(max_digits=5, decimal_places=2, default=0)
    session_commission = serializers.DecimalField(max_digits=5, decimal_places=2, default=0)
    casino_commission = serializers.DecimalField(max_digits=5, decimal_places=2, default=0)

    def validate_parent_username(self, value):
        if value:
            try:
                parent_user = User.objects.get(username=value)
                self.parent_user = parent_user
            except User.DoesNotExist:
                raise serializers.ValidationError("Parent user does not exist.")
        else:
            self.parent_user = None
        return value

    def validate(self, attrs):
        role = attrs.get("role")
        if hasattr(self, "parent_user") and self.parent_user:
            parent_role = self.parent_user.role
            if ROLE_LEVEL[parent_role] <= ROLE_LEVEL[role]:
                raise serializers.ValidationError(
                    "Child role must be lower than parent role."
                )
        return attrs

    def create(self, validated_data):
        username = validated_data["username"]
        password = validated_data["password"]
        name = validated_data.get("name", "")
        role = validated_data["role"]
        initial_coins = validated_data.get("coins", 0)

        # Determine parent account
        parent_account = None
        parent_username = validated_data.get("parent_username")
        if parent_username:
            try:
                parent_user = User.objects.get(username=parent_username)
                parent_account = parent_user.account
                if parent_account.match_share < validated_data.get("match_share") or parent_account.casino_share < validated_data.get("casino_share") or parent_account.match_commission< validated_data.get("match_commission")or parent_account.session_commission < validated_data.get("session_commission") or parent_account.casino_commission< validated_data.get("casino_commission"):
                    raise serializers.ValidationError("Share or commission is more than parent")
            except User.DoesNotExist:
                raise serializers.ValidationError("Parent user does not exist.")

        #  Create User and Account (coins = 0 initially)
        user = User.objects.create_user(username=username, password=password, role=role, first_name=name)
        account = Account.objects.create(
            user=user,
            parent=parent_account,
            role=role,
            coins=0,  # initially 0
            match_share=validated_data.get("match_share", 0),
            refrence_match_share = parent_account.match_share -  validated_data.get("match_share", 0),
            casino_share=validated_data.get("casino_share", 0),
            commission_type=validated_data.get("commission_type"),
            match_commission=validated_data.get("match_commission", 0),
            session_commission=validated_data.get("session_commission", 0),
            casino_commission=validated_data.get("casino_commission", 0),
            reference=validated_data.get("reference", ""),
            share_type=validated_data.get("share_type")
        )

        # transfer coins from parent to new account atomically
        if initial_coins > 0 and parent_account:
            with transaction.atomic():
                if parent_account.coins < initial_coins:
                    raise serializers.ValidationError("Parent does not have enough coins to share.")
                
                # debit parent
                parent_account.coins -= initial_coins
                parent_account.save()

                # credit child
                account.coins += initial_coins
                account.save()

                # Optional: log both transactions in a Transaction table
                CoinTransaction.objects.create(
                sender=parent_account,
                receiver=account,
                amount=initial_coins
            )

        return user

class UserStatusSerializer(serializers.Serializer):
    username = serializers.CharField()
    is_active = serializers.BooleanField()

    def update(self, instance, validated_data):
        instance.is_active = validated_data["is_active"]
        instance.save()
        return instance