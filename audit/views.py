"""Read-only audit log views (SRS FR-17, module 'audit')."""
from core import permissions
from core.crud import CrudDetailView, CrudListView

from .models import AuditLog

MODULE = permissions.AUDIT


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
        qs = super().get_queryset().select_related('user', 'tenant').order_by('-created_at')
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
