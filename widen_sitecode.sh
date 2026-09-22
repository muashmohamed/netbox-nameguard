#!/usr/bin/env bash
set -e

cd ~/netbox-nameguard

cat > netbox_nameguard/models.py << 'PYEOF'
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
    reusable code.

    Site-level codes carry the full Atoll-Island-Facility hierarchy,
    hyphen-separated (e.g. "K-KAA-PH1"), and feed the {SITE} token in a
    NamingPattern's template. Location-level codes are scoped to a
    single Building ("B1"), Floor ("GF", "F1"), or Other zone, tagged
    via location_kind.
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
        max_length=20,
        help_text=(
            "Site-level codes carry the full hierarchy, hyphen-separated, "
            "e.g. K-KAA-PH1 (Atoll-Island-Facility). Location-level codes "
            "are scoped to their kind: Building (e.g. B1, up to 4 chars), "
            "Floor (e.g. GF, F1, up to 3 chars), Other (up to 6 chars). "
            "Letters, numbers, and hyphens only. Must be unique within its "
            "owning Site."
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
            allowed = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-")
            if not set(self.code) <= allowed:
                raise ValidationError({"code": "Code must be letters, numbers, and hyphens only."})
            if self.code.startswith("-") or self.code.endswith("-") or "--" in self.code:
                raise ValidationError({"code": "Code cannot start/end with a hyphen or contain a double hyphen."})

            if self.location_kind == LocationKindChoices.FLOOR:
                if not (1 <= len(self.code) <= 3):
                    raise ValidationError({"code": "Floor codes must be 1-3 characters, e.g. GF, F1, F10."})
            elif self.location_kind == LocationKindChoices.BUILDING:
                if not (1 <= len(self.code) <= 4):
                    raise ValidationError({"code": "Building codes must be 1-4 characters, e.g. B1, B10."})
            elif self.location_kind == LocationKindChoices.OTHER:
                if not (1 <= len(self.code) <= 6):
                    raise ValidationError({"code": "Other-zone codes must be 1-6 characters."})
            else:
                # Site-level: full Atoll-Island-Facility hierarchy
                if not (1 <= len(self.code) <= 20):
                    raise ValidationError({"code": "Site code must be 1-20 characters (letters, numbers, hyphens)."})

    def save(self, *args, **kwargs):
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
PYEOF

echo "models.py updated."

cd ~/netbox-docker
docker compose exec netbox python manage.py makemigrations netbox_nameguard

docker compose cp netbox-1:/plugins/netbox-nameguard/netbox_nameguard/migrations/. \
  ~/netbox-nameguard/netbox_nameguard/migrations/ 2>/dev/null || \
  echo "NOTE: adjust the container name/path above if this copy step fails — run 'docker compose ps' to check the netbox container's name."

cd ~/netbox-nameguard
git add -A
git commit -m "Widen SiteCode.code to 20 chars, allow hyphens, split length rules by location_kind"
git push

NEW_HASH=$(git log --oneline -1 | awk '{print $1}')
echo "New commit hash: $NEW_HASH"

cd ~/netbox-docker
sed -i "s#archive/[a-f0-9]*\.tar\.gz#archive/${NEW_HASH}.tar.gz#" Dockerfile-plugins
grep "archive/" Dockerfile-plugins

docker compose build --no-cache
docker compose up -d

docker compose exec netbox python manage.py migrate netbox_nameguard

echo "Done. SiteCode now accepts full hyphenated hierarchy codes like K-KAA-PH1."
