"""
Core naming logic for NameGuard, kept independent of Django views/forms so
it's easy to unit test in isolation.

Tokens supported in a NamingPattern's template:
  {SITE}     - the code registered on the device's Site (Atoll-Island).
  {FACILITY} - the code of the nearest ancestor Location tagged as a
               Facility, found by walking up the Location tree.
  {LOCATION} - the code of the nearest ancestor Location tagged as a
               Building, found the same way, independent of {FACILITY}.
  {FLOOR}    - the code of the nearest ancestor Location tagged as a
               Floor, found the same way, independent of the others.
  {SEQ}      - the zero-padded sequence number.

All location-based tokens are optional — a template only needs to use the
tokens relevant to how that Device Role's devices are actually placed.
"""
import re
from dataclasses import dataclass
from typing import Optional

from .choices import ComplianceStatusChoices, LocationKindChoices, SequencePolicyChoices
from .models import NamingPattern, RackNamingPattern, SiteCode

TOKEN_RE = re.compile(r"\{(SITE|FACILITY|LOCATION|FLOOR|SEQ)\}")


def get_site_level_code(device) -> Optional[str]:
    if not device.site_id:
        return None
    sc = SiteCode.objects.filter(site_id=device.site_id).first()
    return sc.code if sc else None


def _walk_for_kind(device, kind: str) -> Optional[str]:
    location_id = device.location_id
    depth_guard = 0
    while location_id and depth_guard < 50:
        sc = SiteCode.objects.filter(location_id=location_id, location_kind=kind).first()
        if sc:
            return sc.code
        location_id = _location_parent_id(location_id)
        depth_guard += 1
    return None


def get_facility_code_for_device(device) -> Optional[str]:
    """Resolve the {FACILITY} token: nearest ancestor Location tagged Facility."""
    return _walk_for_kind(device, LocationKindChoices.FACILITY)


def get_location_code_for_device(device) -> Optional[str]:
    """Resolve the {LOCATION} token: nearest ancestor Location tagged Building."""
    return _walk_for_kind(device, LocationKindChoices.BUILDING)


def get_floor_code_for_device(device) -> Optional[str]:
    """Resolve the {FLOOR} token: nearest ancestor Location tagged Floor."""
    return _walk_for_kind(device, LocationKindChoices.FLOOR)


def get_facility_place_name(device) -> Optional[str]:
    """
    The specific place name (e.g. "NRD Office"), not the generic glossary
    category (e.g. "Building") - walks up from the device's own Location
    to find the nearest one tagged Facility-kind, and returns ITS name.
    """
    location = device.location
    while location is not None:
        if hasattr(location, "nameguard_codes") and location.nameguard_codes.filter(location_kind=LocationKindChoices.FACILITY).exists():
            return location.name
        location = location.parent
    return None


def _location_parent_id(location_id):
    from dcim.models import Location

    loc = Location.objects.filter(pk=location_id).only("parent_id").first()
    return loc.parent_id if loc else None


def get_pattern_for_device(device) -> Optional[NamingPattern]:
    role_id = getattr(device, "role_id", None) or getattr(device, "device_role_id", None)
    if not role_id:
        return None
    return NamingPattern.objects.filter(device_role_id=role_id).first()


def render_name(template: str, seq: int, seq_width: int, site_code: str = None,
                 facility_code: str = None, location_code: str = None, floor_code: str = None) -> str:
    out = template
    if site_code is not None:
        out = out.replace("{SITE}", site_code)
    if facility_code is not None:
        out = out.replace("{FACILITY}", facility_code)
    if location_code is not None:
        out = out.replace("{LOCATION}", location_code)
    if floor_code is not None:
        out = out.replace("{FLOOR}", floor_code)
    out = out.replace("{SEQ}", str(seq).zfill(seq_width))
    return out


