"""Reusable generic CRUD building blocks with RBAC and tenant isolation.

Concrete screens subclass these and set a few attributes (model, form_class,
``list_display``, ``permission_module``, ``crud_basename``). The base classes
provide: login + permission enforcement (SRS 4.2), tenant-scoped querysets and
auto-stamped tenant/created_by/updated_by (SRS 12.2), generic list/detail
rendering and consistent success URLs.
"""
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.urls import NoReverseMatch, path, reverse
from django.utils import timezone
from django.views import View
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)

from . import permissions


# --- Shared mixins -----------------------------------------------------------
class PermissionRequiredMixin(LoginRequiredMixin):
    """Enforce a (module, action) permission for the view (SRS 4.2)."""

    permission_module = None
    permission_action = 'r'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)
        if self.permission_module and not permissions.has_perm(
            request.user, self.permission_module, self.permission_action
        ):
            raise PermissionDenied('You do not have permission for this action.')
        return super().dispatch(request, *args, **kwargs)


class TenantRequiredMixin:
    """Require a current company for tenant-scoped screens.

    A SaaS owner / superuser with no company selected is sent to the dashboard
    with a hint to pick one (so data entry can't hit a NULL-tenant error); a
    normal user with no company goes to the friendly no-company page. Set
    ``requires_tenant = False`` to opt out (e.g. global user management).
    """

    requires_tenant = True

    def dispatch(self, request, *args, **kwargs):
        if (self.requires_tenant and request.user.is_authenticated
                and getattr(request, 'tenant', None) is None):
            if request.user.is_superuser or getattr(request.user, 'is_saas_staff', False):
                messages.info(request, 'Select a company from the top bar to work in first.')
                return redirect('reports:dashboard')
            return redirect('accounts:no_tenant')
        return super().dispatch(request, *args, **kwargs)


class CrudContextMixin:
    """Supplies the navigation/rendering context shared by every CRUD screen."""

    crud_basename = None          # e.g. 'customer' -> customer_list/create/...
    list_display = []             # field names shown in list & detail tables
    delete_action = None          # 'delete' | 'cancel' | None
    title = None

    # -- url helpers --
    def _ns(self):
        ns = self.request.resolver_match.namespace
        return f'{ns}:' if ns else ''

    def crud_url_name(self, action):
        return f'{self._ns()}{self.crud_basename}_{action}'

    def get_crud_urls(self):
        return {a: self.crud_url_name(a)
                for a in ('list', 'create', 'detail', 'update', 'delete', 'cancel')}

    def url_available(self, action):
        """Whether the CRUD url for ``action`` is actually wired up.

        Lets the generic templates support read-only or partial-CRUD screens
        without raising NoReverseMatch for buttons the screen doesn't offer.
        """
        name = self.crud_url_name(action)
        try:
            if action in ('detail', 'update', 'delete', 'cancel'):
                reverse(name, args=[0])
            else:
                reverse(name)
            return True
        except NoReverseMatch:
            return False

    # -- field rendering --
    def field_label(self, name):
        try:
            return self.model._meta.get_field(name).verbose_name.title()
        except Exception:
            return name.replace('_', ' ').title()

    def _uses_bs(self):
        tenant = getattr(self.request, 'tenant', None)
        return bool(tenant and getattr(tenant, 'default_calendar', 'AD') == 'BS')

    def field_value(self, obj, name):
        display = getattr(obj, f'get_{name}_display', None)
        if callable(display):
            return display()
        value = getattr(obj, name, None)
        if callable(value):
            value = value()
        if value is None or value == '':
            return '—'
        if isinstance(value, bool):
            return 'Yes' if value else 'No'
        import datetime
        if isinstance(value, datetime.date) and self._uses_bs():
            from .dates import ad_to_bs_str
            return ad_to_bs_str(value)
        return value

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        module = self.permission_module
        context.update({
            'crud': self.get_crud_urls(),
            'crud_basename': self.crud_basename,
            'verbose_name': self.model._meta.verbose_name.title(),
            'verbose_name_plural': self.model._meta.verbose_name_plural.title(),
            'page_title': self.title or self.model._meta.verbose_name_plural.title(),
            'list_display': self.list_display,
            'delete_action': self.delete_action,
            'can_create': permissions.has_perm(user, module, 'c'),
            'can_update': permissions.has_perm(user, module, 'u'),
            'can_delete': permissions.has_perm(user, module, 'd'),
            'can_cancel': permissions.has_perm(user, module, 'u'),
            'available': {a: self.url_available(a)
                          for a in ('create', 'detail', 'update', 'delete', 'cancel')},
        })
        return context


