from utilities.choices import ChoiceSet


class SequencePolicyChoices(ChoiceSet):
    GAP_AWARE = "gap_aware"
    ALWAYS_INCREMENT = "always_increment"

    CHOICES = [
        (GAP_AWARE, "Reuse freed-up numbers (gap-aware)"),
        (ALWAYS_INCREMENT, "Always increment (never reuse)"),
    ]


class ComplianceStatusChoices(ChoiceSet):
    COMPLIANT = "compliant"
    NONCOMPLIANT = "noncompliant"
    UNCONFIGURED = "unconfigured"
    COLLISION = "collision"

    CHOICES = [
        (COMPLIANT, "Compliant", "green"),
        (NONCOMPLIANT, "Non-compliant", "red"),
        (UNCONFIGURED, "Unconfigured", "gray"),
        (COLLISION, "Collision", "orange"),
    ]


class LocationKindChoices(ChoiceSet):
    """
    Tags what a Location-based SiteCode actually represents, so the naming
    engine's ancestor-walk can tell "the nearest Facility" apart from "the
    nearest Building" apart from "the nearest Floor" instead of treating
    every registered Location code the same way. Only meaningful when a
    SiteCode targets a Location (not a Site) — left blank for Site-level
    codes.
    """
    FACILITY = "facility"
    BUILDING = "building"
    FLOOR = "floor"
    OTHER = "other"

    CHOICES = [
        (FACILITY, "Facility"),
        (BUILDING, "Building"),
        (FLOOR, "Floor"),
        (OTHER, "Other"),
    ]
