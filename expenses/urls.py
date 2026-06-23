from django.urls import path

from core.crud import crud_urlpatterns

from . import views

app_name = 'expenses'

urlpatterns = [
    path('app/expense-categories/quick-add/',
         views.category_quick_create, name='category_quick_create'),
    *crud_urlpatterns(
        'app/expense-categories', 'expensecategory',
        list=views.CategoryListView, create=views.CategoryCreateView,
        detail=views.CategoryDetailView, update=views.CategoryUpdateView,
        delete=views.CategoryDeleteView,
    ),
    *crud_urlpatterns(
        'app/expenses', 'expense',
        list=views.ExpenseListView, create=views.ExpenseCreateView,
        detail=views.ExpenseDetailView, update=views.ExpenseUpdateView,
        cancel=views.ExpenseCancelView,
    ),
]
