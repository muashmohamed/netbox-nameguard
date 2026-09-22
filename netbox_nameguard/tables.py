import django_tables2 as tables

from netbox.tables import NetBoxTable, columns

from .models import AtollType, FacilityType, IslandType, NamingPattern, RenameLog, SiteCode


class AtollTypeTable(NetBoxTable):
    code = tables.Column(linkify=True)
    name = tables.Column()
    is_official = columns.BooleanColumn(verbose_name="Official Govt Code")

    class Meta(NetBoxTable.Meta):
        model = AtollType
        fields = ("pk", "id", "code", "name", "is_official", "description", "tags")
        default_columns = ("code", "name", "is_official")


class IslandTypeTable(NetBoxTable):
    code = tables.Column(linkify=True)
    atoll = tables.Column(linkify=True)
    name = tables.Column()

    class Meta(NetBoxTable.Meta):
        model = IslandType
        fields = ("pk", "id", "atoll", "code", "name", "description", "tags")
        default_columns = ("atoll", "code", "name")


class FacilityTypeTable(NetBoxTable):
    prefix = tables.Column(linkify=True)
    name = tables.Column()

    class Meta(NetBoxTable.Meta):
        model = FacilityType
        fields = ("pk", "id", "prefix", "name", "description", "tags")
        default_columns = ("prefix", "name")


class SiteCodeTable(NetBoxTable):
    code = tables.Column(linkify=True)
    target = tables.Column(verbose_name="Site / Location", accessor="target", order_by=("site", "location"))

    def render_target(self, record):
        if record.site_id:
            return record.site.name
        if record.location_id:
            return f"{record.location.site.name} / {record.location.name}"
        return ""
    location_kind = columns.ChoiceFieldColumn(verbose_name="Kind")
    meaning = tables.Column(
        verbose_name="Meaning",
        accessor="facility_label",
        empty_values=(),
        order_by=None,
    )

    def render_meaning(self, record):
        # For a Facility-kind code, show the generic category alongside
        # the specific place it actually is, since PH1 alone could be any
        # island's powerhouse - e.g. "Powerhouse - MAN Powerhouse" for a
        # Location whose real name is MAN Powerhouse. site_label still
        # covers Site-targeted Atoll-Island codes on its own.
        if record.location_kind == "facility" and record.location_id:
            category = record.facility_label
            specific = record.location.name
            if category and category != specific:
                return f"{category} - {specific}"
            return specific or category
        return record.facility_label or record.site_label or ""

    class Meta(NetBoxTable.Meta):
        model = SiteCode
        fields = ("pk", "id", "code", "target", "location_kind", "meaning", "comments", "tags")
        default_columns = ("code", "target", "location_kind", "meaning")


class NamingPatternTable(NetBoxTable):
    device_role = tables.Column(linkify=True)
    template = tables.Column()
    seq_policy = columns.ChoiceFieldColumn()

    class Meta(NetBoxTable.Meta):
        model = NamingPattern
        fields = ("pk", "id", "device_role", "template", "seq_width", "seq_policy", "comments", "tags")
        default_columns = ("device_role", "template", "seq_width", "seq_policy")


class RenameLogTable(NetBoxTable):
    device = tables.Column(linkify=True)
    old_name = tables.Column()
    new_name = tables.Column()
    applied_by = tables.Column()
    applied_at = columns.DateTimeColumn()

    class Meta(NetBoxTable.Meta):
        model = RenameLog
        fields = ("pk", "id", "device", "old_name", "new_name", "batch_id", "applied_by", "applied_at")
        default_columns = ("device", "old_name", "new_name", "applied_by", "applied_at")


class ComplianceTable(tables.Table):
    """
    Not a NetBoxTable, since its rows are ComplianceResult dataclasses
    (a Device paired with computed status), not a plain queryset of one
    model. Supports bulk selection for the rename workflow.
    """
    pk = columns.ToggleColumn(accessor="device.pk")
    name = tables.Column(accessor="current_name", verbose_name="Current Name", linkify=lambda record: record.device.get_absolute_url())
    site = tables.Column(accessor="device.site", verbose_name="Site", order_by=("device.site.name",))
    role = tables.Column(accessor="device.role", verbose_name="Role", order_by=("device.role.name",))
    status = tables.TemplateColumn(
        verbose_name="Naming Status",
        order_by=("status",),
        template_code="""
            {% if record.status == 'compliant' %}<span class="badge text-bg-green">Compliant</span>
            {% elif record.status == 'noncompliant' %}<span class="badge text-bg-red">Non-compliant</span>
            {% elif record.status == 'collision' %}<span class="badge text-bg-orange">Collision</span>
            {% else %}<span class="badge text-bg-gray">Unconfigured</span>{% endif %}
        """,
    )
    expected_name = tables.Column(verbose_name="Proposed Name")
    location_code = tables.Column(verbose_name="Building Code", empty_values=())
    floor_code = tables.Column(verbose_name="Floor Code", empty_values=())
    reason = tables.Column(verbose_name="Notes")

    class Meta:
        attrs = {"class": "table table-hover object-list"}
        empty_text = "No devices to display."
        order_by = ("name",)
