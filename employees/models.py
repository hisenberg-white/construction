"""Employees, work logs and payroll basis (SRS FR-12)."""
from django.db import models

from core.models import TenantOwnedModel


class Employee(TenantOwnedModel):
    """An employee paid monthly, per-trip, per-load, daily or mixed (SRS FR-12)."""

    class EmploymentType(models.TextChoices):
        MONTHLY = 'monthly', 'Monthly Salary'
        PER_TRIP = 'per_trip', 'Per Trip'
        PER_LOAD = 'per_load', 'Per Load / Unload'
        DAILY = 'daily', 'Temporary Daily Wage'
        MIXED = 'mixed', 'Mixed'

    depot = models.ForeignKey(
        'tenants.DepotLocation', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='employees',
    )
    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=30, blank=True)
    employment_type = models.CharField(
        max_length=12, choices=EmploymentType.choices, default=EmploymentType.MONTHLY
    )
    salary_rate = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        help_text='Monthly salary, or rate per trip/load/day per employment type.',
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class EmployeeWorkLog(TenantOwnedModel):
    """Work performed by an employee, used to compute payable amount (FR-12)."""

    class WorkType(models.TextChoices):
        TRIP = 'trip', 'Trip'
        LOAD = 'load', 'Load / Unload'
        DAY = 'day', 'Day'
        HOURS = 'hours', 'Hours'

    depot = models.ForeignKey(
        'tenants.DepotLocation', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='work_logs',
    )
    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name='work_logs'
    )
    work_date = models.DateField()
    work_type = models.CharField(max_length=10, choices=WorkType.choices)
    # Optional links to the trip/invoice the work relates to.
    reference_type = models.CharField(max_length=40, blank=True)
    reference_id = models.PositiveBigIntegerField(null=True, blank=True)
    quantity = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        help_text='Number of trips/loads/days/hours.',
    )
    rate = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    class Meta:
        ordering = ['-work_date', '-id']
        indexes = [models.Index(fields=['tenant', 'employee', 'work_date'])]

    def save(self, *args, **kwargs):
        self.amount = (self.quantity or 0) * (self.rate or 0)
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.employee} — {self.get_work_type_display()} ({self.work_date})'
