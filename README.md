# NetBox NameGuard

A NetBox plugin that standardizes and enforces device naming conventions
across the inventory: a Site/Location code registry, per-Device-Role naming
templates, a compliance dashboard, and a dry-run-then-confirm bulk rename
workflow with a permanent audit log.

This scaffold follows the structure and conventions of NetBox's own
[**Plugin Development Tutorial**](https://github.com/netbox-community/netbox-plugin-tutorial)
(targets NetBox v4.5+). If you haven't built a NetBox plugin before, read
that tutorial alongside this code — the section headers below point at the
matching step.

## What's implemented

| Spec requirement | Where |
|---|---|
| Site/Location → 4-letter code registry | `models.SiteCode`, enforced unique + exactly-one-target |
| Per-role naming templates (`{SITE}-CAM-{SEQ}`) | `models.NamingPattern` |
| Compliance checking / "Naming Status" column | `naming.check_device()`, `tables.ComplianceTable`, `views.ComplianceListView` |
| Bulk enforcement with preview/dry-run | `views.BulkRenamePreviewView` → `views.BulkRenameApplyView` (nothing is written until the preview is explicitly confirmed) |
| Rename history / audit log | `models.RenameLog`, `views.RenameLogListView` |
| Collision handling | `naming.resolve_collisions()` — colliding devices are flagged and skipped, never silently overwritten |
| Gap-aware vs. always-increment sequencing | `choices.SequencePolicyChoices`, `naming.next_sequence()`, configurable per Naming Pattern |
| Dry-run CSV export | `views.BulkRenameExportView` |

## Project layout

```
netbox-nameguard/
├── pyproject.toml
├── README.md
└── netbox_nameguard/
    ├── __init__.py          # Step 1: PluginConfig
    ├── models.py            # Step 2: SiteCode, NamingPattern, RenameLog
    ├── choices.py            #         SequencePolicy / ComplianceStatus choice sets
    ├── naming.py             #         core matching/rendering/sequencing engine (plain Python)
    ├── tables.py             # Step 3: list + compliance tables
    ├── forms.py              # Step 4: create/edit forms + bulk-rename confirm form
    ├── views.py              # Step 5: CRUD views + compliance/bulk-rename workflow
    ├── urls.py               # Step 6
    ├── navigation.py         # Step 7: left-nav menu
    ├── admin.py              #         Django admin registration
    ├── migrations/0001_initial.py
    ├── templates/netbox_nameguard/
    │   ├── sitecode.html
    │   ├── namingpattern.html
    │   ├── renamelog.html
    │   ├── compliance_list.html
    │   └── bulk_rename_preview.html
    └── api/                  # left empty — see "Next steps" if you want REST/GraphQL
```

Deliberately not yet covered (the tutorial's later steps, and your own
"nice-to-have" list): filter sets (Step 9), REST API serializers/views
(Step 10), GraphQL (Step 11), global search registration (Step 12), and
unit tests. The core engine in `naming.py` is written as plain,
Django-light functions specifically so it's easy to unit test — see
"Next steps" below.

## How the naming engine works

`naming.py` has no view/form logic in it, so you can read (and test) it on
its own:

- `get_site_code_for_device(device)` — resolves a device's SiteCode via its
  Location first, falling back to its Site.
- `get_pattern_for_device(device)` — looks up the NamingPattern for the
  device's role.
- `build_name_regex(template, site_code, seq_width)` — turns
  `"{SITE}-CAM-{SEQ}"` + `"HOBB"` into a regex that matches any name the
  pattern could have generated, with the sequence number captured.
- `check_device(device)` — the core compliance check. Returns a
  `ComplianceResult` with one of four statuses: `compliant`,
  `noncompliant`, `unconfigured` (no SiteCode/pattern registered), or
  `collision` (assigned by `resolve_collisions()` afterward).
- `next_sequence(existing_seqs, policy)` — implements both sequencing
  policies: gap-aware (reuse the lowest free number) and always-increment
  (never reuse a retired number).
- `resolve_collisions(results)` — after computing proposed names for a
  batch, groups any that landed on the identical name and flags every
  member of that group as a `collision` instead of letting the last one
  silently win.

## Installing into your dev environment

Follow [Step 0](https://github.com/netbox-community/netbox-plugin-tutorial/blob/main/tutorial/step00-initial-setup.md)
of the tutorial to get a NetBox 4.5+ dev instance running with
`DEBUG = True` and `DEVELOPER = True`, then:

```bash
# from this project's root
pip install -e .
```

In NetBox's `configuration.py`:

```python
PLUGINS = ["netbox_nameguard"]
```

Then, from your NetBox root:

```bash
python manage.py migrate netbox_nameguard
python manage.py runserver
```

You should see a **NameGuard** entry in the left nav with Site Codes,
Naming Patterns, a Compliance Dashboard, and a Rename Log.

## Suggested first run

1. Under **Site Codes**, register a code for each Site/Location you care
   about (e.g. `HOBB`, `KKSH`).
2. Under **Naming Patterns**, add one row per Device Role with its
   template (e.g. Camera → `{SITE}-CAM-{SEQ}`, Switch → `{SITE}-SW-{SEQ}`).
3. Open the **Compliance Dashboard** — every device with a resolvable
   SiteCode + NamingPattern gets a Naming Status badge.
4. Tick the non-compliant devices you want to fix, click **Preview rename
   for selected devices**. Review the current → proposed table (or
   download it as CSV), then tick the confirmation box and **Apply**.
5. Check the **Rename Log** — every applied rename is recorded there
   permanently, grouped by batch, even if the device is later deleted.

## Next steps / where to take this further

- **Tests**: since `naming.py` is dependency-light, start there —
  parametrize `build_name_regex` / `next_sequence` / `resolve_collisions`
  with plain dataclass fixtures before you need a full NetBox test DB.
- **REST API** (tutorial Step 10): expose `SiteCode`/`NamingPattern` so
  other tools can read the registry, and consider a `POST
  /nameguard/bulk-rename/` endpoint that mirrors the UI's preview→apply
  flow for scripted enforcement.
- **Filter sets** (Step 9): the compliance dashboard currently filters by
  Site/Role/status via a plain form; wiring up `django-filter` FilterSets
  would let you drop it into NetBox's standard filterable list-view UI.
- **Search** (Step 12): register `SiteCode` and `NamingPattern` so they
  show up in NetBox's global search.
- **Permissions**: views currently gate on the built-in `view_sitecode` /
  `change_sitecode` permissions as a placeholder — consider a dedicated
  permission (e.g. `netbox_nameguard.apply_rename`) so "can configure
  patterns" and "can execute bulk renames" can be granted separately.

## A note on this scaffold

This was generated without a live NetBox instance to run it against, so
treat it as a solid, tutorial-conformant starting point rather than
tested-and-shipped code — run `migrate`, click through each view, and fix
up anything that doesn't match your exact NetBox version (model field
names like `Device.role` vs. the older `Device.device_role` changed
between NetBox releases, for example).
