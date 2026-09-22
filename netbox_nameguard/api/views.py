"""
netbox_nameguard/api/views.py
"""

from netbox.api.viewsets import NetBoxModelViewSet
from ..models import SiteCode
from .serializers import SiteCodeSerializer


class SiteCodeViewSet(NetBoxModelViewSet):
    queryset = SiteCode.objects.all()
    serializer_class = SiteCodeSerializer
