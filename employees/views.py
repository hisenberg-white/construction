"""Employee and work-log CRUD (SRS FR-12, module 'employees')."""
from core import permissions
from core.crud import (
    CrudCreateView,
    CrudDeleteView,
    CrudDetailView,
    CrudListView,
    CrudUpdateView,
)

from .forms import EmployeeForm, EmployeeWorkLogForm
from .models import Employee, EmployeeWorkLog

MODULE = permissions.EMPLOYEES


class EmployeeListView(CrudListView):
    model = Employee
    permission_module = MODULE
    crud_basename = 'employee'
    list_display = ['name', 'depot', 'employment_type', 'salary_rate', 'is_active']


class EmployeeDetailView(CrudDetailView):
    model = Employee
    permission_module = MODULE
    crud_basename = 'employee'
    list_display = ['name', 'depot', 'phone', 'employment_type', 'salary_rate', 'is_active']


class EmployeeCreateView(CrudCreateView):
    model = Employee
    permission_module = MODULE
    crud_basename = 'employee'
    form_class = EmployeeForm


class EmployeeUpdateView(CrudUpdateView):
    model = Employee
    permission_module = MODULE
    crud_basename = 'employee'
    form_class = EmployeeForm


class EmployeeDeleteView(CrudDeleteView):
    model = Employee
    permission_module = MODULE
    crud_basename = 'employee'
    list_display = ['name']


class WorkLogListView(CrudListView):
    model = EmployeeWorkLog
    permission_module = MODULE
    crud_basename = 'worklog'
    title = 'Employee Work Logs'
    list_display = ['work_date', 'employee', 'work_type', 'quantity', 'rate', 'amount']

    def get_queryset(self):
        return super().get_queryset().select_related('employee')


class WorkLogDetailView(CrudDetailView):
    model = EmployeeWorkLog
    permission_module = MODULE
    crud_basename = 'worklog'
    list_display = ['work_date', 'depot', 'employee', 'work_type', 'quantity',
                    'rate', 'amount']


class WorkLogCreateView(CrudCreateView):
    model = EmployeeWorkLog
    permission_module = MODULE
    crud_basename = 'worklog'
    form_class = EmployeeWorkLogForm


class WorkLogUpdateView(CrudUpdateView):
    model = EmployeeWorkLog
    permission_module = MODULE
    crud_basename = 'worklog'
    form_class = EmployeeWorkLogForm


class WorkLogDeleteView(CrudDeleteView):
    model = EmployeeWorkLog
    permission_module = MODULE
    crud_basename = 'worklog'
    list_display = ['employee', 'work_date']
