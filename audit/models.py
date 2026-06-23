"""Audit log of important create/update/cancel/payment/subscription actions.

Implements SRS FR-17 and the auditability NFR — financial and subscription
changes must be traceable.
"""
from django.conf import settings
from django.db import models

from core.models import TimeStampedModel


class AuditLog(TimeStampedModel):
    """An immutable record of a significant action (SRS FR-17)."""

    class Action(models.TextChoices):
        CREATE = 'create', 'Create'
        UPDATE = 'update', 'Update'
        DELETE = 'delete', 'Delete'
        CANCEL = 'cancel', 'Cancel / Void'
        PAYMENT = 'payment', 'Payment'
        EMAIL = 'email', 'Email / Share'
        SUBSCRIPTION = 'subscription', 'Subscription Change'
        LOGIN = 'login', 'Login'
        LOGOUT = 'logout', 'Logout'
        IMPERSONATE = 'impersonate', 'Support Impersonation'

    tenant = models.ForeignKey(
        'tenants.TenantCompany', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='audit_logs',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='audit_logs',
    )
    action = models.CharField(max_length=20, choices=Action.choices)
    model_name = models.CharField(max_length=100, blank=True)
    object_id = models.CharField(max_length=64, blank=True)
    before_json = models.JSONField(null=True, blank=True)
    after_json = models.JSONField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant', 'model_name', 'created_at']),
            models.Index(fields=['user', 'created_at']),
        ]

    def __str__(self):
        return f'{self.get_action_display()} {self.model_name}#{self.object_id} by {self.user}'
