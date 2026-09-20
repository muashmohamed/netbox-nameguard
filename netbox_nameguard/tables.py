import django_tables2 as tables

from netbox.tables import NetBoxTable, columns

from .models import NamingPattern, RenameLog, SiteCode


class SiteCodeTable(NetBoxTable):
    code = tables.Column(linkify=True)
    target = tables.Column(verbose_name="Site / Location")

    class Meta(NetBoxTable.Meta):
        model = SiteCode
        fields = ("pk", "id", "code", "target", "comments", "tags")
        default_columns = ("code", "target")


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
    location_code = tables.Column(verbose_name="Location Code", empty_values=())
    reason = tables.Column(verbose_name="Notes")

    class Meta:
        attrs = {"class": "table table-hover object-list"}
        empty_text = "No devices to display."
        order_by = ("name",)
