import re
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse

from netbox.models import NetBoxModel

from .choices import LocationKindChoices, SequencePolicyChoices


class AtollType(NetBoxModel):
    """
    Glossary entry: what an Atoll-code prefix (the segment before the
    first hyphen in a Site-level code) actually means, e.g. "K" -> Kaafu,
    "GRM" -> Greater Male' (not an official government code, but treated
    the same way here).
    """
    code = models.CharField(
        max_length=6,
        unique=True,
        help_text="The Atoll code as used in Site-level SiteCodes, e.g. K, HDh, GRM.",
    )
    name = models.CharField(
        max_length=50,
        help_text="What the code means, e.g. Kaafu, Haa Dhaalu, Greater Male'.",
    )
    is_official = models.BooleanField(
        default=True,
        help_text="Uncheck for non-government additions like Greater Male' (GRM).",
    )
    description = models.TextField(blank=True)
    comments = models.TextField(blank=True)

    class Meta:
        ordering = ("code",)
        verbose_name = "Atoll Type"
        verbose_name_plural = "Atoll Types"

    def __str__(self):
        return f"{self.code} ({self.name})"

    def get_absolute_url(self):
        return reverse("plugins:netbox_nameguard:atolltype", args=[self.pk])

    def clean(self):
        super().clean()
        if self.code:
            self.code = self.code.strip()


class IslandType(NetBoxModel):
    """
    Glossary entry: what an Island-code (the segment after the first
    hyphen in a Site-level code) means, scoped to its Atoll since island
    codes are only guaranteed unique within their own atoll, not globally.
    """
    atoll = models.ForeignKey(
        to=AtollType,
        on_delete=models.PROTECT,
        related_name="islands",
    )
    code = models.CharField(
        max_length=10,
        help_text="The Island code as used after the Atoll in a Site-level SiteCode, e.g. KAA, HUL1, MAL.",
    )
    name = models.CharField(
        max_length=50,
        help_text="What the code means, e.g. Kaashidhoo, Hulhumale Phase 1, Male.",
    )
    description = models.TextField(blank=True)
    comments = models.TextField(blank=True)

    class Meta:
        ordering = ("atoll__code", "code")
        constraints = [
            models.UniqueConstraint(fields=["atoll", "code"], name="nameguard_unique_island_code_per_atoll"),
        ]
        verbose_name = "Island Type"
        verbose_name_plural = "Island Types"

    def __str__(self):
        return f"{self.atoll.code}-{self.code} ({self.name})"

    def get_absolute_url(self):
        return reverse("plugins:netbox_nameguard:islandtype", args=[self.pk])

    def clean(self):
        super().clean()
        if self.code:
            self.code = self.code.strip().upper()

    @property
    def full_code(self):
        """The actual unique identifier: Atoll-Island combined, e.g. AA-MAN."""
        return f"{self.atoll.code}-{self.code}"


class FacilityType(NetBoxModel):
    """
    Glossary entry: what a Facility-code prefix actually means, so codes
    like "PH1", "SS10" don't need their meaning re-explained everywhere.
    A code's prefix is its leading letters (e.g. "PH" in "PH1"); anything
    trailing is treated as the instance number for self-numbering types
    (Powerhouse, Substation, Pump Station). One-off named facilities
    (Apollo Tower, Gaakoshi) just use their whole code as the prefix with
    no trailing number.
    """
    prefix = models.CharField(
        max_length=6,
        unique=True,
        help_text="The leading letters of the code, e.g. PH, SS, PS, or the whole code for a one-off facility like APL.",
    )
    name = models.CharField(
        max_length=50,
        help_text="What the prefix means, e.g. Powerhouse, Substation, Apollo Tower.",
    )
    description = models.TextField(blank=True)
    comments = models.TextField(blank=True)

    class Meta:
        ordering = ("prefix",)
        verbose_name = "Facility Type"
        verbose_name_plural = "Facility Types"

    def __str__(self):
        return f"{self.prefix} ({self.name})"

    def get_absolute_url(self):
        return reverse("plugins:netbox_nameguard:facilitytype", args=[self.pk])

    def clean(self):
        super().clean()
        if self.prefix:
            self.prefix = self.prefix.strip().upper()
            if not self.prefix.isalpha():
                raise ValidationError({"prefix": "Prefix must be letters only (the number is computed from the code itself)."})

    @classmethod
    def label_for(cls, code: str) -> str:
        """
        Turn a Facility-kind SiteCode value into a human-readable label
        using this glossary, e.g. "SS10" -> "Substation 10", "APL" ->
        "Apollo Tower". Falls back to the raw code if no glossary entry
        matches its prefix.
        """
        if not code:
            return code
        m = re.match(r"^([A-Z]+)(\d*)$", code.upper())
        if not m:
            return code
        prefix, number = m.groups()
        entry = cls.objects.filter(prefix=prefix).first()
        if not entry:
            return code
        return f"{entry.name} {number}" if number else entry.name


