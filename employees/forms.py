from core.forms import DateInput, TenantModelForm

from .models import Employee, EmployeeWorkLog


class EmployeeForm(TenantModelForm):
    class Meta:
        model = Employee
        fields = ['name', 'depot', 'phone', 'employment_type', 'salary_rate', 'is_active']


class EmployeeWorkLogForm(TenantModelForm):
    class Meta:
        model = EmployeeWorkLog
        fields = ['work_date', 'depot', 'employee', 'work_type', 'quantity', 'rate']
        widgets = {'work_date': DateInput()}
