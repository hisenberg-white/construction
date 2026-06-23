from django import forms

from core.forms import DateInput, TenantModelForm

from .models import Expense, ExpenseCategory


class ExpenseCategoryForm(TenantModelForm):
    class Meta:
        model = ExpenseCategory
        fields = ['name', 'is_active']


class ExpenseForm(TenantModelForm):
    class Meta:
        model = Expense
        fields = ['expense_date', 'depot', 'category', 'amount', 'payment_method',
                  'vehicle', 'employee', 'supplier', 'notes', 'reference_image']
        widgets = {'expense_date': DateInput(), 'notes': forms.Textarea(attrs={'rows': 2})}
