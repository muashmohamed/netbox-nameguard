from django.urls import path

from netbox.views.generic import ObjectChangeLogView

from . import views
from .models import AtollType, FacilityType, IslandType, NamingPattern, RackNamingPattern, SiteCode

urlpatterns = (
    # Atoll Types (glossary)
    path("atoll-types/", views.AtollTypeListView.as_view(), name="atolltype_list"),
    path("atoll-types/add/", views.AtollTypeEditView.as_view(), name="atolltype_add"),
    path("atoll-types/delete/", views.AtollTypeBulkDeleteView.as_view(), name="atolltype_bulk_delete"),
    path("atoll-types/<int:pk>/", views.AtollTypeView.as_view(), name="atolltype"),
    path("atoll-types/<int:pk>/edit/", views.AtollTypeEditView.as_view(), name="atolltype_edit"),
    path("atoll-types/<int:pk>/delete/", views.AtollTypeDeleteView.as_view(), name="atolltype_delete"),
    path(
        "atoll-types/<int:pk>/changelog/",
        ObjectChangeLogView.as_view(),
        name="atolltype_changelog",
        kwargs={"model": AtollType},
    ),

    # Island Types (glossary)
    path("island-types/", views.IslandTypeListView.as_view(), name="islandtype_list"),
    path("island-types/add/", views.IslandTypeEditView.as_view(), name="islandtype_add"),
    path("island-types/delete/", views.IslandTypeBulkDeleteView.as_view(), name="islandtype_bulk_delete"),
    path("island-types/<int:pk>/", views.IslandTypeView.as_view(), name="islandtype"),
    path("island-types/<int:pk>/edit/", views.IslandTypeEditView.as_view(), name="islandtype_edit"),
    path("island-types/<int:pk>/delete/", views.IslandTypeDeleteView.as_view(), name="islandtype_delete"),
    path(
        "island-types/<int:pk>/changelog/",
        ObjectChangeLogView.as_view(),
        name="islandtype_changelog",
        kwargs={"model": IslandType},
    ),

    # Facility Types (glossary)
    path("facility-types/", views.FacilityTypeListView.as_view(), name="facilitytype_list"),
    path("facility-types/add/", views.FacilityTypeEditView.as_view(), name="facilitytype_add"),
    path("facility-types/delete/", views.FacilityTypeBulkDeleteView.as_view(), name="facilitytype_bulk_delete"),
    path("facility-types/<int:pk>/", views.FacilityTypeView.as_view(), name="facilitytype"),
    path("facility-types/<int:pk>/edit/", views.FacilityTypeEditView.as_view(), name="facilitytype_edit"),
    path("facility-types/<int:pk>/delete/", views.FacilityTypeDeleteView.as_view(), name="facilitytype_delete"),
    path(
        "facility-types/<int:pk>/changelog/",
        ObjectChangeLogView.as_view(),
        name="facilitytype_changelog",
        kwargs={"model": FacilityType},
    ),

    # Site Codes
    path("site-codes/", views.SiteCodeListView.as_view(), name="sitecode_list"),
    path("site-codes/add/", views.SiteCodeEditView.as_view(), name="sitecode_add"),
    path("site-codes/delete/", views.SiteCodeBulkDeleteView.as_view(), name="sitecode_bulk_delete"),
    path("site-codes/<int:pk>/", views.SiteCodeView.as_view(), name="sitecode"),
    path("site-codes/<int:pk>/edit/", views.SiteCodeEditView.as_view(), name="sitecode_edit"),
    path("site-codes/<int:pk>/delete/", views.SiteCodeDeleteView.as_view(), name="sitecode_delete"),
    path(
        "site-codes/<int:pk>/changelog/",
        ObjectChangeLogView.as_view(),
        name="sitecode_changelog",
        kwargs={"model": SiteCode},
    ),

    # Naming Patterns
    path("patterns/", views.NamingPatternListView.as_view(), name="namingpattern_list"),
    path("patterns/add/", views.NamingPatternEditView.as_view(), name="namingpattern_add"),
    path("patterns/delete/", views.NamingPatternBulkDeleteView.as_view(), name="namingpattern_bulk_delete"),
    path("patterns/<int:pk>/", views.NamingPatternView.as_view(), name="namingpattern"),
    path("patterns/<int:pk>/edit/", views.NamingPatternEditView.as_view(), name="namingpattern_edit"),
    path("patterns/<int:pk>/delete/", views.NamingPatternDeleteView.as_view(), name="namingpattern_delete"),
    path(
        "patterns/<int:pk>/changelog/",
        ObjectChangeLogView.as_view(),
        name="namingpattern_changelog",
        kwargs={"model": NamingPattern},
    ),

    # Rack Naming Patterns
    path("rack-patterns/", views.RackNamingPatternListView.as_view(), name="racknamingpattern_list"),
    path("rack-patterns/add/", views.RackNamingPatternEditView.as_view(), name="racknamingpattern_add"),
    path("rack-patterns/delete/", views.RackNamingPatternBulkDeleteView.as_view(), name="racknamingpattern_bulk_delete"),
    path("rack-patterns/<int:pk>/", views.RackNamingPatternView.as_view(), name="racknamingpattern"),
    path("rack-patterns/<int:pk>/edit/", views.RackNamingPatternEditView.as_view(), name="racknamingpattern_edit"),
    path("rack-patterns/<int:pk>/delete/", views.RackNamingPatternDeleteView.as_view(), name="racknamingpattern_delete"),
    path(
        "rack-patterns/<int:pk>/changelog/",
        ObjectChangeLogView.as_view(),
        name="racknamingpattern_changelog",
        kwargs={"model": RackNamingPattern},
    ),

    # Rename Log (audit trail)
    path("rename-log/", views.RenameLogListView.as_view(), name="renamelog_list"),
    path("rename-log/<int:pk>/", views.RenameLogView.as_view(), name="renamelog"),

    # Compliance dashboard + bulk enforcement workflow
    path("compliance/", views.ComplianceListView.as_view(), name="compliance_list"),
    path("compliance/preview/", views.BulkRenamePreviewView.as_view(), name="bulk_rename_preview"),
    path("compliance/export/", views.BulkRenameExportView.as_view(), name="bulk_rename_export"),
    path("compliance/apply/", views.BulkRenameApplyView.as_view(), name="bulk_rename_apply"),

    # Rack compliance dashboard + bulk enforcement workflow (kept separate
    # from Device compliance to avoid ever mixing up a Device pk with a Rack pk)
    path("rack-compliance/", views.RackComplianceListView.as_view(), name="rack_compliance_list"),
    path("rack-compliance/preview/", views.RackBulkRenamePreviewView.as_view(), name="rack_bulk_rename_preview"),
    path("rack-compliance/export/", views.RackBulkRenameExportView.as_view(), name="rack_bulk_rename_export"),
    path("rack-compliance/apply/", views.RackBulkRenameApplyView.as_view(), name="rack_bulk_rename_apply"),
)