def build_name_regex(template: str, seq_width: int, site_code: str = None,
                      facility_code: str = None, location_code: str = None, floor_code: str = None) -> re.Pattern:
    pattern = ""
    last = 0
    for m in TOKEN_RE.finditer(template):
        pattern += re.escape(template[last:m.start()])
        token = m.group(1)
        if token == "SITE":
            pattern += re.escape(site_code) if site_code else r"[^-]+"
        elif token == "FACILITY":
            pattern += re.escape(facility_code) if facility_code else r"[^-]+"
        elif token == "LOCATION":
            pattern += re.escape(location_code) if location_code else r"[^-]+"
        elif token == "FLOOR":
            pattern += re.escape(floor_code) if floor_code else r"[^-]+"
        else:  # SEQ
            pattern += rf"(?P<seq>\d{{{seq_width},}})"
        last = m.end()
    pattern += re.escape(template[last:])
    return re.compile(f"^{pattern}$")


def next_sequence(existing_seqs, policy: str) -> int:
    used = sorted(existing_seqs)
    if policy == SequencePolicyChoices.GAP_AWARE:
        n = 1
        for s in used:
            if s == n:
                n += 1
            elif s > n:
                break
        return n
    return (max(used) + 1) if used else 1


@dataclass
class ComplianceResult:
    device: object
    status: str
    current_name: str
    expected_name: Optional[str] = None
    site_code: Optional[str] = None
    facility_code: Optional[str] = None
    location_code: Optional[str] = None
    floor_code: Optional[str] = None
    pattern: Optional[NamingPattern] = None
    reason: str = ""


def _pattern_uses(template: str, token: str) -> bool:
    return f"{{{token}}}" in template


def check_device(device, seq_cache=None) -> ComplianceResult:
    current_name = device.name or ""
    pattern = get_pattern_for_device(device)

    if not pattern:
        return ComplianceResult(
            device=device,
            status=ComplianceStatusChoices.UNCONFIGURED,
            current_name=current_name,
            reason="no naming pattern for this device role",
        )

    needs_site = _pattern_uses(pattern.template, "SITE")
    needs_facility = _pattern_uses(pattern.template, "FACILITY")
    needs_location = _pattern_uses(pattern.template, "LOCATION")
    needs_floor = _pattern_uses(pattern.template, "FLOOR")

    site_code = get_site_level_code(device) if needs_site else None
    facility_code = get_facility_code_for_device(device) if needs_facility else None
    location_code = get_location_code_for_device(device) if needs_location else None
    floor_code = get_floor_code_for_device(device) if needs_floor else None

    missing = []
    if needs_site and not site_code:
        missing.append("no Site code registered")
    if needs_facility and not facility_code:
        missing.append("no Facility code registered on this device or any ancestor location")
    if needs_location and not location_code:
        missing.append("no Building code registered on this device or any ancestor location")
    if needs_floor and not floor_code:
        missing.append("no Floor code registered on this device or any ancestor location")
    if missing:
        return ComplianceResult(
            device=device,
            status=ComplianceStatusChoices.UNCONFIGURED,
            current_name=current_name,
            pattern=pattern,
            reason="; ".join(missing),
        )

    regex = build_name_regex(pattern.template, pattern.seq_width, site_code=site_code,
                              facility_code=facility_code, location_code=location_code, floor_code=floor_code)
    if regex.match(current_name):
        return ComplianceResult(
            device=device,
            status=ComplianceStatusChoices.COMPLIANT,
            current_name=current_name,
            expected_name=current_name,
            site_code=site_code,
            facility_code=facility_code,
            location_code=location_code,
            floor_code=floor_code,
            pattern=pattern,
        )

    key = (site_code, facility_code, location_code, floor_code, pattern.pk)
    if seq_cache is not None and key in seq_cache:
        used_seqs = seq_cache[key]
    else:
        used_seqs = _used_sequences(pattern, site_code=site_code, facility_code=facility_code,
                                     location_code=location_code, floor_code=floor_code)

    seq = next_sequence(used_seqs, pattern.seq_policy)
    expected = render_name(pattern.template, seq, pattern.seq_width, site_code=site_code,
                            facility_code=facility_code, location_code=location_code, floor_code=floor_code)

    return ComplianceResult(
        device=device,
        status=ComplianceStatusChoices.NONCOMPLIANT,
        current_name=current_name,
        expected_name=expected,
        site_code=site_code,
        facility_code=facility_code,
        location_code=location_code,
        floor_code=floor_code,
        pattern=pattern,
        reason="Name does not match the pattern for its role/site/facility/location/floor.",
    )


