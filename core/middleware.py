"""Request middleware that attaches the current tenant and profile.

Tenant isolation (SRS NFR Security, 12.2) depends on knowing *which* tenant a
request belongs to. We resolve it once per request:

* a normal tenant user → their profile's company;
* a SaaS owner / superuser → the company they've chosen to "work in" (stored in
  the session), so they can view dashboards and enter data for that client.
"""


class CurrentTenantMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.profile = None
        request.tenant = None
        request.acting_company = False
        user = getattr(request, 'user', None)
        if user is not None and user.is_authenticated:
            profile = getattr(user, 'profile', None)
            request.profile = profile
            if profile is not None and profile.tenant_id:
                request.tenant = profile.tenant
            elif user.is_superuser or getattr(user, 'is_saas_staff', False):
                # SaaS owner working inside a selected client company.
                tenant_id = request.session.get('acting_tenant_id')
                if tenant_id:
                    from tenants.models import TenantCompany
                    company = TenantCompany.objects.filter(pk=tenant_id, is_active=True).first()
                    if company is not None:
                        request.tenant = company
                        request.acting_company = True
        return self.get_response(request)
