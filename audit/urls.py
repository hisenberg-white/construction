from core.crud import crud_urlpatterns

from . import views

app_name = 'audit'

urlpatterns = [
    *crud_urlpatterns(
        'app/audit-log', 'auditlog',
        list=views.AuditLogListView, detail=views.AuditLogDetailView,
    ),
]
