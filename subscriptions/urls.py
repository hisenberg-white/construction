from core.crud import crud_urlpatterns

from . import views

app_name = 'subscriptions'

urlpatterns = [
    *crud_urlpatterns(
        'saas-admin/plans', 'plan',
        list=views.PlanListView, create=views.PlanCreateView,
        detail=views.PlanDetailView, update=views.PlanUpdateView,
        delete=views.PlanDeleteView,
    ),
    *crud_urlpatterns(
        'saas-admin/subscriptions', 'subscription',
        list=views.SubscriptionListView, create=views.SubscriptionCreateView,
        detail=views.SubscriptionDetailView, update=views.SubscriptionUpdateView,
        delete=views.SubscriptionDeleteView,
    ),
    *crud_urlpatterns(
        'saas-admin/usage', 'usage',
        list=views.UsageListView, detail=views.UsageDetailView,
    ),
]
