"""
netbox_nameguard/api/urls.py
"""

from netbox.api.routers import NetBoxRouter
from . import views

app_name = 'netbox_nameguard'

router = NetBoxRouter()
router.register('site-codes', views.SiteCodeViewSet)

urlpatterns = router.urls
