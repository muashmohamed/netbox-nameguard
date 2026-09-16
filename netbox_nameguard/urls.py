from django.urls import path

from netbox.views.generic import ObjectChangeLogView

from . import views
from .models import NamingPattern, SiteCode

urlpatterns = (
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

    # Rename Log (audit trail)
    path("rename-log/", views.RenameLogListView.as_view(), name="renamelog_list"),
    path("rename-log/<int:pk>/", views.RenameLogView.as_view(), name="renamelog"),

    # Compliance dashboard + bulk enforcement workflow
    path("compliance/", views.ComplianceListView.as_view(), name="compliance_list"),
    path("compliance/preview/", views.BulkRenamePreviewView.as_view(), name="bulk_rename_preview"),
    path("compliance/export/", views.BulkRenameExportView.as_view(), name="bulk_rename_export"),
    path("compliance/apply/", views.BulkRenameApplyView.as_view(), name="bulk_rename_apply"),
)
