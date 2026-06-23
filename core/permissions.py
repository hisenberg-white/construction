"""Role-based access control derived from the SRS permission matrix (section 4.2).

Permissions are expressed as (module, action) pairs. Actions use single
letters: ``c`` create, ``r`` read, ``u`` update, ``d`` delete. A role grants a
set of actions per module; deletion of financial records is deliberately
withheld in favour of cancel/reverse (SRS FR-17).
"""

# --- Modules -----------------------------------------------------------------
SAAS = 'saas'                       # Clients, plans, subscriptions (SaaS owner)
COMPANY_SETTINGS = 'company_settings'
USERS_ROLES = 'users_roles'
ITEMS = 'items'                     # Material/service/vehicle master data
PARTIES = 'parties'                 # Customers & suppliers
PURCHASES = 'purchases'
SALES = 'sales'
PAYMENTS_LEDGER = 'payments_ledger'
STOCK = 'stock'
EXPENSES = 'expenses'
EMPLOYEES = 'employees'
REPORTS = 'reports'
AUDIT = 'audit'

MODULES = [
    SAAS, COMPANY_SETTINGS, USERS_ROLES, ITEMS, PARTIES, PURCHASES, SALES,
    PAYMENTS_LEDGER, STOCK, EXPENSES, EMPLOYEES, REPORTS, AUDIT,
]

# --- Roles (mirror accounts.Role values) ------------------------------------
SAAS_SUPER_ADMIN = 'saas_super_admin'
SAAS_STAFF = 'saas_staff'
CLIENT_OWNER = 'client_owner'
CLIENT_ADMIN = 'client_admin'
DEPOT_ADMIN = 'depot_admin'
BILLING_USER = 'billing_user'
STOCK_USER = 'stock_user'
VIEWER = 'viewer'
STAFF = 'staff'


def _a(letters):
    return frozenset(letters)


# Permission matrix: MATRIX[module][role] -> set of allowed action letters.
# Transcribed from SRS section 4.2; financial modules grant CRUD without a
# hard "d" where the SRS mandates cancel/reverse — cancellation is gated on "u".
MATRIX = {
    SAAS: {
        SAAS_SUPER_ADMIN: _a('crud'),
        SAAS_STAFF: _a('r'),
    },
    COMPANY_SETTINGS: {
        SAAS_SUPER_ADMIN: _a('ru'),
        CLIENT_OWNER: _a('crud'),
        CLIENT_ADMIN: _a('r'),
        DEPOT_ADMIN: _a('r'),
        VIEWER: _a('r'),
    },
    USERS_ROLES: {
        # SaaS owner provisions client companies and their users (SRS 8.1
        # "create clients … support tenants"), so full CRUD here.
        SAAS_SUPER_ADMIN: _a('crud'),
        CLIENT_OWNER: _a('crud'),
        # Client Admin/Accountant can manage staff users below their rank
        # (role choices are hierarchy-limited via assignable_roles()).
        CLIENT_ADMIN: _a('cru'),
        DEPOT_ADMIN: _a('r'),  # "Limited" in the SRS
    },
    ITEMS: {
        SAAS_SUPER_ADMIN: _a('r'),
        CLIENT_OWNER: _a('crud'),
        CLIENT_ADMIN: _a('crud'),
        DEPOT_ADMIN: _a('crud'),
        STOCK_USER: _a('r'),
        BILLING_USER: _a('r'),
        STAFF: _a('r'),
        VIEWER: _a('r'),
    },
    PARTIES: {
        SAAS_SUPER_ADMIN: _a('r'),
        CLIENT_OWNER: _a('crud'),
        CLIENT_ADMIN: _a('crud'),
        DEPOT_ADMIN: _a('crud'),
        BILLING_USER: _a('cru'),
        STOCK_USER: _a('r'),
        STAFF: _a('cr'),
        VIEWER: _a('r'),
    },
    PURCHASES: {
        SAAS_SUPER_ADMIN: _a('r'),
        CLIENT_OWNER: _a('crud'),
        CLIENT_ADMIN: _a('crud'),
        DEPOT_ADMIN: _a('crud'),
        BILLING_USER: _a('r'),
        STOCK_USER: _a('crud'),
        STAFF: _a('cr'),
        VIEWER: _a('r'),
    },
    SALES: {
        SAAS_SUPER_ADMIN: _a('r'),
        CLIENT_OWNER: _a('crud'),
        CLIENT_ADMIN: _a('crud'),
        DEPOT_ADMIN: _a('crud'),
        BILLING_USER: _a('crud'),
        STOCK_USER: _a('r'),
        STAFF: _a('cr'),
        VIEWER: _a('r'),
    },
    PAYMENTS_LEDGER: {
        SAAS_SUPER_ADMIN: _a('r'),
        CLIENT_OWNER: _a('crud'),
        CLIENT_ADMIN: _a('crud'),
        DEPOT_ADMIN: _a('crud'),
        BILLING_USER: _a('cr'),
        STOCK_USER: _a('r'),
        VIEWER: _a('r'),
    },
    STOCK: {
        SAAS_SUPER_ADMIN: _a('r'),
        CLIENT_OWNER: _a('crud'),
        CLIENT_ADMIN: _a('crud'),
        DEPOT_ADMIN: _a('crud'),
        BILLING_USER: _a('r'),
        STOCK_USER: _a('crud'),
        STAFF: _a('cr'),
        VIEWER: _a('r'),
    },
    EXPENSES: {
        SAAS_SUPER_ADMIN: _a('r'),
        CLIENT_OWNER: _a('crud'),
        CLIENT_ADMIN: _a('crud'),
        DEPOT_ADMIN: _a('crud'),
        BILLING_USER: _a('r'),  # "Limited"
        STOCK_USER: _a('cru'),
        STAFF: _a('cr'),
        VIEWER: _a('r'),
    },
    EMPLOYEES: {
        SAAS_SUPER_ADMIN: _a('r'),
        CLIENT_OWNER: _a('crud'),
        CLIENT_ADMIN: _a('crud'),
        DEPOT_ADMIN: _a('crud'),
        STAFF: _a('cr'),
        VIEWER: _a('r'),
    },
    REPORTS: {
        SAAS_SUPER_ADMIN: _a('r'),
        SAAS_STAFF: _a('r'),
        CLIENT_OWNER: _a('r'),
        CLIENT_ADMIN: _a('r'),
        DEPOT_ADMIN: _a('r'),
        BILLING_USER: _a('r'),
        STOCK_USER: _a('r'),
        VIEWER: _a('r'),
    },
    AUDIT: {
        SAAS_SUPER_ADMIN: _a('r'),
        CLIENT_OWNER: _a('r'),
        CLIENT_ADMIN: _a('r'),
    },
}