class SiteCode(NetBoxModel):
    """
    A single registry mapping exactly one of {Site, Location} to a fixed,
    reusable code.

    Site-level codes carry the full Atoll-Island hierarchy, hyphen-
    separated (e.g. "K-KAA"), and feed the {SITE} token; their human
    meaning comes from AtollType/IslandType. Location-level codes are
    scoped to a single Facility ("PH1", "SS1"), Building ("B1"), Floor
    ("GF", "F1"), or Other zone, tagged via location_kind; a Facility-kind
    code's meaning comes from FacilityType.
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
        help_text="Required when targeting a Location: Facility, Building, Floor, or Other?",
    )
    code = models.CharField(
        max_length=20,
        help_text=(
            "Site-level codes carry the Atoll-Island hierarchy, hyphen-"
            "separated, e.g. K-KAA (see Atoll/Island Types for what each "
            "part means). Location-level codes are scoped to their kind: "
            "Facility (e.g. PH1, PH2, SS1, up to 5 chars - see Facility "
            "Types for meaning), Building (e.g. B1, up to 4 chars), Floor "
            "(e.g. GF, F1, up to 3 chars), Other (up to 6 chars). Letters, "
            "numbers, and hyphens only. Must be unique within its owning Site."
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

    @property
    def facility_label(self):
        """Human-readable meaning of this code, only meaningful for Facility-kind codes."""
        if self.location_kind == LocationKindChoices.FACILITY:
            return FacilityType.label_for(self.code)
        return ""

    @property
    def site_label(self):
        """
        Human-readable meaning of a Site-level code, e.g. "K-KAA" ->
        "Kaafu, Kaashidhoo". Only meaningful when this SiteCode targets a
        Site (not a Location). Falls back gracefully if the Atoll/Island
        isn't in the glossary yet.
        """
        if not self.site_id or not self.code:
            return ""
        parts = self.code.split("-", 1)
        if len(parts) != 2:
            return ""
        atoll_code, island_code = parts
        atoll = AtollType.objects.filter(code=atoll_code).first()
        island = IslandType.objects.filter(atoll__code=atoll_code, code=island_code).first()
        atoll_name = atoll.name if atoll else atoll_code
        island_name = island.name if island else island_code
        return f"{atoll_name}, {island_name}"

    def clean(self):
        super().clean()
        if bool(self.site) == bool(self.location):
            raise ValidationError("Set exactly one of Site or Location, not both/neither.")
        if self.location and not self.location_kind:
            raise ValidationError({"location_kind": "Required when targeting a Location: Facility, Building, Floor, or Other?"})
        if self.site and self.location_kind:
            self.location_kind = ""
        if self.code:
            self.code = self.code.strip().upper()
            allowed = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-")
            if not set(self.code) <= allowed:
                raise ValidationError({"code": "Code must be letters, numbers, and hyphens only."})
            if self.code.startswith("-") or self.code.endswith("-") or "--" in self.code:
                raise ValidationError({"code": "Code cannot start/end with a hyphen or contain a double hyphen."})

            if self.location_kind == LocationKindChoices.FACILITY:
                if not (1 <= len(self.code) <= 5):
                    raise ValidationError({"code": "Facility codes must be 1-5 characters, e.g. PH1, SS1, PS1."})
            elif self.location_kind == LocationKindChoices.FLOOR:
                if not (1 <= len(self.code) <= 3):
                    raise ValidationError({"code": "Floor codes must be 1-3 characters, e.g. GF, F1, F10."})
            elif self.location_kind == LocationKindChoices.BUILDING:
                if not (1 <= len(self.code) <= 4):
                    raise ValidationError({"code": "Building codes must be 1-4 characters, e.g. B1, B10."})
            elif self.location_kind == LocationKindChoices.OTHER:
                if not (1 <= len(self.code) <= 6):
                    raise ValidationError({"code": "Other-zone codes must be 1-6 characters."})
            else:
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
    Camera -> "{SITE}-{FACILITY}-CAM-{SEQ}".
    """
    device_role = models.OneToOneField(
        to="dcim.DeviceRole",
        on_delete=models.CASCADE,
        related_name="nameguard_pattern",
    )
    template = models.CharField(
        max_length=100,
        help_text="Use {SITE}, {FACILITY}, {LOCATION}, {FLOOR}, and {SEQ} tokens.",
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
            if not any(t in self.template for t in ("{SITE}", "{FACILITY}", "{LOCATION}", "{FLOOR}")):
                raise ValidationError({"template": "Template must include at least one of {SITE}/{FACILITY}/{LOCATION}/{FLOOR}."})


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
