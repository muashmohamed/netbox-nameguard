import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse

from netbox.models import NetBoxModel

from .choices import LocationKindChoices, SequencePolicyChoices


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
    location_kind = models.CharField(
        max_length=20,
        choices=LocationKindChoices,
        blank=True,
        help_text="Required when targeting a Location: is this a Building, a Floor, or Other?",
    )
    code = models.CharField(
        max_length=5,
        help_text=(
            "4-character code (letters and numbers), e.g. HOBB, KKSH, or HML1. "
            "A 5th character is allowed for special cases that need it, e.g. BLDGA. "
            "Must be unique within its owning Site — the same code (e.g. PH for "
            "Powerhouse) can be reused at a different Site."
        ),
    )
    owning_site = models.ForeignKey(
        to="dcim.Site",
        on_delete=models.CASCADE,
        related_name="nameguard_owned_codes",
        editable=False,
        null=True,
        help_text="Auto-computed: this SiteCode's own Site, or its Location's Site.",
    )
    comments = models.TextField(blank=True)

    class Meta:
        ordering = ("code",)
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(site__isnull=False, location__isnull=True)
                    | models.Q(site__isnull=True, location__isnull=False)
                ),
                name="nameguard_sitecode_exactly_one_target",
            ),
            models.UniqueConstraint(fields=["site"], name="nameguard_unique_site"),
            models.UniqueConstraint(fields=["location"], name="nameguard_unique_location"),
            models.UniqueConstraint(fields=["owning_site", "code"], name="nameguard_unique_code_per_owning_site"),
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
        if self.location and not self.location_kind:
            raise ValidationError({"location_kind": "Required when targeting a Location: is this a Building, Floor, or Other?"})
        if self.site and self.location_kind:
            self.location_kind = ""
        if self.code:
            self.code = self.code.strip().upper()
            if not (4 <= len(self.code) <= 5) or not self.code.isalnum():
                raise ValidationError({"code": "Code must be 4 characters (5 allowed for special cases), letters and numbers only."})

    def save(self, *args, **kwargs):
        # Always keep owning_site correct, even on programmatic saves that
        # might skip full_clean() (e.g. some API/script paths).
        if self.site_id:
            self.owning_site_id = self.site_id
        elif self.location_id:
            self.owning_site_id = self.location.site_id
        super().save(*args, **kwargs)


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
            if "{SEQ}" not in self.template:
                raise ValidationError({"template": "Template must include the {SEQ} token."})
            if "{SITE}" not in self.template and "{LOCATION}" not in self.template:
                raise ValidationError({"template": "Template must include {SITE} and/or {LOCATION}."})


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
