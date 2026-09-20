"""
Core naming logic for NameGuard, kept independent of Django views/forms so
it's easy to unit test in isolation.

Tokens supported in a NamingPattern's template:
  {SITE}     - the code registered on the device's Site (the whole facility).
  {LOCATION} - the code of the nearest ancestor Location tagged as a
               Building, found by walking up the Location tree.
  {FLOOR}    - the code of the nearest ancestor Location tagged as a
               Floor, found the same way, independent of {LOCATION}.
  {SEQ}      - the zero-padded sequence number.

{LOCATION} and {FLOOR} are both optional — a template only needs to use
the tokens relevant to how that Device Role's devices are actually placed.
"""
import re
from dataclasses import dataclass
from typing import Optional

from .choices import ComplianceStatusChoices, LocationKindChoices, SequencePolicyChoices
from .models import NamingPattern, SiteCode

TOKEN_RE = re.compile(r"\{(SITE|LOCATION|FLOOR|SEQ)\}")


def get_site_level_code(device) -> Optional[str]:
    """
    Resolve the code registered directly on the device's Site (the whole
    facility) — this is the {SITE} token's value. Deliberately does NOT
    look at Location; that's get_location_code_for_device's job.
    """
    if not device.site_id:
        return None
    sc = SiteCode.objects.filter(site_id=device.site_id).first()
    return sc.code if sc else None


def _walk_for_kind(device, kind: str) -> Optional[str]:
    """
    Walk up the device's Location ancestry looking for the nearest
    registered SiteCode of a specific kind (BUILDING or FLOOR). A
    differently-kinded code along the way is skipped, not treated as a
    match — e.g. walking for FLOOR keeps going past a BUILDING-kind entry
    if no FLOOR-kind entry has been found yet.
    """
    location_id = device.location_id
    depth_guard = 0
    while location_id and depth_guard < 50:  # guard against any cyclic data
        sc = SiteCode.objects.filter(location_id=location_id, location_kind=kind).first()
        if sc:
            return sc.code
        location_id = _location_parent_id(location_id)
        depth_guard += 1
    return None


def get_location_code_for_device(device) -> Optional[str]:
    """
    Resolve the {LOCATION} token's value: the nearest ancestor Location
    tagged as a Building. This means a device doesn't need its own floor
    individually registered — it inherits the nearest Building's code, the
    same way a device on "First Floor" inside "Building A" picks up
    Building A's code without "First Floor" needing its own entry.

    Returns None if the device has no Location, or no Building-kind
    ancestor (up to and including its own Location) has a registered code.
    """
    return _walk_for_kind(device, LocationKindChoices.BUILDING)


def get_floor_code_for_device(device) -> Optional[str]:
    """
    Resolve the {FLOOR} token's value: the nearest ancestor Location
    tagged as a Floor. Independent of get_location_code_for_device — a
    device can resolve a Building code, a Floor code, both, or neither,
    depending on what's registered along its Location ancestry.
    """
    return _walk_for_kind(device, LocationKindChoices.FLOOR)


def _location_parent_id(location_id):
    from dcim.models import Location  # local import to avoid app-loading order issues

    loc = Location.objects.filter(pk=location_id).only("parent_id").first()
    return loc.parent_id if loc else None


def get_pattern_for_device(device) -> Optional[NamingPattern]:
    role_id = getattr(device, "role_id", None) or getattr(device, "device_role_id", None)
    if not role_id:
        return None
    return NamingPattern.objects.filter(device_role_id=role_id).first()


def render_name(template: str, seq: int, seq_width: int, site_code: str = None, location_code: str = None, floor_code: str = None) -> str:
    out = template
    if site_code is not None:
        out = out.replace("{SITE}", site_code)
    if location_code is not None:
        out = out.replace("{LOCATION}", location_code)
    if floor_code is not None:
        out = out.replace("{FLOOR}", floor_code)
    out = out.replace("{SEQ}", str(seq).zfill(seq_width))
    return out


def build_name_regex(template: str, seq_width: int, site_code: str = None, location_code: str = None, floor_code: str = None) -> re.Pattern:
    """
    Turn a template like "{SITE}-{LOCATION}-{FLOOR}-CAM-{SEQ}" plus resolved
    codes into a regex that matches any name generated from it, with the
    sequence number captured as a named group so it can be extracted back
    out. If the template doesn't use a given token, its code is unused.
    """
    pattern = ""
    last = 0
    for m in TOKEN_RE.finditer(template):
        pattern += re.escape(template[last:m.start()])
        token = m.group(1)
        if token == "SITE":
            pattern += re.escape(site_code) if site_code else r"[^-]+"
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
    """
    Given the sequence numbers already in use for a particular scope
    (site/location/pattern combination), return the next one to assign.
    """
    used = sorted(existing_seqs)
    if policy == SequencePolicyChoices.GAP_AWARE:
        n = 1
        for s in used:
            if s == n:
                n += 1
            elif s > n:
                break
        return n
    # ALWAYS_INCREMENT: never reuse a retired number
    return (max(used) + 1) if used else 1


