import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse

from netbox.models import NetBoxModel

from .choices import SequencePolicyChoices


class SiteCode(NetBoxModel):
    """
    A single registry mapping exactly one of {Site, Location} to a fixed,
    reusable 4-letter code (e.g. "Head Office Building" -> HOBB).
    """
    site = models.ForeignKey(
        to="dcim.Site",
        on_delete=models.CASCADE,
        related_name="nameguard_codes",
        blank=True,
        null=True,
    )
    location = models.ForeignKey(
        to="dcim.Location",
        on_delete=models.CASCADE,
        related_name="nameguard_codes",
        blank=True,
        null=True,
    )
    code = models.CharField(
        max_length=4,
        unique=True,
        help_text="Fixed 4-letter code, e.g. HOBB or KKSH.",
    )
    comments = models.TextField(blank=True)

    class Meta:
        ordering = ("code",)
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(site__isnull=False, location__isnull=True)
                    | models.Q(site__isnull=True, location__isnull=False)
                ),
                name="nameguard_sitecode_exactly_one_target",
            ),
            models.UniqueConstraint(fields=["site"], name="nameguard_unique_site"),
            models.UniqueConstraint(fields=["location"], name="nameguard_unique_location"),
        ]
        verbose_name = "Site Code"
        verbose_name_plural = "Site Codes"

    def __str__(self):
        return f"{self.target} → {self.code}"

    def get_absolute_url(self):
        return reverse("plugins:netbox_nameguard:sitecode", args=[self.pk])

    @property
    def target(self):
        return self.site or self.location

    def clean(self):
        super().clean()
        if bool(self.site) == bool(self.location):
            raise ValidationError("Set exactly one of Site or Location, not both/neither.")
        if self.code:
            self.code = self.code.strip().upper()
            if len(self.code) != 4 or not self.code.isalpha():
                raise ValidationError({"code": "Code must be exactly 4 letters."})


class NamingPattern(NetBoxModel):
    """
    A configurable naming template for a given Device Role, e.g.
    Camera -> "{SITE}-CAM-{SEQ}".
    """
    device_role = models.OneToOneField(
        to="dcim.DeviceRole",
        on_delete=models.CASCADE,
        related_name="nameguard_pattern",
    )
    template = models.CharField(
        max_length=100,
        help_text="Use {SITE} and {SEQ} tokens, e.g. {SITE}-CAM-{SEQ}",
    )
    seq_width = models.PositiveSmallIntegerField(
        default=3,
        help_text="Zero-padded width of the sequence number, e.g. 3 -> 001",
    )
    seq_policy = models.CharField(
        max_length=30,
        choices=SequencePolicyChoices,
        default=SequencePolicyChoices.GAP_AWARE,
    )
    comments = models.TextField(blank=True)

    class Meta:
        ordering = ("device_role__name",)
        verbose_name = "Naming Pattern"
        verbose_name_plural = "Naming Patterns"

    def __str__(self):
        return f"{self.device_role}: {self.template}"

    def get_absolute_url(self):
        return reverse("plugins:netbox_nameguard:namingpattern", args=[self.pk])

    def clean(self):
        super().clean()
        if self.template:
            if "{SITE}" not in self.template:
                raise ValidationError({"template": "Template must include the {SITE} token."})
            if "{SEQ}" not in self.template:
                raise ValidationError({"template": "Template must include the {SEQ} token."})


class RenameLog(NetBoxModel):
    """
    Permanent audit record of every rename NameGuard has applied. Kept even
    if the device is later deleted, so history is never lost.
    """
    device = models.ForeignKey(
        to="dcim.Device",
        on_delete=models.SET_NULL,
        related_name="nameguard_rename_logs",
        blank=True,
        null=True,
    )
    device_name_snapshot = models.CharField(
        max_length=64,
        help_text="Device name at the time of this log entry (survives device deletion).",
    )
    old_name = models.CharField(max_length=64, blank=True)
    new_name = models.CharField(max_length=64)
    batch_id = models.UUIDField(default=uuid.uuid4, editable=False, db_index=True)
    applied_by = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="+",
        blank=True,
        null=True,
    )
    applied_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-applied_at",)
        verbose_name = "Rename Log"
        verbose_name_plural = "Rename Logs"

    def __str__(self):
        return f"{self.old_name} → {self.new_name}"

    def get_absolute_url(self):
        return reverse("plugins:netbox_nameguard:renamelog", args=[self.pk])
