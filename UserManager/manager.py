from django.contrib.auth.models import BaseUserManager
from .roles import Role

class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, username, password=None, **extra_fields):
        if not username:
            raise ValueError("The username must be set")
        if extra_fields.get('role') is not "Client" :
            extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('role', Role.CLIENT)  # default role for normal users
        user = self.model(username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, password=None, **extra_fields):
        extra_fields.setdefault('role', Role.SUPERADMIN)
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(username, password, **extra_fields)

