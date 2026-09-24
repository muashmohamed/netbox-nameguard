"""
netbox_nameguard/api/views.py
"""

from netbox.api.viewsets import NetBoxModelViewSet
from ..models import AtollType, FacilityType, IslandType, RackNamingPattern, SiteCode
from .serializers import (
    AtollTypeSerializer, FacilityTypeSerializer, IslandTypeSerializer,
    RackNamingPatternSerializer, SiteCodeSerializer,
)


class AtollTypeViewSet(NetBoxModelViewSet):
    queryset = AtollType.objects.all()
    serializer_class = AtollTypeSerializer


class IslandTypeViewSet(NetBoxModelViewSet):
    queryset = IslandType.objects.all()
    serializer_class = IslandTypeSerializer


class FacilityTypeViewSet(NetBoxModelViewSet):
    queryset = FacilityType.objects.all()
    serializer_class = FacilityTypeSerializer


class SiteCodeViewSet(NetBoxModelViewSet):
    queryset = SiteCode.objects.all()
    serializer_class = SiteCodeSerializer


class RackNamingPatternViewSet(NetBoxModelViewSet):
    queryset = RackNamingPattern.objects.all()
    serializer_class = RackNamingPatternSerializer
