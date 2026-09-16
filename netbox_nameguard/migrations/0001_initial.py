import django.core.validators
import taggit.managers
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import utilities.json


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("dcim", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("extras", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="SiteCode",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("created", models.DateTimeField(auto_now_add=True, null=True)),
                ("last_updated", models.DateTimeField(auto_now=True, null=True)),
                ("custom_field_data", models.JSONField(blank=True, default=dict, encoder=utilities.json.CustomFieldJSONEncoder)),
                ("code", models.CharField(max_length=4, unique=True)),
                ("comments", models.TextField(blank=True)),
                ("location", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="nameguard_codes", to="dcim.location")),
                ("site", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="nameguard_codes", to="dcim.site")),
                ("tags", taggit.managers.TaggableManager(through="extras.TaggedItem", to="extras.Tag")),
            ],
            options={"verbose_name": "Site Code", "verbose_name_plural": "Site Codes", "ordering": ("code",)},
        ),
        migrations.CreateModel(
            name="NamingPattern",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("created", models.DateTimeField(auto_now_add=True, null=True)),
                ("last_updated", models.DateTimeField(auto_now=True, null=True)),
                ("custom_field_data", models.JSONField(blank=True, default=dict, encoder=utilities.json.CustomFieldJSONEncoder)),
                ("template", models.CharField(max_length=100)),
                ("seq_width", models.PositiveSmallIntegerField(default=3)),
                ("seq_policy", models.CharField(choices=[("gap_aware", "Reuse freed-up numbers (gap-aware)"), ("always_increment", "Always increment (never reuse)")], default="gap_aware", max_length=30)),
                ("comments", models.TextField(blank=True)),
                ("device_role", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="nameguard_pattern", to="dcim.devicerole")),
                ("tags", taggit.managers.TaggableManager(through="extras.TaggedItem", to="extras.Tag")),
            ],
            options={"verbose_name": "Naming Pattern", "verbose_name_plural": "Naming Patterns", "ordering": ("device_role__name",)},
        ),
        migrations.CreateModel(
            name="RenameLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("created", models.DateTimeField(auto_now_add=True, null=True)),
                ("last_updated", models.DateTimeField(auto_now=True, null=True)),
                ("custom_field_data", models.JSONField(blank=True, default=dict, encoder=utilities.json.CustomFieldJSONEncoder)),
                ("device_name_snapshot", models.CharField(max_length=64)),
                ("old_name", models.CharField(blank=True, max_length=64)),
                ("new_name", models.CharField(max_length=64)),
                ("batch_id", models.UUIDField(db_index=True, editable=False)),
                ("applied_at", models.DateTimeField(auto_now_add=True)),
                ("applied_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
                ("device", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="nameguard_rename_logs", to="dcim.device")),
                ("tags", taggit.managers.TaggableManager(through="extras.TaggedItem", to="extras.Tag")),
            ],
            options={"verbose_name": "Rename Log", "verbose_name_plural": "Rename Logs", "ordering": ("-applied_at",)},
        ),
        migrations.AddConstraint(
            model_name="sitecode",
            constraint=models.CheckConstraint(
                condition=models.Q(("location__isnull", True), ("site__isnull", False)) | models.Q(("location__isnull", False), ("site__isnull", True)),
                name="nameguard_sitecode_exactly_one_target",
            ),
        ),
        migrations.AddConstraint(
            model_name="sitecode",
            constraint=models.UniqueConstraint(fields=("site",), name="nameguard_unique_site"),
        ),
        migrations.AddConstraint(
            model_name="sitecode",
            constraint=models.UniqueConstraint(fields=("location",), name="nameguard_unique_location"),
        ),
    ]