def _used_sequences(pattern: NamingPattern, site_code: str = None, facility_code: str = None,
                     location_code: str = None, floor_code: str = None):
    from dcim.models import Device

    regex = build_name_regex(pattern.template, pattern.seq_width, site_code=site_code,
                              facility_code=facility_code, location_code=location_code, floor_code=floor_code)
    seqs = set()
    for name in Device.objects.filter(role_id=pattern.device_role_id).values_list("name", flat=True):
        if not name:
            continue
        m = regex.match(name)
        if m:
            seqs.add(int(m.group("seq")))
    return seqs


def build_seq_cache(devices):
    cache = {}
    patterns = {p.device_role_id: p for p in NamingPattern.objects.all()}

    for device in devices:
        role_id = getattr(device, "role_id", None)
        pattern = patterns.get(role_id)
        if not pattern:
            continue

        needs_site = _pattern_uses(pattern.template, "SITE")
        needs_facility = _pattern_uses(pattern.template, "FACILITY")
        needs_location = _pattern_uses(pattern.template, "LOCATION")
        needs_floor = _pattern_uses(pattern.template, "FLOOR")
        site_code = get_site_level_code(device) if needs_site else None
        facility_code = get_facility_code_for_device(device) if needs_facility else None
        location_code = get_location_code_for_device(device) if needs_location else None
        floor_code = get_floor_code_for_device(device) if needs_floor else None

        if ((needs_site and not site_code) or (needs_facility and not facility_code)
                or (needs_location and not location_code) or (needs_floor and not floor_code)):
            continue

        key = (site_code, facility_code, location_code, floor_code, pattern.pk)
        if key not in cache:
            cache[key] = _used_sequences(pattern, site_code=site_code, facility_code=facility_code,
                                          location_code=location_code, floor_code=floor_code)
    return cache


def _used_rack_sequences(pattern, site_code=None, facility_code=None, location_code=None, floor_code=None):
    from dcim.models import Rack

    regex = build_name_regex(pattern.template, pattern.seq_width, site_code=site_code,
                              facility_code=facility_code, location_code=location_code, floor_code=floor_code)
    seqs = set()
    for name in Rack.objects.all().values_list("name", flat=True):
        if not name:
            continue
        m = regex.match(name)
        if m:
            seqs.add(int(m.group("seq")))
    return seqs


