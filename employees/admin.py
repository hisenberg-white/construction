from django.contrib import admin

from .models import Employee, EmployeeWorkLog


class WorkLogInline(admin.TabularInline):
    model = EmployeeWorkLog
    extra = 0


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('name', 'tenant', 'depot', 'employment_type',
                    'salary_rate', 'is_active')
    list_filter = ('tenant', 'depot', 'employment_type', 'is_active')
    search_fields = ('name', 'phone')
    inlines = [WorkLogInline]


@admin.register(EmployeeWorkLog)
class EmployeeWorkLogAdmin(admin.ModelAdmin):
    list_display = ('employee', 'tenant', 'work_date', 'work_type',
                    'quantity', 'rate', 'amount')
    list_filter = ('tenant', 'work_type')
    date_hierarchy = 'work_date'
