"""Forms for user & role management (SRS FR-03).

Two modes:

* **Tenant mode** — a Client Owner manages users within their own company
  (``tenant`` is fixed from the request, not shown).
* **SaaS mode** — the SaaS owner / superuser has no fixed company, so the form
  exposes a ``company`` selector to assign the user to any tenant. The user's
  *permissions* are their ``role`` (SRS section 4.2).
"""
from django import forms
from django.contrib.auth import get_user_model

from core import permissions
from core.forms import BootstrapFormMixin
from tenants.models import DepotLocation, TenantCompany

from .models import Role, UserProfile

User = get_user_model()


class UserCreateForm(BootstrapFormMixin, forms.Form):
    """Create a user together with their profile/role (and company in SaaS mode)."""

    company = forms.ModelChoiceField(
        queryset=TenantCompany.objects.none(), required=False,
        help_text='The company this user belongs to.')
    username = forms.CharField(max_length=150)
    first_name = forms.CharField(max_length=150, required=False)
    last_name = forms.CharField(max_length=150, required=False)
    email = forms.EmailField(required=False)
    password = forms.CharField(widget=forms.PasswordInput, min_length=8)
    role = forms.ChoiceField(choices=Role.choices, help_text='Determines the permissions.')
    phone = forms.CharField(max_length=30, required=False)
    assigned_locations = forms.ModelMultipleChoiceField(
        queryset=DepotLocation.objects.none(), required=False,
        widget=forms.CheckboxSelectMultiple,
        help_text='Leave empty to grant access to all depots of the company.')

    def __init__(self, *args, tenant=None, actor=None, **kwargs):
        self.fixed_tenant = tenant
        super().__init__(*args, **kwargs)
        # Hierarchy: only offer roles the creator is allowed to grant (SRS 4.1).
        if actor is not None:
            self.fields['role'].choices = permissions.assignable_roles(actor)
        if tenant is None:
            # SaaS mode: choose the company; depots assigned later via edit.
            self.fields['company'].queryset = TenantCompany.objects.filter(is_active=True)
            self.fields['company'].required = True
            self.fields.pop('assigned_locations')
        else:
            self.fields.pop('company')
            self.fields['assigned_locations'].queryset = DepotLocation.objects.filter(tenant=tenant)

    def clean_username(self):
        username = self.cleaned_data['username']
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError('A user with that username already exists.')
        return username

    def save(self):
        data = self.cleaned_data
        tenant = self.fixed_tenant or data.get('company')
        user = User.objects.create_user(
            username=data['username'],
            email=data['email'],
            password=data['password'],
            first_name=data['first_name'],
            last_name=data['last_name'],
            phone=data['phone'],
        )
        profile = UserProfile.objects.create(
            user=user, tenant=tenant, role=data['role'], phone=data['phone'])
        if data.get('assigned_locations'):
            profile.assigned_locations.set(data['assigned_locations'])
        return profile


class UserProfileForm(BootstrapFormMixin, forms.ModelForm):
    """Edit a user's company (SaaS mode only), role, depots and active state."""

    class Meta:
        model = UserProfile
        fields = ['tenant', 'role', 'phone', 'assigned_locations', 'is_active']
        widgets = {'assigned_locations': forms.CheckboxSelectMultiple}

    def __init__(self, *args, tenant=None, actor=None, **kwargs):
        super().__init__(*args, **kwargs)
        if actor is not None:
            choices = permissions.assignable_roles(actor)
            # Keep the user's current role visible even if it's above the editor's
            # grant level, so editing other fields doesn't silently downgrade it.
            current = self.instance.role if self.instance.pk else None
            if current and current not in {c[0] for c in choices}:
                label = dict(Role.choices).get(current, current)
                choices = [(current, label)] + choices
            self.fields['role'].choices = choices
        effective = tenant or (self.instance.tenant if self.instance.pk else None)
        self.fields['assigned_locations'].queryset = (
            DepotLocation.objects.filter(tenant=effective) if effective
            else DepotLocation.objects.none())
        if tenant is not None:
            # Tenant mode: company is fixed and hidden.
            self.fields.pop('tenant')
        else:
            self.fields['tenant'].queryset = TenantCompany.objects.filter(is_active=True)
            self.fields['tenant'].label = 'Company'
