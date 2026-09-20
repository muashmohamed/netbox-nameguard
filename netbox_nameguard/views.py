import csv
import uuid

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View
from django_tables2 import RequestConfig

from dcim.models import Device
from netbox.views import generic

from . import naming
from .choices import ComplianceStatusChoices
from .forms import BulkRenameConfirmForm, ComplianceFilterForm, NamingPatternForm, SiteCodeForm
from .models import NamingPattern, RenameLog, SiteCode
from .tables import ComplianceTable, NamingPatternTable, RenameLogTable, SiteCodeTable


# ---------------------------------------------------------------------------
# SiteCode CRUD
# ---------------------------------------------------------------------------

class SiteCodeListView(generic.ObjectListView):
    queryset = SiteCode.objects.all()
    table = SiteCodeTable


class SiteCodeView(generic.ObjectView):
    queryset = SiteCode.objects.all()


class SiteCodeEditView(generic.ObjectEditView):
    queryset = SiteCode.objects.all()
    form = SiteCodeForm


class SiteCodeDeleteView(generic.ObjectDeleteView):
    queryset = SiteCode.objects.all()


class SiteCodeBulkDeleteView(generic.BulkDeleteView):
    queryset = SiteCode.objects.all()
    table = SiteCodeTable


# ---------------------------------------------------------------------------
# NamingPattern CRUD
# ---------------------------------------------------------------------------

class NamingPatternListView(generic.ObjectListView):
    queryset = NamingPattern.objects.all()
    table = NamingPatternTable


class NamingPatternView(generic.ObjectView):
    queryset = NamingPattern.objects.all()


class NamingPatternEditView(generic.ObjectEditView):
    queryset = NamingPattern.objects.all()
    form = NamingPatternForm


class NamingPatternDeleteView(generic.ObjectDeleteView):
    queryset = NamingPattern.objects.all()


class NamingPatternBulkDeleteView(generic.BulkDeleteView):
    queryset = NamingPattern.objects.all()
    table = NamingPatternTable


# ---------------------------------------------------------------------------
# RenameLog (read-only audit trail)
# ---------------------------------------------------------------------------

class RenameLogListView(generic.ObjectListView):
    queryset = RenameLog.objects.all()
    table = RenameLogTable


class RenameLogView(generic.ObjectView):
    queryset = RenameLog.objects.all()


# ---------------------------------------------------------------------------
# Compliance dashboard + bulk rename workflow
# ---------------------------------------------------------------------------

def _run_compliance(request):
    """Apply the filter form and return (results, filter_form)."""
    filter_form = ComplianceFilterForm(request.GET or None)
    qs = Device.objects.all()
    if filter_form.is_valid():
        if filter_form.cleaned_data.get("site"):
            qs = qs.filter(site=filter_form.cleaned_data["site"])
        if filter_form.cleaned_data.get("device_role"):
            qs = qs.filter(role=filter_form.cleaned_data["device_role"])

    seq_cache = naming.build_seq_cache(qs)
    results = [naming.check_device(d, seq_cache=seq_cache) for d in qs]
    naming.resolve_collisions(results)

    status_filter = filter_form.cleaned_data.get("status") if filter_form.is_valid() else None
    if status_filter:
        results = [r for r in results if r.status == status_filter]

    return results, filter_form


class ComplianceListView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "netbox_nameguard.view_sitecode"
    template_name = "netbox_nameguard/compliance_list.html"

    def get(self, request):
        results, filter_form = _run_compliance(request)

        for r in results:
            if r.expected_name is None:
                r.expected_name = ""
            if r.location_code is None:
                r.location_code = ""

        table = ComplianceTable(results)
        RequestConfig(request, paginate=False).configure(table)

        summary = {
            "total": len(results),
            "compliant": sum(1 for r in results if r.status == ComplianceStatusChoices.COMPLIANT),
            "noncompliant": sum(1 for r in results if r.status == ComplianceStatusChoices.NONCOMPLIANT),
            "collision": sum(1 for r in results if r.status == ComplianceStatusChoices.COLLISION),
            "unconfigured": sum(1 for r in results if r.status == ComplianceStatusChoices.UNCONFIGURED),
        }
        return render(request, self.template_name, {
            "table": table,
            "filter_form": filter_form,
            "summary": summary,
        })


