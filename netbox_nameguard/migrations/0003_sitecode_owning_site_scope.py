from django.db import migrations, models
import django.db.models.deletion


def backfill_owning_site(apps, schema_editor):
    SiteCode = apps.get_model("netbox_nameguard", "SiteCode")
    for sc in SiteCode.objects.all():
        if sc.site_id:
            sc.owning_site_id = sc.site_id
        elif sc.location_id:
            Location = apps.get_model("dcim", "Location")
            loc = Location.objects.filter(pk=sc.location_id).first()
            sc.owning_site_id = loc.site_id if loc else None
        sc.save(update_fields=["owning_site"])


def noop_reverse(apps, schema_editor):
    pass  # owning_site is dropped entirely on reverse; nothing else to undo


class Migration(migrations.Migration):

    dependencies = [
        ("dcim", "0001_initial"),
        ("netbox_nameguard", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="sitecode",
            name="owning_site",
            field=models.ForeignKey(
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="nameguard_owned_codes",
                to="dcim.site",
            ),
        ),
        migrations.RunPython(backfill_owning_site, noop_reverse),
        migrations.AlterField(
            model_name="sitecode",
            name="code",
            field=models.CharField(max_length=5),
        ),
        migrations.AddConstraint(
            model_name="sitecode",
            constraint=models.UniqueConstraint(
                fields=("owning_site", "code"),
                name="nameguard_unique_code_per_owning_site",
            ),
        ),
    ]
