from django.contrib.auth import views as auth_views
from django.urls import path

from core.crud import crud_urlpatterns

from . import views

app_name = 'accounts'

urlpatterns = [
    path('accounts/login/', auth_views.LoginView.as_view(
        template_name='accounts/login.html'), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('accounts/no-company/', views.NoTenantView.as_view(), name='no_tenant'),

    # Users & roles management (SRS 12.3 /app/settings/users-roles/).
    *crud_urlpatterns(
        'app/settings/users-roles', 'userprofile',
        list=views.UserProfileListView,
        create=views.UserProfileCreateView,
        detail=views.UserProfileDetailView,
        update=views.UserProfileUpdateView,
        delete=views.UserProfileDeleteView,
    ),
]