class BulkRenamePreviewView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """
    Step 1 of enforcement: never renames anything directly. Takes the
    devices selected on the compliance dashboard, computes what their
    proposed names would be, and shows a preview the user must explicitly
    confirm (or export as CSV) before anything is written.
    """
    permission_required = "netbox_nameguard.change_sitecode"
    template_name = "netbox_nameguard/bulk_rename_preview.html"

    def post(self, request):
        pks = request.POST.getlist("pk")
        if not pks:
            messages.warning(request, "No devices were selected.")
            return redirect("plugins:netbox_nameguard:compliance_list")

        devices = Device.objects.filter(pk__in=pks)
        seq_cache = naming.build_seq_cache(devices)
        results = [naming.check_device(d, seq_cache=seq_cache) for d in devices]
        naming.resolve_collisions(results)

        renameable = [
            r for r in results
            if r.status == ComplianceStatusChoices.NONCOMPLIANT and r.expected_name
        ]
        blocked = [r for r in results if r.status == ComplianceStatusChoices.COLLISION]
        already_ok = [r for r in results if r.status == ComplianceStatusChoices.COMPLIANT]

        confirm_form = BulkRenameConfirmForm(initial={"pk": [r.device.pk for r in renameable]})

        request.session["nameguard_preview_pks"] = [r.device.pk for r in renameable]

        return render(request, self.template_name, {
            "renameable": renameable,
            "blocked": blocked,
            "already_ok": already_ok,
            "confirm_form": confirm_form,
        })


class BulkRenameExportView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Download the current dry-run preview as a CSV: current name -> proposed name."""
    permission_required = "netbox_nameguard.change_sitecode"

    def get(self, request):
        pks = request.session.get("nameguard_preview_pks", [])
        devices = Device.objects.filter(pk__in=pks)
        seq_cache = naming.build_seq_cache(devices)
        results = [naming.check_device(d, seq_cache=seq_cache) for d in devices]

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="nameguard_dry_run.csv"'
        writer = csv.writer(response)
        writer.writerow(["device_id", "current_name", "proposed_name", "site_code", "location_code", "pattern"])
        for r in results:
            writer.writerow([
                r.device.pk, r.current_name, r.expected_name or "",
                r.site_code or "", r.location_code or "", r.pattern.template if r.pattern else "",
            ])
        return response


class BulkRenameApplyView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """
    Step 2: only reached after the user has seen the preview and ticked the
    explicit confirmation checkbox. Applies renames and writes a RenameLog
    row (grouped under one batch_id) for every device changed.
    """
    permission_required = "netbox_nameguard.change_sitecode"

    def post(self, request):
        form = BulkRenameConfirmForm(request.POST)
        if not form.is_valid():
            messages.error(request, "You must confirm before applying changes.")
            return redirect("plugins:netbox_nameguard:compliance_list")

        devices = list(form.cleaned_data["pk"])
        seq_cache = naming.build_seq_cache(devices)
        results = [naming.check_device(d, seq_cache=seq_cache) for d in devices]
        naming.resolve_collisions(results)

        batch_id = uuid.uuid4()
        applied = 0
        for r in results:
            if r.status != ComplianceStatusChoices.NONCOMPLIANT or not r.expected_name:
                continue  # skip anything that became a collision or already compliant
            old_name = r.device.name
            r.device.name = r.expected_name
            r.device.save()
            RenameLog.objects.create(
                device=r.device,
                device_name_snapshot=r.expected_name,
                old_name=old_name or "",
                new_name=r.expected_name,
                batch_id=batch_id,
                applied_by=request.user,
            )
            applied += 1

        messages.success(request, f"Renamed {applied} device(s). See the Rename Log for details.")
        return redirect("plugins:netbox_nameguard:renamelog_list")
