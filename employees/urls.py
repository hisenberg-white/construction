from core.crud import crud_urlpatterns

from . import views

app_name = 'employees'

urlpatterns = [
    *crud_urlpatterns(
        'app/employees', 'employee',
        list=views.EmployeeListView, create=views.EmployeeCreateView,
        detail=views.EmployeeDetailView, update=views.EmployeeUpdateView,
        delete=views.EmployeeDeleteView,
    ),
    *crud_urlpatterns(
        'app/work-logs', 'worklog',
        list=views.WorkLogListView, create=views.WorkLogCreateView,
        detail=views.WorkLogDetailView, update=views.WorkLogUpdateView,
        delete=views.WorkLogDeleteView,
    ),
]