# Role hierarchy — a user may only assign roles strictly below their own rank
# (SaaS roles are never offered through the tenant UI). Higher = more power.
ROLE_RANK = {
    SAAS_SUPER_ADMIN: 100,
    SAAS_STAFF: 90,
    CLIENT_OWNER: 80,
    CLIENT_ADMIN: 70,
    DEPOT_ADMIN: 50,
    BILLING_USER: 40,
    STOCK_USER: 40,
    VIEWER: 10,
    STAFF: 30,
}
SAAS_ROLES = {SAAS_SUPER_ADMIN, SAAS_STAFF}


def assignable_roles(user):
    """Roles ``user`` is allowed to grant when creating/editing users.

    Simplified 3-tier model: superuser/saas_super_admin can assign any role;
    client_owner can assign STAFF; client_admin can assign STAFF; others nothing.
    Returns a list of (value, label).
    """
    from accounts.models import Role
    if getattr(user, 'is_superuser', False):
        return list(Role.choices)
    role = get_role(user)
    if role == SAAS_SUPER_ADMIN:
        return list(Role.choices)
    if role in (CLIENT_OWNER, CLIENT_ADMIN):
        return [(v, l) for v, l in Role.choices if v == STAFF]
    return []


def get_role(user):
    """Return the effective role code for ``user`` (or ``None``)."""
    if not getattr(user, 'is_authenticated', False):
        return None
    if getattr(user, 'is_saas_staff', False) or user.is_superuser:
        return SAAS_SUPER_ADMIN
    profile = getattr(user, 'profile', None)
    return profile.role if profile else None


def has_perm(user, module, action):
    """Whether ``user`` may perform ``action`` (c/r/u/d) on ``module``."""
    if getattr(user, 'is_superuser', False):
        return True
    role = get_role(user)
    if role is None:
        return False
    return action in MATRIX.get(module, {}).get(role, frozenset())


def readable_modules(user):
    """Set of modules the user can at least read — used to build navigation."""
    return {m for m in MODULES if has_perm(user, m, 'r')}
