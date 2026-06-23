"""User, role and profile models (SRS section 4 and FR-03).

A custom ``User`` is used from the start (Django best practice) so the
project can grow without a painful migration later. ``UserProfile`` binds a
user to a tenant, a role and the depot locations they may operate in.
"""
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models

from core.models import TimeStampedModel


class User(AbstractUser):
    """Application user.

    SaaS-owner staff have no tenant (they operate across all tenants); tenant
    users reach their tenant/role through :class:`UserProfile`.
    """

    is_saas_staff = models.BooleanField(
        default=False,
        help_text='SaaS owner / super-admin staff who manage all tenants.',
    )
    phone = models.CharField(max_length=30, blank=True)

    def __str__(self):
        return self.get_full_name() or self.username


class Role(models.TextChoices):
    """Roles from SRS section 4.1."""

    SAAS_SUPER_ADMIN = 'saas_super_admin', 'SaaS Super Admin'
    SAAS_STAFF = 'saas_staff', 'SaaS Staff'
    CLIENT_OWNER = 'client_owner', 'Client Owner'
    CLIENT_ADMIN = 'client_admin', 'Client Admin / Accountant'
    DEPOT_ADMIN = 'depot_admin', 'Depot Admin / Location Manager'
    BILLING_USER = 'billing_user', 'Sales / Billing User'
    STOCK_USER = 'stock_user', 'Purchase / Stock User'
    VIEWER = 'viewer', 'Read-Only Viewer'
    STAFF = 'staff', 'Staff'


class UserProfile(TimeStampedModel):
    """Tenant membership, role and location scope for a user (SRS FR-03)."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile',
    )
    tenant = models.ForeignKey(
        'tenants.TenantCompany',
        on_delete=models.CASCADE,
        related_name='user_profiles',
        null=True,
        blank=True,
    )
    role = models.CharField(max_length=32, choices=Role.choices, default=Role.VIEWER)
    # Empty assigned_locations means "all locations of the tenant".
    assigned_locations = models.ManyToManyField(
        'tenants.DepotLocation',
        blank=True,
        related_name='assigned_users',
    )
    phone = models.CharField(max_length=30, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f'{self.user} ({self.get_role_display()})'

    @property
    def has_all_locations(self):
        return not self.assigned_locations.exists()
