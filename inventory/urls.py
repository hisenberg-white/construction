from core.crud import crud_urlpatterns

from . import views

app_name = 'inventory'

urlpatterns = [
    *crud_urlpatterns(
        'app/items/materials', 'material',
        list=views.MaterialListView, create=views.MaterialCreateView,
        detail=views.MaterialDetailView, update=views.MaterialUpdateView,
        delete=views.MaterialDeleteView,
    ),
    *crud_urlpatterns(
        'app/items/services', 'service',
        list=views.ServiceListView, create=views.ServiceCreateView,
        detail=views.ServiceDetailView, update=views.ServiceUpdateView,
        delete=views.ServiceDeleteView,
    ),
    *crud_urlpatterns(
        'app/vehicle-types', 'vehicletype',
        list=views.VehicleTypeListView, create=views.VehicleTypeCreateView,
        detail=views.VehicleTypeDetailView, update=views.VehicleTypeUpdateView,
        delete=views.VehicleTypeDeleteView,
    ),
    *crud_urlpatterns(
        'app/vehicles', 'vehicle',
        list=views.VehicleListView, create=views.VehicleCreateView,
        detail=views.VehicleDetailView, update=views.VehicleUpdateView,
        delete=views.VehicleDeleteView,
    ),
    *crud_urlpatterns(
        'app/capacity-rules', 'capacityrule',
        list=views.CapacityRuleListView, create=views.CapacityRuleCreateView,
        detail=views.CapacityRuleDetailView, update=views.CapacityRuleUpdateView,
        delete=views.CapacityRuleDeleteView,
    ),
    # Stock ledger is append-only: ledger-book view + detail + manual adjustment.
    *crud_urlpatterns(
        'app/stock', 'stock',
        list=views.StockLedgerBookView, create=views.StockAdjustmentView,
        detail=views.StockLedgerDetailView,
    ),
]
