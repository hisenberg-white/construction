from django.contrib import admin

from .models import Expense, ExpenseCategory


@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'tenant', 'is_active')
    list_filter = ('tenant', 'is_active')
    search_fields = ('name',)


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('id', 'tenant', 'depot', 'category', 'amount',
                    'payment_method', 'expense_date', 'status')
    list_filter = ('tenant', 'depot', 'category', 'payment_method', 'status')
    date_hierarchy = 'expense_date'
