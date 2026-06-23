"""Audit login / logout events (SRS FR-17)."""
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver

from .services import log_action


def _tenant_of(user):
    profile = getattr(user, 'profile', None)
    return profile.tenant if profile else None


@receiver(user_logged_in)
def _on_login(sender, request, user, **kwargs):
    log_action(request, 'login', model_name='User', object_id=user.pk,
               tenant=_tenant_of(user), after={'username': user.get_username()})


@receiver(user_logged_out)
def _on_logout(sender, request, user, **kwargs):
    if user is not None:
        log_action(request, 'logout', model_name='User', object_id=user.pk,
                   tenant=_tenant_of(user), after={'username': user.get_username()})
