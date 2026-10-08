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


class TenantMessagingConfig(TimeStampedModel):
    """Per-tenant SMS and WhatsApp gateway settings so invoices are sent from
    the client's own sender ID / WhatsApp number (SRS FR-16)."""

    class SMSProvider(models.TextChoices):
        SPARROW = 'sparrow', 'Sparrow SMS'
        AAKASH = 'aakash', 'Aakash SMS'
        TWILIO = 'twilio', 'Twilio'

    class WhatsAppProvider(models.TextChoices):
        META = 'meta', 'WhatsApp Cloud API (Meta)'
        TWILIO = 'twilio', 'Twilio'

    tenant = models.OneToOneField(
        TenantCompany, on_delete=models.CASCADE, related_name='messaging_config')
    country_code = models.CharField(
        'Default country code', max_length=5, default='977',
        help_text='Added to local numbers for Twilio / WhatsApp, e.g. 977 for Nepal.')

    # --- SMS ---
    sms_enabled = models.BooleanField('Enable SMS', default=False)
    sms_provider = models.CharField(
        'SMS provider', max_length=10, choices=SMSProvider.choices,
        default=SMSProvider.SPARROW)
    sms_token = models.CharField(
        'SMS API token', max_length=255, blank=True,
        help_text='Sparrow/Aakash token, or the Twilio auth token.')
    sms_account_sid = models.CharField(
        'SMS account SID', max_length=100, blank=True, help_text='Twilio only.')
    sms_sender = models.CharField(
        'SMS sender', max_length=50, blank=True,
        help_text='Sparrow "identity" or Twilio "from" number. Not used by Aakash.')

    # --- WhatsApp ---
    whatsapp_enabled = models.BooleanField('Enable WhatsApp', default=False)
    whatsapp_provider = models.CharField(
        'WhatsApp provider', max_length=10, choices=WhatsAppProvider.choices,
        default=WhatsAppProvider.META)
    whatsapp_token = models.CharField(
        'WhatsApp access token', max_length=500, blank=True,
        help_text='Meta permanent access token, or the Twilio auth token.')
    whatsapp_account_sid = models.CharField(
        'WhatsApp account SID', max_length=100, blank=True, help_text='Twilio only.')
    whatsapp_sender = models.CharField(
        'WhatsApp sender', max_length=50, blank=True,
        help_text='Meta "phone number ID", or the Twilio WhatsApp number (e.g. +14155238886).')
    whatsapp_template = models.CharField(
        'WhatsApp template name', max_length=100, blank=True,
        help_text='Meta only. Approved template with 4 body variables: customer, '
                  'invoice no, amount, link. Leave blank to send plain text '
                  '(Meta only delivers that within 24h of the customer\'s last message).')
    whatsapp_template_language = models.CharField(
        'Template language', max_length=10, default='en', blank=True)

    class Meta:
        verbose_name = 'SMS / WhatsApp configuration'
        verbose_name_plural = 'SMS / WhatsApp configurations'

    def __str__(self):
        return f'SMS/WhatsApp for {self.tenant.name}'

    @property
    def sms_ready(self):
        return self.sms_enabled and bool(self.sms_token)

    @property
    def whatsapp_ready(self):
        return self.whatsapp_enabled and bool(self.whatsapp_token and self.whatsapp_sender)
