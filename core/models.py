"""Shared abstract base models and mixins for DepotLedger SaaS.

These enforce the cross-cutting rules from SRS section 12.2:

* every tenant-owned business model carries a ``tenant`` foreign key;
* every record stores ``created_at`` / ``updated_at`` / ``created_by`` /
  ``updated_by`` for auditability (SRS FR-03, FR-17);
* financial records are never hard-deleted — they are cancelled/reversed
  with a reason and an audit trail.
"""
from django.conf import settings
from django.db import models


class TimeStampedModel(models.Model):
    """Adds self-managed created/updated timestamps."""

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class ActorStampedModel(TimeStampedModel):
    """Adds the user who created and last updated the record."""

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(app_label)s_%(class)s_created',
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(app_label)s_%(class)s_updated',
    )

    class Meta:
        abstract = True


class TenantQuerySet(models.QuerySet):
    """QuerySet helper that makes tenant scoping explicit and hard to forget."""

    def for_tenant(self, tenant):
        return self.filter(tenant=tenant)


class TenantManager(models.Manager.from_queryset(TenantQuerySet)):
    """Default manager exposing :meth:`for_tenant`."""


class TenantOwnedModel(ActorStampedModel):
    """Base class for every tenant-scoped business model (SRS 12.2).

    Never query subclasses without filtering by ``tenant`` — use
    ``Model.objects.for_tenant(request.tenant)``.
    """

    tenant = models.ForeignKey(
        'tenants.TenantCompany',
        on_delete=models.CASCADE,
        related_name='%(app_label)s_%(class)s_set',
        db_index=True,
    )

    objects = TenantManager()

    class Meta:
        abstract = True


class CancellableModel(models.Model):
    """Soft-cancel support for financial records (SRS FR-17).

    Financial transactions (invoices, purchases, payments, stock entries)
    must not be hard-deleted; they are cancelled with a reason and reversed.
    """

    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        ACTIVE = 'active', 'Active'
        CANCELLED = 'cancelled', 'Cancelled'

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True,
    )
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancel_reason = models.TextField(blank=True)

    class Meta:
        abstract = True

    @property
    def is_cancelled(self):
        return self.status == self.Status.CANCELLED