@dataclass
class ComplianceResult:
    device: object
    status: str
    current_name: str
    expected_name: Optional[str] = None
    site_code: Optional[str] = None
    location_code: Optional[str] = None
    floor_code: Optional[str] = None
    pattern: Optional[NamingPattern] = None
    reason: str = ""


def _pattern_uses(template: str, token: str) -> bool:
    return f"{{{token}}}" in template


def check_device(device, seq_cache=None) -> ComplianceResult:
    """
    Evaluate a single device against its resolved SiteCode(s) + NamingPattern.

    `seq_cache` is an optional dict of
    {(site_code, location_code, pattern_id): set(seqs)} used to batch this
    check efficiently across many devices (see naming.build_seq_cache
    below); when omitted it's computed on the fly for a single device,
    which is fine for one-off checks.
    """
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
    needs_location = _pattern_uses(pattern.template, "LOCATION")
    needs_floor = _pattern_uses(pattern.template, "FLOOR")

    site_code = get_site_level_code(device) if needs_site else None
    location_code = get_location_code_for_device(device) if needs_location else None
    floor_code = get_floor_code_for_device(device) if needs_floor else None

    missing = []
    if needs_site and not site_code:
        missing.append("no Site code registered")
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

    regex = build_name_regex(pattern.template, pattern.seq_width, site_code=site_code, location_code=location_code, floor_code=floor_code)
    if regex.match(current_name):
        return ComplianceResult(
            device=device,
            status=ComplianceStatusChoices.COMPLIANT,
            current_name=current_name,
            expected_name=current_name,
            site_code=site_code,
            location_code=location_code,
            floor_code=floor_code,
            pattern=pattern,
        )

    # Non-compliant: figure out what the correct name *would* be, based on
    # sequence numbers already in legitimate use for this scope.
    key = (site_code, location_code, floor_code, pattern.pk)
    if seq_cache is not None and key in seq_cache:
        used_seqs = seq_cache[key]
    else:
        used_seqs = _used_sequences(pattern, site_code=site_code, location_code=location_code, floor_code=floor_code)

    seq = next_sequence(used_seqs, pattern.seq_policy)
    expected = render_name(pattern.template, seq, pattern.seq_width, site_code=site_code, location_code=location_code, floor_code=floor_code)

    return ComplianceResult(
        device=device,
        status=ComplianceStatusChoices.NONCOMPLIANT,
        current_name=current_name,
        expected_name=expected,
        site_code=site_code,
        location_code=location_code,
        floor_code=floor_code,
        pattern=pattern,
        reason="Name does not match the pattern for its role/site/location/floor.",
    )


def _used_sequences(pattern: NamingPattern, site_code: str = None, location_code: str = None, floor_code: str = None):
    from dcim.models import Device  # local import to avoid app-loading order issues

    regex = build_name_regex(pattern.template, pattern.seq_width, site_code=site_code, location_code=location_code, floor_code=floor_code)
    seqs = set()
    for name in Device.objects.filter(role_id=pattern.device_role_id).values_list("name", flat=True):
        if not name:
            continue
        m = regex.match(name)
        if m:
            seqs.add(int(m.group("seq")))
    return seqs


def build_seq_cache(devices):
    """Pre-compute used-sequence sets for a queryset/list of devices in bulk."""
    cache = {}
    patterns = {p.device_role_id: p for p in NamingPattern.objects.all()}

    for device in devices:
        role_id = getattr(device, "role_id", None)
        pattern = patterns.get(role_id)
        if not pattern:
            continue

        needs_site = _pattern_uses(pattern.template, "SITE")
        needs_location = _pattern_uses(pattern.template, "LOCATION")
        needs_floor = _pattern_uses(pattern.template, "FLOOR")
        site_code = get_site_level_code(device) if needs_site else None
        location_code = get_location_code_for_device(device) if needs_location else None
        floor_code = get_floor_code_for_device(device) if needs_floor else None

        if (needs_site and not site_code) or (needs_location and not location_code) or (needs_floor and not floor_code):
            continue

        key = (site_code, location_code, floor_code, pattern.pk)
        if key not in cache:
            cache[key] = _used_sequences(pattern, site_code=site_code, location_code=location_code, floor_code=floor_code)
    return cache


def resolve_collisions(results):
    """
    Given a list of ComplianceResult for non-compliant devices, detect when
    two or more would be assigned the identical proposed name and flag them
    as collisions instead of silently letting one overwrite the other.
    """
    seen = {}
    for r in results:
        if r.status != ComplianceStatusChoices.NONCOMPLIANT or not r.expected_name:
            continue
        seen.setdefault(r.expected_name, []).append(r)

    for name, group in seen.items():
        if len(group) > 1:
            for r in group:
                r.status = ComplianceStatusChoices.COLLISION
                r.reason = f"{len(group)} devices would all be renamed to '{name}'."
    return results
