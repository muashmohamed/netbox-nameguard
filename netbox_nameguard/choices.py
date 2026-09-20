from utilities.choices import ChoiceSet


class SequencePolicyChoices(ChoiceSet):
    """
    Controls how the next {SEQ} value is chosen for a given Site + Naming
    Pattern when a new name is generated.
    """
    GAP_AWARE = "gap_aware"       # reuse the lowest freed-up number
    ALWAYS_INCREMENT = "always_increment"  # never reuse a retired number

    CHOICES = [
        (GAP_AWARE, "Reuse freed-up numbers (gap-aware)"),
        (ALWAYS_INCREMENT, "Always increment (never reuse)"),
    ]


class ComplianceStatusChoices(ChoiceSet):
    COMPLIANT = "compliant"
    NONCOMPLIANT = "noncompliant"
    UNCONFIGURED = "unconfigured"  # no SiteCode and/or NamingPattern found
    COLLISION = "collision"        # proposed name collides with another device

    CHOICES = [
        (COMPLIANT, "Compliant", "green"),
        (NONCOMPLIANT, "Non-compliant", "red"),
        (UNCONFIGURED, "Unconfigured", "gray"),
        (COLLISION, "Collision", "orange"),
    ]


class LocationKindChoices(ChoiceSet):
    """
    Tags what a Location-based SiteCode actually represents, so the naming
    engine's ancestor-walk can tell "the nearest Building" apart from "the
    nearest Floor" instead of treating every registered Location code the
    same way. Only meaningful when a SiteCode targets a Location (not a
    Site) — left blank for Site-level codes.
    """
    BUILDING = "building"
    FLOOR = "floor"
    OTHER = "other"  # e.g. an outdoor/compound zone that isn't a building or floor

    CHOICES = [
        (BUILDING, "Building"),
        (FLOOR, "Floor"),
        (OTHER, "Other"),
    ]