class _FormStampMixin:
    """Pass the tenant to the form and stamp tenant/created_by/updated_by."""

    scoped = True  # tenant-owned model?
    audit_action = 'update'  # overridden to 'create' on create views

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        from .forms import TenantModelForm
        form_class = self.get_form_class()
        if isinstance(form_class, type) and issubclass(form_class, TenantModelForm):
            kwargs['tenant'] = getattr(self.request, 'tenant', None)
        return kwargs

    def form_valid(self, form):
        obj = form.save(commit=False)
        if self.scoped and hasattr(obj, 'tenant_id') and not obj.tenant_id:
            obj.tenant = self.request.tenant
        if hasattr(obj, 'created_by_id') and not obj.created_by_id:
            obj.created_by = self.request.user
        if hasattr(obj, 'updated_by_id'):
            obj.updated_by = self.request.user
        obj.save()
        form.save_m2m()
        self.object = obj
        from audit.services import log_action
        log_action(self.request, self.audit_action, instance=obj)
        messages.success(self.request, f'{self.model._meta.verbose_name.title()} saved.')
        return super().form_valid(form)


# --- Tenant-scoped CRUD bases ------------------------------------------------
class TenantScopedQuerysetMixin:
    def get_queryset(self):
        qs = super().get_queryset()
        tenant = getattr(self.request, 'tenant', None)
        if tenant is not None and any(f.name == 'tenant' for f in self.model._meta.fields):
            qs = qs.filter(tenant=tenant)
        # Staff users with assigned depot locations see only those depots.
        user = getattr(self.request, 'user', None)
        if user is not None and user.is_authenticated:
            profile = getattr(user, 'profile', None)
            if (profile is not None
                    and profile.role == permissions.STAFF
                    and profile.assigned_locations.exists()
                    and any(f.name == 'depot' for f in self.model._meta.fields)):
                qs = qs.filter(depot__in=profile.assigned_locations.all())
        return qs


class CrudListView(TenantRequiredMixin, PermissionRequiredMixin, CrudContextMixin,
                   TenantScopedQuerysetMixin, ListView):
    permission_action = 'r'
    template_name = 'core/object_list.html'
    paginate_by = 25
    context_object_name = 'objects'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['headers'] = [self.field_label(f) for f in self.list_display]
        rows = []
        for obj in context['objects']:
            rows.append({
                'obj': obj,
                'cells': [self.field_value(obj, f) for f in self.list_display],
            })
        context['rows'] = rows
        return context


class CrudDetailView(TenantRequiredMixin, PermissionRequiredMixin, CrudContextMixin,
                     TenantScopedQuerysetMixin, DetailView):
    permission_action = 'r'
    template_name = 'core/object_detail.html'
    context_object_name = 'obj'

    detail_fields = None  # defaults to list_display

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        fields = self.detail_fields or self.list_display
        context['detail_rows'] = [
            (self.field_label(f), self.field_value(self.object, f)) for f in fields
        ]
        return context


class CrudCreateView(TenantRequiredMixin, PermissionRequiredMixin, CrudContextMixin,
                     _FormStampMixin, CreateView):
    permission_action = 'c'
    audit_action = 'create'
    template_name = 'core/object_form.html'

    def get_success_url(self):
        return reverse(self.crud_url_name('list'))


class CrudUpdateView(TenantRequiredMixin, PermissionRequiredMixin, CrudContextMixin,
                     TenantScopedQuerysetMixin, _FormStampMixin, UpdateView):
    permission_action = 'u'
    template_name = 'core/object_form.html'

    def get_success_url(self):
        return reverse(self.crud_url_name('list'))


class CrudDeleteView(TenantRequiredMixin, PermissionRequiredMixin, CrudContextMixin,
                     TenantScopedQuerysetMixin, DeleteView):
    permission_action = 'd'
    template_name = 'core/object_confirm_delete.html'
    delete_action = 'delete'

    def get_success_url(self):
        return reverse(self.crud_url_name('list'))

    def form_valid(self, form):
        obj = self.get_object()
        from audit.services import log_action
        log_action(self.request, 'delete', instance=obj)
        messages.success(self.request, f'{self.model._meta.verbose_name.title()} deleted.')
        return super().form_valid(form)


