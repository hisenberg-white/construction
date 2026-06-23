"""Expense category and expense CRUD (SRS FR-13, module 'expenses')."""
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from core import permissions
from core.crud import (
    CrudCancelView,
    CrudCreateView,
    CrudDeleteView,
    CrudDetailView,
    CrudListView,
    CrudUpdateView,
)
from ledger.services import LedgerService

from .forms import ExpenseCategoryForm, ExpenseForm
from .models import Expense, ExpenseCategory

MODULE = permissions.EXPENSES


@login_required
@require_POST
def category_quick_create(request):
    """Inline AJAX create of an expense category (e.g. Petrol) from entry forms."""
    if not permissions.has_perm(request.user, MODULE, 'c'):
        return JsonResponse({'ok': False, 'error': 'You are not allowed to add this.'}, status=403)
    tenant = getattr(request, 'tenant', None)
    if tenant is None:
        return JsonResponse({'ok': False, 'error': 'No company is linked to your account.'}, status=400)
    name = (request.POST.get('name') or '').strip()
    if not name:
        return JsonResponse({'ok': False, 'error': 'Name is required.'}, status=400)
    obj, _ = ExpenseCategory.objects.get_or_create(
        tenant=tenant, name=name,
        defaults={'created_by': request.user, 'updated_by': request.user})
    return JsonResponse({'ok': True, 'id': obj.pk, 'label': str(obj)})


def _post_expense_effects(expense, actor, *, reverse=False):
    """Post (or reverse) the expense to the company Expense ledger (SRS FR-14)."""
    amount = expense.amount or 0
    if amount <= 0:
        return
    LedgerService.post(
        tenant=expense.tenant, account_type='expense', account_id=None,
        entry_date=expense.expense_date,
        description=('Reversal of ' if reverse else '') + f'{expense.category} expense #{expense.pk}',
        debit=0 if reverse else amount, credit=amount if reverse else 0,
        reference_type='expense', reference_id=expense.pk,
        depot=expense.depot, actor=actor,
    )


# --- Categories (simple master, hard delete allowed) -------------------------
class CategoryListView(CrudListView):
    model = ExpenseCategory
    permission_module = MODULE
    crud_basename = 'expensecategory'
    title = 'Expense Categories'
    list_display = ['name', 'is_active']


class CategoryDetailView(CrudDetailView):
    model = ExpenseCategory
    permission_module = MODULE
    crud_basename = 'expensecategory'
    list_display = ['name', 'is_active']


class CategoryCreateView(CrudCreateView):
    model = ExpenseCategory
    permission_module = MODULE
    crud_basename = 'expensecategory'
    form_class = ExpenseCategoryForm


class CategoryUpdateView(CrudUpdateView):
    model = ExpenseCategory
    permission_module = MODULE
    crud_basename = 'expensecategory'
    form_class = ExpenseCategoryForm


class CategoryDeleteView(CrudDeleteView):
    model = ExpenseCategory
    permission_module = MODULE
    crud_basename = 'expensecategory'
    list_display = ['name']


# --- Expenses (financial, cancellable) ---------------------------------------
class ExpenseListView(CrudListView):
    model = Expense
    permission_module = MODULE
    crud_basename = 'expense'
    delete_action = 'cancel'
    list_display = ['expense_date', 'category', 'depot', 'vehicle', 'amount',
                    'payment_method', 'status']

    def get_queryset(self):
        return super().get_queryset().select_related('category', 'depot', 'vehicle')


class ExpenseDetailView(CrudDetailView):
    model = Expense
    permission_module = MODULE
    crud_basename = 'expense'
    delete_action = 'cancel'
    list_display = ['expense_date', 'depot', 'category', 'amount', 'payment_method',
                    'vehicle', 'employee', 'supplier', 'status', 'notes']


class ExpenseCreateView(CrudCreateView):
    model = Expense
    permission_module = MODULE
    crud_basename = 'expense'
    form_class = ExpenseForm

    @transaction.atomic
    def form_valid(self, form):
        response = super().form_valid(form)
        _post_expense_effects(self.object, self.request.user)
        return response


class ExpenseUpdateView(CrudUpdateView):
    model = Expense
    permission_module = MODULE
    crud_basename = 'expense'
    form_class = ExpenseForm


class ExpenseCancelView(CrudCancelView):
    model = Expense
    permission_module = MODULE
    crud_basename = 'expense'

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        obj = self.get_object()
        if not obj.is_cancelled:
            _post_expense_effects(obj, request.user, reverse=True)
        return super().post(request, *args, **kwargs)
