from django.contrib import admin

from .models import NamingPattern, RenameLog, SiteCode


@admin.register(SiteCode)
class SiteCodeAdmin(admin.ModelAdmin):
    list_display = ("code", "site", "location")
    search_fields = ("code",)


@admin.register(NamingPattern)
class NamingPatternAdmin(admin.ModelAdmin):
    list_display = ("device_role", "template", "seq_width", "seq_policy")


@admin.register(RenameLog)
class RenameLogAdmin(admin.ModelAdmin):
    list_display = ("old_name", "new_name", "applied_by", "applied_at", "batch_id")
    list_filter = ("batch_id",)
    readonly_fields = [f.name for f in RenameLog._meta.fields]
