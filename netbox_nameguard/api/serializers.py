"""
netbox_nameguard/api/serializers.py
"""

from netbox.api.serializers import NetBoxModelSerializer
from ..models import AtollType, FacilityType, IslandType, RackNamingPattern, SiteCode


class AtollTypeSerializer(NetBoxModelSerializer):
    class Meta:
        model = AtollType
        fields = '__all__'


class IslandTypeSerializer(NetBoxModelSerializer):
    class Meta:
        model = IslandType
        fields = '__all__'


class FacilityTypeSerializer(NetBoxModelSerializer):
    class Meta:
        model = FacilityType
        fields = '__all__'


class SiteCodeSerializer(NetBoxModelSerializer):
    class Meta:
        model = SiteCode
        fields = '__all__'


class RackNamingPatternSerializer(NetBoxModelSerializer):
    class Meta:
        model = RackNamingPattern
        fields = '__all__'
