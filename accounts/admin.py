from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import User, UserProfile


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = ('username', 'email', 'is_saas_staff', 'is_staff', 'is_active')
    list_filter = DjangoUserAdmin.list_filter + ('is_saas_staff',)
    fieldsets = DjangoUserAdmin.fieldsets + (
        ('SaaS', {'fields': ('is_saas_staff', 'phone')}),
    )


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'tenant', 'role', 'is_active')
    list_filter = ('role', 'tenant', 'is_active')
    search_fields = ('user__username', 'user__email', 'phone')
    filter_horizontal = ('assigned_locations',)
