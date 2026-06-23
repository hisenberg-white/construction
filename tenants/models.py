"""Tenant company and depot/location models (SRS FR-01, FR-02)."""
from django.db import models

from core.models import TimeStampedModel


class TenantCompany(TimeStampedModel):
    """A construction-supplier business that subscribes to the SaaS (a tenant).

    This model is intentionally NOT tenant-owned — it *is* the tenant.
    """

    class SubscriptionStatus(models.TextChoices):
        TRIAL = 'trial', 'Trial'
        ACTIVE = 'active', 'Active'
        GRACE = 'grace', 'Grace Period'
        EXPIRED = 'expired', 'Expired (read-only)'
        SUSPENDED = 'suspended', 'Suspended'

    name = models.CharField(max_length=200)
    registration_no = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    default_currency = models.CharField(max_length=8, default='NPR')
    invoice_prefix = models.CharField(max_length=20, default='INV')

    # Subscription snapshot (managed by the subscriptions app, mirrored here
    # for fast access-control checks on every request — SRS 10.6).
    current_plan = models.ForeignKey(
        'subscriptions.SaaSPlan',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tenants',
    )
    subscription_status = models.CharField(
        max_length=20,
        choices=SubscriptionStatus.choices,
        default=SubscriptionStatus.TRIAL,
    )
    subscription_start = models.DateField(null=True, blank=True)
    subscription_end = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    # Invoice branding (SRS FR-01: invoice branding; appendix sample invoice).
    logo = models.ImageField(
        upload_to='tenant_logos/', blank=True, null=True,
        help_text='Company logo shown on invoices.')

    class Calendar(models.TextChoices):
        AD = 'AD', 'English date (AD)'
        BS = 'BS', 'Nepali date (BS)'

    # Preferred calendar for displaying/entering dates (SRS NFR: Localization).
    default_calendar = models.CharField(
        max_length=2, choices=Calendar.choices, default=Calendar.AD,
        help_text='Default calendar shown to this company’s users.')

    class Meta:
        verbose_name = 'Tenant Company'
        verbose_name_plural = 'Tenant Companies'
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def can_create_entries(self):
        """Whether new billable entries are allowed (SRS 8.2, 10.6)."""
        return self.subscription_status in {
            self.SubscriptionStatus.TRIAL,
            self.SubscriptionStatus.ACTIVE,
            self.SubscriptionStatus.GRACE,
        }


class DepotLocation(TimeStampedModel):
    """A depot / warehouse / branch (dipo) belonging to a tenant (SRS FR-02)."""

    tenant = models.ForeignKey(
        TenantCompany,
        on_delete=models.CASCADE,
        related_name='depots',
    )
    name = models.CharField(max_length=200)
    address = models.TextField(blank=True)
    contact_person = models.CharField(max_length=200, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    opening_balance = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['tenant', 'name']
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'name'], name='unique_depot_name_per_tenant'
            ),
        ]

    def __str__(self):
        return f'{self.name} — {self.tenant.name}'


class TenantEmailConfig(TimeStampedModel):
    """Per-tenant SMTP settings so invoices are emailed from the client's own
    mailbox (SRS FR-16: invoice delivery by email)."""

    tenant = models.OneToOneField(
        TenantCompany, on_delete=models.CASCADE, related_name='email_config')
    host = models.CharField('SMTP host', max_length=200)
    port = models.PositiveIntegerField('SMTP port', default=587)
    username = models.CharField(max_length=200, blank=True)
    password = models.CharField(max_length=255, blank=True)
    use_tls = models.BooleanField('Use TLS', default=True)
    use_ssl = models.BooleanField('Use SSL', default=False)
    from_email = models.EmailField('From address')
    from_name = models.CharField('From name', max_length=200, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Email (SMTP) configuration'
        verbose_name_plural = 'Email (SMTP) configurations'

    def __str__(self):
        return f'SMTP for {self.tenant.name}'

    @property
    def sender(self):
        return f'{self.from_name} <{self.from_email}>' if self.from_name else self.from_email

    def get_connection(self):
        """Build a Django SMTP connection from these settings."""
        from django.core.mail import get_connection
        return get_connection(
            backend='django.core.mail.backends.smtp.EmailBackend',
            host=self.host, port=self.port,
            username=self.username or None, password=self.password or None,
            use_tls=self.use_tls, use_ssl=self.use_ssl, fail_silently=False,
        )
