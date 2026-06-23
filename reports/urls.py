from django.urls import path

from . import views

app_name = 'reports'

urlpatterns = [
    path('app/dashboard/', views.DashboardView.as_view(), name='dashboard'),
    path('app/reports/vehicle-analytics/', views.VehicleAnalyticsView.as_view(), name='vehicle_analytics'),
]
