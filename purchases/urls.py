from django.urls import path

from core.crud import crud_urlpatterns

from . import views

app_name = 'purchases'

urlpatterns = [
    path('app/purchases/<int:pk>/pdf/', views.PurchasePDFView.as_view(), name='purchase_pdf'),
    path('app/purchases/<int:pk>/record-payment/',
         views.PurchasePaymentView.as_view(), name='purchase_payment'),
    path('bill/purchase/<str:token>/', views.PurchasePublicView.as_view(), name='purchase_public'),
    *crud_urlpatterns(
        'app/purchases', 'purchase',
        list=views.PurchaseListView, create=views.PurchaseCreateView,
        detail=views.PurchaseDetailView, update=views.PurchaseUpdateView,
        cancel=views.PurchaseCancelView,
    ),
    *crud_urlpatterns(
        'app/trips', 'trip',
        list=views.TripListView, create=views.TripCreateView,
        detail=views.TripDetailView, update=views.TripUpdateView,
        cancel=views.TripCancelView,
    ),
]
