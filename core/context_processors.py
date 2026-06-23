"""Template context: which modules the current user may see (for navigation),
and — for SaaS owners — the company switcher options."""
from . import permissions


def navigation(request):
    user = getattr(request, 'user', None)
    if user is None or not user.is_authenticated:
        return {'access': set(), 'user_role': None}

    tenant = getattr(request, 'tenant', None)
    profile = getattr(request, 'profile', None)
    is_saas = (user.is_superuser or getattr(user, 'is_saas_staff', False)) and (
        profile is None or not profile.tenant_id)

    context = {
        'access': permissions.readable_modules(user),
        'user_role': permissions.get_role(user),
        'current_tenant': tenant,
        'use_bs': bool(tenant and getattr(tenant, 'default_calendar', 'AD') == 'BS'),
        'is_saas': is_saas,
        'acting_company': getattr(request, 'acting_company', False),
    }
    if is_saas:
        from tenants.models import TenantCompany
        context['saas_companies'] = TenantCompany.objects.filter(is_active=True).order_by('name')
    return context
