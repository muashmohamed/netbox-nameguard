from django import forms

from dcim.models import Device, DeviceRole, Location, Site
from netbox.forms import NetBoxModelForm
from utilities.forms.fields import DynamicModelChoiceField

from .choices import SequencePolicyChoices
from .models import NamingPattern, SiteCode


class SiteCodeForm(NetBoxModelForm):
    site = DynamicModelChoiceField(queryset=Site.objects.all(), required=False)
    location = DynamicModelChoiceField(queryset=Location.objects.all(), required=False)

    class Meta:
        model = SiteCode
        fields = ("site", "location", "code", "comments", "tags")

    def clean(self):
        cleaned = super().clean()
        site, location = cleaned.get("site"), cleaned.get("location")
        if bool(site) == bool(location):
            raise forms.ValidationError("Choose exactly one of Site or Location.")
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
