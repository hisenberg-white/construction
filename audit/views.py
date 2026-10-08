"""Read-only audit log views (SRS FR-17, module 'audit')."""
from core import permissions
from core.crud import CrudDetailView, CrudListView

from .models import AuditLog

MODULE = permissions.AUDIT

SAAS_ROLES = (permissions.SAAS_SUPER_ADMIN, permissions.SAAS_STAFF)


def is_saas_user(user):
    """SaaS owner side (superuser / SaaS staff), as opposed to a company user."""
    profile = getattr(user, 'profile', None)
    return bool(user.is_superuser or getattr(user, 'is_saas_staff', False)
                or (profile is not None and profile.role in SAAS_ROLES))


def scope_audit_logs(request, qs):
    """Restrict audit rows to what this user may see.

    * SaaS owner/staff: every company, or the company they're working in.
    * Company users: only their own company's rows made by their own
      company's users — SaaS admin/support activity is hidden, and a user
      with no company sees nothing (never other companies' logs).
    """
    if is_saas_user(request.user):
        return qs.filter(tenant=request.tenant) if request.tenant is not None else qs
    if request.tenant is None:
        return qs.none()
    return (qs.filter(tenant=request.tenant)
              .exclude(user__is_superuser=True)
              .exclude(user__is_saas_staff=True)
              .exclude(user__profile__role__in=SAAS_ROLES))


class AuditLogListView(CrudListView):
    model = AuditLog
    permission_module = MODULE
    crud_basename = 'auditlog'
    title = 'Audit Log'
    template_name = 'audit/auditlog_list.html'
    # SaaS owner (no company) sees all tenants' logs; a tenant user is scoped to
    # their own company by TenantScopedQuerysetMixin.
    requires_tenant = False
    paginate_by = 50
    list_display = ['created_at', 'tenant', 'user', 'action', 'model_name', 'object_id']

    def get_queryset(self):
        qs = scope_audit_logs(self.request, super().get_queryset())
        qs = qs.select_related('user', 'tenant').order_by('-created_at')
        params = self.request.GET
        date_from = params.get('date_from', '').strip()
        date_to = params.get('date_to', '').strip()
        action = params.get('action', '').strip()
        search = params.get('search', '').strip()
        if date_from:
            qs = qs.filter(created_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(created_at__date__lte=date_to)
        if action:
            qs = qs.filter(action=action)
        if search:
            from django.db.models import Q
            qs = qs.filter(
                Q(user__username__icontains=search) | Q(model_name__icontains=search)
            )
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        params = self.request.GET
        context['filter_date_from'] = params.get('date_from', '')
        context['filter_date_to'] = params.get('date_to', '')
        context['filter_action'] = params.get('action', '')
        context['filter_search'] = params.get('search', '')
        context['action_choices'] = AuditLog.Action.choices
        return context


class AuditLogDetailView(CrudDetailView):
    model = AuditLog
    permission_module = MODULE
    crud_basename = 'auditlog'
    requires_tenant = False
    list_display = ['created_at', 'tenant', 'user', 'action', 'model_name',
                    'object_id', 'before_json', 'after_json', 'ip_address']

    def get_queryset(self):
        return scope_audit_logs(self.request, super().get_queryset())
