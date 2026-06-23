from django.contrib import admin

from .models import DepotLocation, TenantCompany, TenantEmailConfig


class DepotInline(admin.TabularInline):
    model = DepotLocation
    extra = 0


@admin.register(TenantCompany)
class TenantCompanyAdmin(admin.ModelAdmin):
    list_display = ('name', 'subscription_status', 'current_plan',
                    'subscription_end', 'is_active')
    list_filter = ('subscription_status', 'is_active')
    search_fields = ('name', 'phone', 'email', 'registration_no')
    inlines = [DepotInline]


@admin.register(DepotLocation)
class DepotLocationAdmin(admin.ModelAdmin):
    list_display = ('name', 'tenant', 'contact_person', 'phone', 'is_active')
    list_filter = ('tenant', 'is_active')
    search_fields = ('name', 'address', 'contact_person')


@admin.register(TenantEmailConfig)
class TenantEmailConfigAdmin(admin.ModelAdmin):
    list_display = ('tenant', 'host', 'port', 'from_email', 'use_tls', 'is_active')
    list_filter = ('is_active', 'use_tls')
    search_fields = ('tenant__name', 'host', 'from_email')
