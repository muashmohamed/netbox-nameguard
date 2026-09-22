from netbox.api.viewsets import NetBoxModelViewSet
from ..models import AtollType, FacilityType, IslandType, SiteCode
from .serializers import AtollTypeSerializer, FacilityTypeSerializer, IslandTypeSerializer, SiteCodeSerializer


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
