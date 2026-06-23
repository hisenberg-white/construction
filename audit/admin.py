from django.contrib import admin

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'tenant', 'user', 'action',
                    'model_name', 'object_id')
    list_filter = ('tenant', 'action', 'model_name')
    search_fields = ('object_id', 'user__username')
    date_hierarchy = 'created_at'
    readonly_fields = ('tenant', 'user', 'action', 'model_name', 'object_id',
                       'before_json', 'after_json', 'ip_address',
                       'created_at', 'updated_at')

    def has_add_permission(self, request):
        return False  # Audit logs are written by the system, never by hand.
