"""User & role management views (SRS FR-03, module 'users_roles')."""
from django.contrib import messages
from django.urls import reverse
from django.views.generic import FormView, TemplateView

from core import permissions
from core.crud import (
    CrudContextMixin,
    CrudDeleteView,
    CrudDetailView,
    CrudListView,
    CrudUpdateView,
    PermissionRequiredMixin,
)

from .forms import UserCreateForm, UserProfileForm
from .models import UserProfile

MODULE = permissions.USERS_ROLES


class NoTenantView(TemplateView):
    template_name = 'accounts/no_tenant.html'


class UserProfileListView(CrudListView):
    model = UserProfile
    permission_module = MODULE
    crud_basename = 'userprofile'
    list_display = ['user', 'tenant', 'role', 'phone', 'is_active']
    title = 'Users & Roles'
    requires_tenant = False  # SaaS owner manages users across companies

    def get_queryset(self):
        return (super().get_queryset()
                .select_related('user', 'tenant').order_by('user__username'))


class UserProfileDetailView(CrudDetailView):
    model = UserProfile
    permission_module = MODULE
    crud_basename = 'userprofile'
    list_display = ['user', 'tenant', 'role', 'phone', 'is_active']
    requires_tenant = False


class UserProfileCreateView(PermissionRequiredMixin, CrudContextMixin, FormView):
    """Create a user and profile in one step."""

    model = UserProfile
    permission_module = MODULE
    permission_action = 'c'
    crud_basename = 'userprofile'
    template_name = 'core/object_form.html'
    form_class = UserCreateForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['tenant'] = getattr(self.request, 'tenant', None)
        kwargs['actor'] = self.request.user
        return kwargs

    def form_valid(self, form):
        profile = form.save()
        from audit.services import log_action
        log_action(self.request, 'create', instance=profile,
                   after={'user': str(profile.user), 'role': profile.get_role_display()})
        messages.success(self.request, 'User created.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse(self.crud_url_name('list'))


class UserProfileUpdateView(CrudUpdateView):
    model = UserProfile
    permission_module = MODULE
    crud_basename = 'userprofile'
    form_class = UserProfileForm
    list_display = ['user', 'role', 'phone', 'is_active']
    requires_tenant = False

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['tenant'] = getattr(self.request, 'tenant', None)
        kwargs['actor'] = self.request.user
        return kwargs


class UserProfileDeleteView(CrudDeleteView):
    model = UserProfile
    permission_module = MODULE
    crud_basename = 'userprofile'
    list_display = ['user', 'role']
    requires_tenant = False