class CrudCancelView(TenantRequiredMixin, PermissionRequiredMixin, CrudContextMixin,
                     TenantScopedQuerysetMixin, DetailView):
    """Soft-cancel a financial record with a reason (SRS FR-17)."""

    permission_action = 'u'
    template_name = 'core/object_confirm_cancel.html'
    delete_action = 'cancel'
    context_object_name = 'obj'

    def post(self, request, *args, **kwargs):
        obj = self.get_object()
        reason = request.POST.get('cancel_reason', '').strip()
        obj.status = obj.Status.CANCELLED
        obj.cancelled_at = timezone.now()
        obj.cancel_reason = reason
        if hasattr(obj, 'updated_by_id'):
            obj.updated_by = request.user
        obj.save()
        from audit.services import log_action
        log_action(request, 'cancel', instance=obj, after={'reason': reason})
        messages.warning(request, f'{self.model._meta.verbose_name.title()} cancelled.')
        return redirect(self.crud_url_name('list'))


# --- SaaS-global CRUD bases (not tenant-scoped) ------------------------------
class SaaSListView(PermissionRequiredMixin, CrudContextMixin, ListView):
    permission_module = permissions.SAAS
    permission_action = 'r'
    template_name = 'core/object_list.html'
    paginate_by = 25
    context_object_name = 'objects'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['headers'] = [self.field_label(f) for f in self.list_display]
        context['rows'] = [
            {'obj': o, 'cells': [self.field_value(o, f) for f in self.list_display]}
            for o in context['objects']
        ]
        return context


class SaaSDetailView(PermissionRequiredMixin, CrudContextMixin, DetailView):
    permission_module = permissions.SAAS
    permission_action = 'r'
    template_name = 'core/object_detail.html'
    context_object_name = 'obj'
    detail_fields = None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        fields = self.detail_fields or self.list_display
        context['detail_rows'] = [
            (self.field_label(f), self.field_value(self.object, f)) for f in fields
        ]
        return context


class SaaSCreateView(PermissionRequiredMixin, CrudContextMixin, _FormStampMixin, CreateView):
    permission_module = permissions.SAAS
    permission_action = 'c'
    audit_action = 'create'
    template_name = 'core/object_form.html'
    scoped = False

    def get_success_url(self):
        return reverse(self.crud_url_name('list'))


class SaaSUpdateView(PermissionRequiredMixin, CrudContextMixin, _FormStampMixin, UpdateView):
    permission_module = permissions.SAAS
    permission_action = 'u'
    template_name = 'core/object_form.html'
    scoped = False

    def get_success_url(self):
        return reverse(self.crud_url_name('list'))


class SaaSDeleteView(PermissionRequiredMixin, CrudContextMixin, DeleteView):
    permission_module = permissions.SAAS
    permission_action = 'd'
    template_name = 'core/object_confirm_delete.html'
    delete_action = 'delete'

    def get_success_url(self):
        return reverse(self.crud_url_name('list'))

    def form_valid(self, form):
        from audit.services import log_action
        log_action(self.request, 'delete', instance=self.get_object())
        return super().form_valid(form)


# --- URL factory -------------------------------------------------------------
def crud_urlpatterns(prefix, basename, *, list, create=None, detail=None,
                     update=None, delete=None, cancel=None):
    """Build standard CRUD url patterns for a model.

    Names follow ``<basename>_<action>`` so :class:`CrudContextMixin` can
    reverse them generically.
    """
    patterns = [path(f'{prefix}/', list.as_view(), name=f'{basename}_list')]
    if create:
        patterns.append(path(f'{prefix}/new/', create.as_view(), name=f'{basename}_create'))
    if detail:
        patterns.append(path(f'{prefix}/<int:pk>/', detail.as_view(), name=f'{basename}_detail'))
    if update:
        patterns.append(path(f'{prefix}/<int:pk>/edit/', update.as_view(), name=f'{basename}_update'))
    if delete:
        patterns.append(path(f'{prefix}/<int:pk>/delete/', delete.as_view(), name=f'{basename}_delete'))
    if cancel:
        patterns.append(path(f'{prefix}/<int:pk>/cancel/', cancel.as_view(), name=f'{basename}_cancel'))
    return patterns
