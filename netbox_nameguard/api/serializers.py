"""
netbox_nameguard/api/serializers.py

NetBox's generic bulk views (delete, edit) look up a REST API serializer
per model to render each object's display name in the confirmation list -
even if you never call the REST API directly. Without this file, bulk
actions on SiteCode raise SerializerNotFound.

fields = '__all__' so this works regardless of SiteCode's actual field
names - no need to hand-list them.
"""

from netbox.api.serializers import NetBoxModelSerializer
from ..models import SiteCode


class SiteCodeSerializer(NetBoxModelSerializer):
    class Meta:
        model = SiteCode
        fields = '__all__'
