from core.crud import crud_urlpatterns

from . import views

app_name = 'ledger'

urlpatterns = [
    *crud_urlpatterns(
        'app/payments', 'payment',
        list=views.PaymentListView, create=views.PaymentCreateView,
        detail=views.PaymentDetailView, update=views.PaymentUpdateView,
        cancel=views.PaymentCancelView,
    ),
    *crud_urlpatterns(
        'app/reports/ledger', 'ledgerentry',
        list=views.LedgerPaperView, detail=views.LedgerEntryDetailView,
    ),
]