def check_rack(rack, pattern=None, seq_cache=None) -> ComplianceResult:
    """
    Same logic as check_device, but for a Rack against a RackNamingPattern.
    Racks have no Role, so the pattern isn't looked up per-object here -
    the caller passes the single (or chosen) RackNamingPattern to use.
    """
    current_name = rack.name or ""

    if pattern is None:
        pattern = RackNamingPattern.objects.first()
    if not pattern:
        return ComplianceResult(
            device=rack,
            status=ComplianceStatusChoices.UNCONFIGURED,
            current_name=current_name,
            reason="no Rack naming pattern configured",
        )

    needs_site = _pattern_uses(pattern.template, "SITE")
    needs_facility = _pattern_uses(pattern.template, "FACILITY")
    needs_location = _pattern_uses(pattern.template, "LOCATION")
    needs_floor = _pattern_uses(pattern.template, "FLOOR")

    site_code = get_site_level_code(rack) if needs_site else None
    facility_code = get_facility_code_for_device(rack) if needs_facility else None
    location_code = get_location_code_for_device(rack) if needs_location else None
    floor_code = get_floor_code_for_device(rack) if needs_floor else None

    missing = []
    if needs_site and not site_code:
        missing.append("no Site code registered")
    if needs_facility and not facility_code:
        missing.append("no Facility code registered on this rack or any ancestor location")
    if needs_location and not location_code:
        missing.append("no Building code registered on this rack or any ancestor location")
    if needs_floor and not floor_code:
        missing.append("no Floor code registered on this rack or any ancestor location")
    if missing:
        return ComplianceResult(
            device=rack,
            status=ComplianceStatusChoices.UNCONFIGURED,
            current_name=current_name,
            pattern=pattern,
            reason="; ".join(missing),
        )

    regex = build_name_regex(pattern.template, pattern.seq_width, site_code=site_code,
                              facility_code=facility_code, location_code=location_code, floor_code=floor_code)
    if regex.match(current_name):
        return ComplianceResult(
            device=rack,
            status=ComplianceStatusChoices.COMPLIANT,
            current_name=current_name,
            expected_name=current_name,
            site_code=site_code,
            facility_code=facility_code,
            location_code=location_code,
            floor_code=floor_code,
            pattern=pattern,
        )

    key = (site_code, facility_code, location_code, floor_code, pattern.pk)
    if seq_cache is not None and key in seq_cache:
        used_seqs = seq_cache[key]
    else:
        used_seqs = _used_rack_sequences(pattern, site_code=site_code, facility_code=facility_code,
                                          location_code=location_code, floor_code=floor_code)

    seq = next_sequence(used_seqs, pattern.seq_policy)
    expected = render_name(pattern.template, seq, pattern.seq_width, site_code=site_code,
                            facility_code=facility_code, location_code=location_code, floor_code=floor_code)

    return ComplianceResult(
        device=rack,
        status=ComplianceStatusChoices.NONCOMPLIANT,
        current_name=current_name,
        expected_name=expected,
        site_code=site_code,
        facility_code=facility_code,
        location_code=location_code,
        floor_code=floor_code,
        pattern=pattern,
        reason="Name does not match the Rack naming pattern.",
    )


def build_rack_seq_cache(racks, pattern=None):
    if pattern is None:
        pattern = RackNamingPattern.objects.first()
    if not pattern:
        return {}

    cache = {}
    needs_site = _pattern_uses(pattern.template, "SITE")
    needs_facility = _pattern_uses(pattern.template, "FACILITY")
    needs_location = _pattern_uses(pattern.template, "LOCATION")
    needs_floor = _pattern_uses(pattern.template, "FLOOR")

    for rack in racks:
        site_code = get_site_level_code(rack) if needs_site else None
        facility_code = get_facility_code_for_device(rack) if needs_facility else None
        location_code = get_location_code_for_device(rack) if needs_location else None
        floor_code = get_floor_code_for_device(rack) if needs_floor else None

        if ((needs_site and not site_code) or (needs_facility and not facility_code)
                or (needs_location and not location_code) or (needs_floor and not floor_code)):
            continue

        key = (site_code, facility_code, location_code, floor_code, pattern.pk)
        if key not in cache:
            cache[key] = _used_rack_sequences(pattern, site_code=site_code, facility_code=facility_code,
                                               location_code=location_code, floor_code=floor_code)
    return cache


def resolve_collisions(results):
    """
    Given a list of ComplianceResult for non-compliant devices, detect when
    two or more would be assigned the identical proposed name and instead
    of blocking them, hand out sequential numbers so each gets a unique,
    valid name - the same way a person renaming them one at a time would.
    """
    from collections import defaultdict

    groups = defaultdict(list)
    for r in results:
        if r.status != ComplianceStatusChoices.NONCOMPLIANT or not r.expected_name or not r.pattern:
            continue
        key = (r.site_code, r.facility_code, r.location_code, r.floor_code, r.pattern.pk)
        groups[key].append(r)

    for key, group in groups.items():
        if len(group) <= 1:
            continue

        pattern_obj = group[0].pattern
        group.sort(key=lambda r: r.current_name or "")

        used = set(_used_sequences(
            pattern_obj, site_code=group[0].site_code, facility_code=group[0].facility_code,
            location_code=group[0].location_code, floor_code=group[0].floor_code,
        ))

        seq = 1
        for r in group:
            while seq in used:
                seq += 1
            r.expected_name = render_name(
                pattern_obj.template, seq, pattern_obj.seq_width,
                site_code=r.site_code, facility_code=r.facility_code,
                location_code=r.location_code, floor_code=r.floor_code,
            )
            used.add(seq)
            seq += 1
    return results
