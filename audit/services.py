"""Central audit logging (SRS FR-17).

`log_action` records who did what to which record, scoped to a tenant so the
audit screen can show a company only its own trail. It never raises — logging
must not break the action being logged.
"""
from .models import AuditLog


def client_ip(request):
    if request is None:
        return None
    xff = request.META.get('HTTP_X_FORWARDED_FOR') if hasattr(request, 'META') else None
    if xff:
        return xff.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR') if hasattr(request, 'META') else None


def log_action(request, action, *, instance=None, model_name=None, object_id=None,
               tenant=None, before=None, after=None):
    """Write an AuditLog row. Safe to call from anywhere."""
    try:
        user = getattr(request, 'user', None)
        user = user if (user is not None and user.is_authenticated) else None

        if instance is not None:
            model_name = model_name or type(instance).__name__
            object_id = object_id if object_id is not None else instance.pk
            if tenant is None:
                tenant = getattr(instance, 'tenant', None)
                if tenant is None:
                    from tenants.models import TenantCompany
                    if isinstance(instance, TenantCompany):
                        tenant = instance
            if after is None:
                after = {'repr': str(instance)}
        if tenant is None:
            tenant = getattr(request, 'tenant', None)

        AuditLog.objects.create(
            tenant=tenant if getattr(tenant, 'pk', None) else None,
            user=user,
            action=action,
            model_name=model_name or '',
            object_id=str(object_id or ''),
            before_json=before,
            after_json=after,
            ip_address=client_ip(request),
        )
    except Exception:
        # Never let auditing break the underlying operation.
        pass
