from netbox.api.routers import NetBoxRouter
from . import views

app_name = 'netbox_nameguard'

router = NetBoxRouter()
router.register('atoll-types', views.AtollTypeViewSet)
router.register('island-types', views.IslandTypeViewSet)
router.register('facility-types', views.FacilityTypeViewSet)
router.register('site-codes', views.SiteCodeViewSet)

urlpatterns = router.urls
