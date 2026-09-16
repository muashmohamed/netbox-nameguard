"""
Core naming logic for NameGuard, kept independent of Django views/forms so
it's easy to unit test in isolation.
"""
import re
from dataclasses import dataclass, field
from typing import Optional

from .choices import ComplianceStatusChoices, SequencePolicyChoices
from .models import NamingPattern, SiteCode

TOKEN_RE = re.compile(r"\{(SITE|SEQ)\}")


def get_site_code_for_device(device) -> Optional[str]:
    """
    Resolve a device's 4-letter site code. Location takes precedence over
    Site if both happen to be registered, since a Location is more specific.
    """
    if device.location_id:
        sc = SiteCode.objects.filter(location_id=device.location_id).first()
        if sc:
            return sc.code
    if device.site_id:
        sc = SiteCode.objects.filter(site_id=device.site_id).first()
        if sc:
            return sc.code
    return None


def get_pattern_for_device(device) -> Optional[NamingPattern]:
    role_id = getattr(device, "role_id", None) or getattr(device, "device_role_id", None)
    if not role_id:
        return None
    return NamingPattern.objects.filter(device_role_id=role_id).first()


def render_name(template: str, site_code: str, seq: int, seq_width: int) -> str:
    return template.replace("{SITE}", site_code).replace("{SEQ}", str(seq).zfill(seq_width))


def build_name_regex(template: str, site_code: str, seq_width: int) -> re.Pattern:
    """
    Turn a template like "{SITE}-CAM-{SEQ}" plus a resolved site code into a
    regex that matches any name generated from it, with the sequence number
    captured as a named group so it can be extracted back out.
    """
    pattern = ""
    last = 0
    for m in TOKEN_RE.finditer(template):
        pattern += re.escape(template[last:m.start()])
        if m.group(1) == "SITE":
            pattern += re.escape(site_code)
        else:  # SEQ
            pattern += rf"(?P<seq>\d{{{seq_width},}})"
        last = m.end()
    pattern += re.escape(template[last:])
    return re.compile(f"^{pattern}$")


def next_sequence(existing_seqs, policy: str) -> int:
    """
    Given the sequence numbers already in use for a Site + NamingPattern
    combination, return the next one to assign.
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
    pattern: Optional[NamingPattern] = None
    reason: str = ""


def check_device(device, seq_cache=None) -> ComplianceResult:
    """
    Evaluate a single device against its resolved SiteCode + NamingPattern.

    `seq_cache` is an optional dict of {(site_code, pattern_id): set(seqs)}
    used to batch this check efficiently across many devices (see
    naming.build_seq_cache below); when omitted it's computed on the fly
    for a single device, which is fine for one-off checks.
    """
    current_name = device.name or ""
    site_code = get_site_code_for_device(device)
    pattern = get_pattern_for_device(device)

    if not site_code or not pattern:
        missing = []
        if not site_code:
            missing.append("no Site/Location code registered")
        if not pattern:
            missing.append("no naming pattern for this device role")
        return ComplianceResult(
            device=device,
            status=ComplianceStatusChoices.UNCONFIGURED,
            current_name=current_name,
            reason="; ".join(missing),
        )

    regex = build_name_regex(pattern.template, site_code, pattern.seq_width)
    if regex.match(current_name):
        return ComplianceResult(
            device=device,
            status=ComplianceStatusChoices.COMPLIANT,
            current_name=current_name,
            expected_name=current_name,
            site_code=site_code,
            pattern=pattern,
        )

    # Non-compliant: figure out what the correct name *would* be, based on
    # sequence numbers already in legitimate use for this site + pattern.
    key = (site_code, pattern.pk)
    if seq_cache is not None and key in seq_cache:
        used_seqs = seq_cache[key]
    else:
        used_seqs = _used_sequences(site_code, pattern)

    seq = next_sequence(used_seqs, pattern.seq_policy)
    expected = render_name(pattern.template, site_code, seq, pattern.seq_width)

    return ComplianceResult(
        device=device,
        status=ComplianceStatusChoices.NONCOMPLIANT,
        current_name=current_name,
        expected_name=expected,
        site_code=site_code,
        pattern=pattern,
        reason="Name does not match the pattern for its role/site.",
    )


def _used_sequences(site_code: str, pattern: NamingPattern):
    from dcim.models import Device  # local import to avoid app-loading order issues

    regex = build_name_regex(pattern.template, site_code, pattern.seq_width)
    seqs = set()
    role_filter = {"role_id": pattern.device_role_id}
    for name in Device.objects.filter(**role_filter).values_list("name", flat=True):
        if not name:
            continue
        m = regex.match(name)
        if m:
            seqs.add(int(m.group("seq")))
    return seqs


def build_seq_cache(devices):
    """Pre-compute used-sequence sets for a queryset/list of devices in bulk."""
    from dcim.models import Device

    cache = {}
    patterns = {p.device_role_id: p for p in NamingPattern.objects.all()}
    site_codes = {}
    for sc in SiteCode.objects.all():
        if sc.site_id:
            site_codes[("site", sc.site_id)] = sc.code
        if sc.location_id:
            site_codes[("location", sc.location_id)] = sc.code

    for device in devices:
        role_id = getattr(device, "role_id", None)
        pattern = patterns.get(role_id)
        if not pattern:
            continue
        code = site_codes.get(("location", device.location_id)) or site_codes.get(("site", device.site_id))
        if not code:
            continue
        key = (code, pattern.pk)
        if key not in cache:
            cache[key] = _used_sequences(code, pattern)
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
