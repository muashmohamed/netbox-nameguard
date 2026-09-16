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
