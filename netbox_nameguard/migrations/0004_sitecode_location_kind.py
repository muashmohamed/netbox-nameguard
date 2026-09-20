from django.db import migrations, models


def backfill_location_kind(apps, schema_editor):
    SiteCode = apps.get_model("netbox_nameguard", "SiteCode")
    # Every existing Location-based code so far has represented a building
    # (that's all NameGuard supported before this migration).
    SiteCode.objects.filter(location__isnull=False).update(location_kind="building")


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("netbox_nameguard", "0003_sitecode_owning_site_scope"),
    ]

    operations = [
        migrations.AddField(
            model_name="sitecode",
            name="location_kind",
            field=models.CharField(blank=True, max_length=20),
        ),
        migrations.RunPython(backfill_location_kind, noop_reverse),
    ]
