from django.urls import path

from core.crud import crud_urlpatterns

from . import views

app_name = 'sales'

urlpatterns = [
    *crud_urlpatterns(
        'app/sales/invoices', 'invoice',
        list=views.InvoiceListView, create=views.InvoiceCreateView,
        detail=views.InvoiceDetailView, update=views.InvoiceUpdateView,
        cancel=views.InvoiceCancelView,
    ),
    path('app/sales/invoices/<int:pk>/deliver/',
         views.DeliveryLogCreateView.as_view(), name='invoice_deliver'),
    path('app/sales/invoices/<int:pk>/pdf/',
         views.InvoicePDFView.as_view(), name='invoice_pdf'),
    path('app/sales/invoices/<int:pk>/email/',
         views.InvoiceEmailView.as_view(), name='invoice_email'),
    path('app/sales/invoices/<int:pk>/record-payment/',
         views.InvoicePaymentView.as_view(), name='invoice_payment'),
    # Public (no-login) bill opened via the QR's signed token.
    path('bill/invoice/<str:token>/', views.InvoicePublicView.as_view(), name='invoice_public'),
]
