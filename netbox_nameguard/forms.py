from django import forms

from dcim.models import Device, DeviceRole, Location, Rack, Site
from netbox.forms import NetBoxModelForm
from utilities.forms.fields import DynamicModelChoiceField

from .choices import SequencePolicyChoices
from .models import AtollType, FacilityType, IslandType, NamingPattern, RackNamingPattern, SiteCode


class AtollTypeForm(NetBoxModelForm):
    class Meta:
        model = AtollType
        fields = ("code", "name", "is_official", "description", "comments", "tags")


class IslandTypeForm(NetBoxModelForm):
    atoll = DynamicModelChoiceField(queryset=AtollType.objects.all())

    class Meta:
        model = IslandType
        fields = ("atoll", "code", "name", "description", "comments", "tags")


class FacilityTypeForm(NetBoxModelForm):
    class Meta:
        model = FacilityType
        fields = ("prefix", "name", "description", "comments", "tags")


class RackNamingPatternForm(NetBoxModelForm):
    class Meta:
        model = RackNamingPattern
        fields = ("name", "template", "seq_width", "seq_policy", "comments", "tags")
        widgets = {
            "seq_policy": forms.RadioSelect(),
        }


class SiteCodeForm(NetBoxModelForm):
    site = DynamicModelChoiceField(queryset=Site.objects.all(), required=False)
    location = DynamicModelChoiceField(queryset=Location.objects.all(), required=False)

    class Meta:
        model = SiteCode
        fields = ("site", "location", "location_kind", "code", "comments", "tags")
        widgets = {
            "location_kind": forms.RadioSelect(),
        }

    class Media:
        js = ("netbox_nameguard/sitecode_form.js",)

    def clean(self):
        super().clean()
        cleaned = self.cleaned_data
        site, location = cleaned.get("site"), cleaned.get("location")
        if bool(site) == bool(location):
            raise forms.ValidationError("Choose exactly one of Site or Location.")
        if location and not cleaned.get("location_kind"):
            raise forms.ValidationError({"location_kind": "Required when targeting a Location: Facility, Building, Floor, or Other?"})
        return cleaned


class NamingPatternForm(NetBoxModelForm):
    class Meta:
        model = NamingPattern
        fields = ("device_role", "template", "seq_width", "seq_policy", "comments", "tags")
        widgets = {
            "seq_policy": forms.RadioSelect(),
        }


class ComplianceFilterForm(forms.Form):
    site = DynamicModelChoiceField(queryset=Site.objects.all(), required=False)
    device_role = DynamicModelChoiceField(queryset=DeviceRole.objects.all(), required=False)
    status = forms.ChoiceField(
        choices=(("", "All"), ("compliant", "Compliant"), ("noncompliant", "Non-compliant"),
                 ("unconfigured", "Unconfigured"), ("collision", "Collision")),
        required=False,
    )


class RackComplianceFilterForm(forms.Form):
    """Racks have no Role, so this is a simpler filter than ComplianceFilterForm."""
    site = DynamicModelChoiceField(queryset=Site.objects.all(), required=False)
    status = forms.ChoiceField(
        choices=(("", "All"), ("compliant", "Compliant"), ("noncompliant", "Non-compliant"),
                 ("unconfigured", "Unconfigured"), ("collision", "Collision")),
        required=False,
    )


class BulkRenameConfirmForm(forms.Form):
    """
    Shown after the dry-run preview. Ticking devices here and submitting is
    the only way an actual rename is ever applied.
    """
    pk = forms.ModelMultipleChoiceField(
        queryset=Device.objects.all(),
        widget=forms.MultipleHiddenInput,
    )
    confirm = forms.BooleanField(
        required=True,
        label="I have reviewed the proposed names above and want to apply them.",
    )


class RackBulkRenameConfirmForm(forms.Form):
    """
    Same as BulkRenameConfirmForm but validates pk against Rack, not Device -
    keeping these separate prevents a Rack pk ever being mistakenly matched
    against a Device row that happens to share the same numeric id.
    """
    pk = forms.ModelMultipleChoiceField(
        queryset=Rack.objects.all(),
        widget=forms.MultipleHiddenInput,
    )
    confirm = forms.BooleanField(
        required=True,
        label="I have reviewed the proposed names above and want to apply them.",
    )
