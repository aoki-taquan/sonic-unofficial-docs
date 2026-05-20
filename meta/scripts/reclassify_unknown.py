#!/usr/bin/env python3
"""Reclassify unknown HLDs by sniffing first 300 lines of body."""
import glob
import json
import os
import re
from collections import Counter

ROOT = "/home/coder/sonic-unofficial-docs"
CACHE = f"{ROOT}/.cache/sonic-sources"
INDEX = f"{ROOT}/meta/index/hld.json"
BACKLOG = f"{ROOT}/meta/backlog"
LOG = f"{ROOT}/meta/index/_reclassify_log.json"

# Keyword dictionary per area (case-insensitive). Weighted by specificity.
KEYWORDS = {
    "routing": [
        (r"\bBGP\b", 3), (r"\bOSPF\b", 3), (r"\bISIS\b", 3),
        (r"\broute[- ]map\b", 2), (r"\bRIB\b", 2), (r"\bFIB\b", 2),
        (r"\bnext[- ]hop\b", 2), (r"\bECMP\b", 2), (r"\bBFD\b", 2),
        (r"\bbgpcfgd\b", 3), (r"\bzebra\b", 3), (r"\bfrr\b", 2),
        (r"\bstatic route\b", 2), (r"\bMPLS\b", 2), (r"\bRSVP\b", 2),
        (r"\bDHCP relay\b", 3), (r"\bDHCPv6\b", 2),
        (r"\bICMP\b", 1), (r"\bIPv6 link[- ]local\b", 3),
        (r"\bclass[- ]based forwarding\b", 3),
        (r"\bpath tracing\b", 3), (r"\bsegment routing\b", 3),
        (r"\bSRv6\b", 3), (r"\bL3 scaling\b", 2),
    ],
    "switching": [
        (r"\bVLAN\b", 3), (r"\bSTP\b", 3), (r"\bMSTP\b", 3), (r"\bRSTP\b", 3),
        (r"\bLAG\b", 2), (r"\bLACP\b", 3), (r"\bportchannel\b", 3),
        (r"\bMAC (?:learning|address)\b", 2), (r"\bFDB\b", 3),
        (r"\bL2 forwarding\b", 3), (r"\bbridge\b", 1),
        (r"\bBUM\b", 3), (r"\bstorm[- ]control\b", 3),
        (r"\bwake[- ]on[- ]lan\b", 3), (r"\bWoL\b", 3),
        (r"\b802\.1[a-zA-Z]+\b", 2), (r"\bMLAG\b", 3),
        (r"\blink event damping\b", 3),
    ],
    "overlay": [
        (r"\bVXLAN\b", 3), (r"\bEVPN\b", 3), (r"\bVNI\b", 3),
        (r"\bVRF\b", 2), (r"\bVTEP\b", 3), (r"\boverlay\b", 2),
        (r"\bdual[- ]ToR\b", 3), (r"\bactive[- ]active\b", 2),
        (r"\bactive[- ]standby\b", 2), (r"\bmuxcable\b", 3),
        (r"\bDASH\b", 3), (r"\bENI\b", 3), (r"\bsmart[- ]switch\b", 3),
        (r"\bsmartswitch\b", 3), (r"\bDPU\b", 2),
        (r"\bsend[- ]to[- ]ingress\b", 3),
    ],
    "acl-qos": [
        (r"\bACL\b", 3), (r"\bQoS\b", 3), (r"\bPFC\b", 3),
        (r"\bbuffer\b", 2), (r"\bWRED\b", 3), (r"\bECN\b", 3),
        (r"\bscheduler\b", 2), (r"\bpolicer\b", 3), (r"\bshaper\b", 2),
        (r"\bDSCP\b", 3), (r"\bTC (?:to|map)\b", 3),
        (r"\bdrop counter\b", 3), (r"\bdrop[- ]counter\b", 3),
        (r"\bdiscard\b", 1), (r"\bingress discard\b", 3),
        (r"\bDoS\b", 2), (r"\bDHCP DoS\b", 3),
        (r"\bport access control\b", 3),
        (r"\bclassif", 2),
    ],
    "system": [
        (r"\bsyslog\b", 3), (r"\bSNMP\b", 3), (r"\bNTP\b", 3),
        (r"\bTACACS\b", 3), (r"\bRADIUS\b", 3), (r"\bAAA\b", 3),
        (r"\bsystemd\b", 2), (r"\bsupervisord\b", 2),
        (r"\bcoredump\b", 2), (r"\bcore dump\b", 2),
        (r"\btechsupport\b", 2), (r"\bbanner\b", 3),
        (r"\bDNS\b", 2), (r"\bstatic DNS\b", 3),
        (r"\bZTP\b", 3), (r"\bzero[- ]touch\b", 3),
        (r"\bsysctl\b", 3), (r"\bFIPS\b", 3),
        (r"\bopenssl\b", 2), (r"\bsecure boot\b", 3),
        (r"\bpassword\b", 2), (r"\buser (?:account|password)\b", 3),
        (r"\bhealth check\b", 3), (r"\bdisk writer\b", 3),
        (r"\bboot chart\b", 3), (r"\binit script\b", 2),
    ],
    "management": [
        (r"\bgNMI\b", 3), (r"\bgNOI\b", 3), (r"\bREST API\b", 3),
        (r"\bKLISH\b", 3), (r"\bCLI\b", 1), (r"\bcommand[- ]line\b", 2),
        (r"\bconfig_db\b", 3), (r"\bCONFIG_DB\b", 3),
        (r"\bYANG\b", 3), (r"\bsonic-yang\b", 3),
        (r"\bconfig reload\b", 3), (r"\bconfig load\b", 2),
        (r"\bP4RT\b", 3), (r"\bPINS\b", 3), (r"\bp4rt\b", 3),
        (r"\bgnmi\b", 3), (r"\btelemetry\b", 2),
        (r"\bManagement (?:Framework|API|Interface)\b", 3),
        (r"\bsonic-mgmt\b", 2),
        (r"\bSB-?327\b", 2), (r"\bSB-?237\b", 2),
        (r"\bcredential management\b", 3),
    ],
    "platform": [
        (r"\bPMON\b", 3), (r"\bSAI\b", 3), (r"\btransceiver\b", 3),
        (r"\bSFP\b", 3), (r"\bQSFP\b", 3), (r"\bxcvrd\b", 3),
        (r"\bplatform[- ]daemon\b", 3), (r"\bsensord\b", 3),
        (r"\bthermal\b", 2), (r"\bfan\b", 2), (r"\bpsu\b", 2),
        (r"\bLED\b", 2), (r"\bBMC\b", 3), (r"\bIPMI\b", 3),
        (r"\bfirmware\b", 2), (r"\bFW utility\b", 3),
        (r"\bfw[- ]utility\b", 3),
        (r"\bFEC\b", 3), (r"\bport FEC\b", 3),
        (r"\bmedia[- ]based\b", 3), (r"\bport setting\b", 2),
        (r"\bs3ip\b", 3), (r"\bsysfs\b", 2),
        (r"\bLPO\b", 3), (r"\bdebug register\b", 3),
        (r"\bliquid cooling\b", 3), (r"\bleakage\b", 3),
        (r"\bTPID\b", 3), (r"\bport naming\b", 3),
        (r"\bdynamic port\b", 2), (r"\badd.{0,5}del.{0,5}port\b", 2),
        (r"\bfast[- ]link[- ]up\b", 3),
        (r"\bfabric port\b", 3),
        (r"\bvoq\b", 3), (r"\bVOQ\b", 3),
        (r"\b1-?6T\b", 2),
    ],
    "internals": [
        (r"\borchagent\b", 3), (r"\bsyncd\b", 3), (r"\bswss\b", 3),
        (r"\bAPP_DB\b", 3), (r"\bSTATE_DB\b", 3), (r"\bASIC_DB\b", 3),
        (r"\bredis\b", 2), (r"\bsairedis\b", 3),
        (r"\bsynchronous mode\b", 3),
        (r"\bflexcounter\b", 3), (r"\bcounter\b", 1),
        (r"\bicmp.{0,10}offload\b", 3),
        (r"\bdebug.{0,10}dump\b", 2), (r"\bdump utility\b", 3),
        (r"\bpacketio\b", 3),
        (r"\bcounter initialization\b", 3),
        (r"\baggregate.{0,5}counter\b", 3),
        (r"\bbyte.{0,5}packet rate\b", 3),
        (r"\bport utilization\b", 3),
    ],
    "architecture": [
        (r"\barchitecture\b", 2), (r"\bhigh[- ]level design\b", 1),
        (r"\brelease note\b", 3), (r"\btest plan\b", 3),
        (r"\btest case\b", 2), (r"\bbuild system\b", 3),
        (r"\bbuild improvement\b", 3), (r"\bbuild profile\b", 3),
        (r"\breproduce.{0,5}build\b", 3),
        (r"\bsplit build\b", 3),
        (r"\bGNS3\b", 3), (r"\bSONiC[- ]VS\b", 3),
        (r"\bKVM\b", 2), (r"\buser manual\b", 3),
        (r"\bconfiguration methods\b", 3),
        (r"\bapplication extension\b", 3),
        (r"\breliable TSA\b", 3), (r"\bTSA\b", 2),
        (r"\bTWAMP\b", 3),
        (r"\bSFlow\b", 3), (r"\bsflow\b", 3),
        (r"\bscope\b", 1), (r"\bintroduction\b", 1),
        (r"\bIP address assignment\b", 3),
        (r"\bgraceful shutdown\b", 3),
    ],
    "reference": [
        (r"\breference\b", 1),
    ],
}

# STRONG path/title overrides — these always win over keyword scoring
STRONG_OVERRIDES = [
    (re.compile(r"/release[- _]?notes?/|release[- _]?notes?\.md", re.I), "architecture", "strong-path:release-notes"),
    (re.compile(r"/test[- _]?plan", re.I), "architecture", "strong-path:test-plan"),
    (re.compile(r"test[- _]plan\.md", re.I), "architecture", "strong-path:test-plan"),
    (re.compile(r"/build", re.I), "architecture", "strong-path:build"),
    (re.compile(r"/ARS/", re.I), "routing", "strong-path:ARS-routing"),
    (re.compile(r"/dhcp[_-]?relay/", re.I), "routing", "strong-path:dhcp-relay"),
    (re.compile(r"/kubernetes/", re.I), "internals", "strong-path:kubernetes"),
    (re.compile(r"/layer1/", re.I), "platform", "strong-path:layer1"),
    (re.compile(r"reliable[- _]tsa|reliable_tsa", re.I), "routing", "strong-path:tsa-routing"),
    (re.compile(r"voq[_-]counter|aggregate.{0,5}voq", re.I), "internals", "strong-path:voq-counter"),
    (re.compile(r"byte.{0,5}packet|port[- ]utilization", re.I), "internals", "strong-path:counter"),
    (re.compile(r"/pins/|/p4rt/", re.I), "management", "strong-path:pins-p4rt"),
    (re.compile(r"reduce[- _]disk[- _]io|disk[- _]write", re.I), "system", "strong-path:disk-io"),
    (re.compile(r"/voq/|voq[- _]sonic", re.I), "platform", "strong-path:voq"),
    (re.compile(r"/twamp/", re.I), "system", "strong-path:twamp"),
    (re.compile(r"/sflow/", re.I), "system", "strong-path:sflow"),
    (re.compile(r"\bARS\b", re.I), "routing", "strong-path:ARS-routing-title"),
    (re.compile(r"port[- _]access[- _]control", re.I), "acl-qos", "strong-path:port-access-control"),
    (re.compile(r"password[- _]?reset|reset.{0,15}password|password.{0,15}reset|/password-reset/", re.I), "system", "strong-path:user-password"),
    (re.compile(r"rates[- _]and[- _]utilization|byte.{0,10}packet.{0,10}rate|port[- _]utilization", re.I), "internals", "strong-path:rates-counters"),
    (re.compile(r"banner", re.I), "system", "strong-path:banner"),
    (re.compile(r"introduction", re.I), "architecture", "strong-path:introduction"),
    (re.compile(r"meeting[- _]recordings|l1-meetings", re.I), "architecture", "strong-path:meetings"),
    (re.compile(r"ip[- _]address[- _]assignment", re.I), "system", "strong-path:ip-assign"),
    (re.compile(r"graceful[- _]shutdown", re.I), "platform", "strong-path:graceful-shutdown"),
    (re.compile(r"send[- _]to[- _]ingress", re.I), "overlay", "strong-path:send-to-ingress"),
    (re.compile(r"icmp[- _]hardware[- _]offload|icmp.{0,5}offload", re.I), "platform", "strong-path:icmp-offload"),
    (re.compile(r"sonic[- _]?dash|/dash/", re.I), "overlay", "strong-path:dash"),
    (re.compile(r"smartswitch|smart[- _]switch", re.I), "overlay", "strong-path:smartswitch"),
    (re.compile(r"dual[- _]?tor|active[- _]active|active[- _]standby", re.I), "overlay", "strong-path:dualtor"),
    (re.compile(r"bum[- _]storm|storm[- _]control", re.I), "switching", "strong-path:bum-storm"),
    (re.compile(r"layer[- _]?2[- _]forwarding", re.I), "switching", "strong-path:l2-fwd"),
    (re.compile(r"link[- _]event[- _]damping", re.I), "switching", "strong-path:link-damping"),
    (re.compile(r"wake[- _]?on[- _]?lan", re.I), "switching", "strong-path:wol"),
    (re.compile(r"ipv6[- _]link[- _]local", re.I), "routing", "strong-path:ipv6-ll"),
    (re.compile(r"class[- _]based[- _]forwarding", re.I), "routing", "strong-path:cbf"),
    (re.compile(r"path[- _]tracing", re.I), "routing", "strong-path:path-tracing"),
    (re.compile(r"l3[- _]scaling|next[- _]hop[- _]table", re.I), "routing", "strong-path:l3-scaling"),
    (re.compile(r"fips|secure[- _]boot|openssl", re.I), "system", "strong-path:security"),
    (re.compile(r"\bztp\b|zero[- _]touch", re.I), "system", "strong-path:ztp"),
    (re.compile(r"static[- _]dns", re.I), "system", "strong-path:static-dns"),
    (re.compile(r"sysctl", re.I), "system", "strong-path:sysctl"),
    (re.compile(r"boot[- _]chart", re.I), "system", "strong-path:boot-chart"),
    (re.compile(r"flexcounter|counter[- _]initialization|aggregate.{0,5}counter", re.I), "internals", "strong-path:counter-internals"),
    (re.compile(r"dump[- _]utility", re.I), "internals", "strong-path:dump-util"),
    (re.compile(r"orchagent|syncd|swss|sairedis|synchronous[- _]mode", re.I), "internals", "strong-path:internals"),
    (re.compile(r"sonic[- _]?fast[- _]link[- _]up|fast[- _]link[- _]up", re.I), "platform", "strong-path:fast-link-up"),
    (re.compile(r"port[- _]naming|tpid", re.I), "platform", "strong-path:port-naming"),
    (re.compile(r"\bbmc\b", re.I), "platform", "strong-path:bmc"),
    (re.compile(r"transceiver|xcvrd|qsfp|sfp|fec[- _]flr|port[- _]fec|media[- _]based|s3ip|liquid[- _]cooling|leakage|lpo|fabric[- _]port|1\.6t|1-6t|fw[- _]util|fw_util|firmware", re.I), "platform", "strong-path:hardware"),
    (re.compile(r"config[- _]reload|user[- _]manual|command[- _]line|application[- _]extension|configuration[- _]methods|nos[- _]configuration", re.I), "management", "strong-path:cli-mgmt"),
    (re.compile(r"acl|drop[- _]counter|ingress[- _]discard|dhcp[- _]dos|add.{0,5}del.{0,5}port", re.I), "acl-qos", "strong-path:acl-qos"),
    (re.compile(r"reliable[- _]tsa|/tsa", re.I), "routing", "strong-path:tsa"),
    (re.compile(r"k(ubernetes|vm)|gns3|sonic[- _]?vs|sonic[- _]on[- _]gns3", re.I), "architecture", "strong-path:vm-test"),
    (re.compile(r"sonic[- _]reproduceable[- _]build|reproduceable[- _]build", re.I), "architecture", "strong-path:repro-build"),
    (re.compile(r"hld[- _]name|^hld$", re.I), "architecture", "strong-path:hld-template"),
    # arp -> routing (proxy arp, gratuitous arp)
    (re.compile(r"/arp/", re.I), "routing", "strong-path:arp-routing"),
    (re.compile(r"/ptp/", re.I), "system", "strong-path:ptp"),
    (re.compile(r"/kubernetes/", re.I), "internals", "strong-path:k8s-2"),
]

# Title-only fallbacks (only apply when path didn't hit any STRONG_OVERRIDES)
TITLE_FALLBACKS = [
    (re.compile(r"^scope$|^\d+\.\s*scope$", re.I), "architecture", "title:scope"),
    (re.compile(r"^introduction$|^\d+\.\s*introduction$", re.I), "architecture", "title:introduction"),
    (re.compile(r"^hld[- _]name$|^hld$", re.I), "architecture", "title:hld-template"),
]

# Special path/title hints (soft suggestion; override only on low confidence)
PATH_HINTS = [
    (re.compile(r"test[- ]plan", re.I), "architecture", "path:test-plan"),
    (re.compile(r"/BGP/|bgp", re.I), "routing", "path:BGP"),
    (re.compile(r"/dhcp", re.I), "routing", "path:dhcp"),
    (re.compile(r"vxlan|evpn", re.I), "overlay", "path:overlay"),
    (re.compile(r"dual[- ]?tor|active[- ]active|active[- ]standby|smartswitch|smart[- ]switch|/dash", re.I), "overlay", "path:overlay"),
    (re.compile(r"/qos|/acl|/buffer|/pfc", re.I), "acl-qos", "path:qos"),
    (re.compile(r"/build", re.I), "architecture", "path:build"),
    (re.compile(r"/sai|pmon|xcvrd|transceiver|fec|tpid|liquid|fabric|fw[- ]?util|firmware|s3ip|voq", re.I), "platform", "path:platform"),
    (re.compile(r"/p4rt|pins|gnmi|yang|klish|cli|mgmt", re.I), "management", "path:management"),
    (re.compile(r"orchagent|syncd|swss|sairedis|flexcounter|packetio|synchronous", re.I), "internals", "path:internals"),
    (re.compile(r"syslog|snmp|ntp|tacacs|radius|ztp|fips|secure[- ]boot|banner|password|sysctl|dns|boot[- ]chart|disk", re.I), "system", "path:system"),
    (re.compile(r"vlan|stp|portchannel|lacp|fdb|bum|wake[- ]on[- ]lan|storm[- ]control|link[- ]event", re.I), "switching", "path:switching"),
]

def find_source_file(repo_full, path):
    """Resolve cache file path."""
    repo = repo_full.split("/")[-1]
    candidate = os.path.join(CACHE, repo, path)
    if os.path.exists(candidate):
        return candidate
    return None

def sniff(text):
    """Return (area, matched_terms, confidence, scores)."""
    scores = Counter()
    matched = {a: [] for a in KEYWORDS}
    for area, kws in KEYWORDS.items():
        for pat, w in kws:
            hits = re.findall(pat, text, flags=re.IGNORECASE)
            if hits:
                scores[area] += w * len(hits)
                # store unique term sample
                term = pat.replace(r"\b", "").replace("\\", "")
                if term not in matched[area]:
                    matched[area].append(term)
    if not scores:
        return None, [], "low", scores
    top = scores.most_common(2)
    best_area, best_score = top[0]
    second_score = top[1][1] if len(top) > 1 else 0
    if best_score >= 6 and best_score >= 2 * max(second_score, 1):
        conf = "high"
    elif best_score >= 3:
        conf = "medium"
    else:
        conf = "low"
    return best_area, matched[best_area][:6], conf, scores

def classify_entry(entry, backlog_entry=None):
    repo = entry["repo"]
    path = entry["path"]
    title = entry.get("title", "")
    src = find_source_file(repo, path)
    body = ""
    if src:
        try:
            with open(src, "r", encoding="utf-8", errors="replace") as f:
                lines = []
                for i, line in enumerate(f):
                    if i >= 300:
                        break
                    lines.append(line)
                body = "".join(lines)
        except Exception:
            body = ""
    # Combine title + path + body for sniffing
    haystack = f"{title}\n{path}\n{body}"

    # Strong path overrides win first (path only — title is too noisy because v1 used first heading as title)
    for rx, a, reason in STRONG_OVERRIDES:
        if rx.search(path):
            return a, [reason], "high", "strong-path-override"

    area, terms, conf, scores = sniff(haystack)

    # If sniff result is weak/medium and title matches a fallback, prefer fallback
    if conf in ("low", "medium"):
        for rx, a, reason in TITLE_FALLBACKS:
            if rx.search(title.strip()):
                return a, [reason], "medium", "title-fallback"

    # Path hints can boost or override low confidence
    path_area = None
    path_reason = None
    for rx, a, reason in PATH_HINTS:
        if rx.search(path) or rx.search(title):
            path_area = a
            path_reason = reason
            break

    if area is None:
        if path_area:
            return path_area, [path_reason], "medium", "path-hint-only"
        return "unknown", [], "low", "no-match"

    # If confidence low and path hint exists, prefer path hint
    if conf == "low" and path_area and path_area != area:
        return path_area, [path_reason] + terms, "medium", f"path-override scores={dict(scores)}"

    # boost confidence if path hint agrees
    if path_area == area and conf != "high":
        conf = "high" if conf == "medium" else "medium"

    return area, terms, conf, f"scores={dict(scores)}"


def main():
    data = json.load(open(INDEX))
    unk_entries = [d for d in data if d.get("area_hint") == "unknown"]
    print(f"unknown entries: {len(unk_entries)}")

    # Build backlog map keyed by primary source path
    backlog_files = glob.glob(f"{BACKLOG}/_unknown/*.json")
    backlog_by_path = {}
    for bf in backlog_files:
        b = json.load(open(bf))
        ps = b.get("primary_sources", [])
        if ps:
            key = (ps[0]["repo"], ps[0]["path"])
            backlog_by_path[key] = (bf, b)

    log = []
    area_counts = Counter()
    conf_counts = Counter()

    for entry in data:
        if entry.get("area_hint") != "unknown":
            continue
        new_area, terms, conf, note = classify_entry(entry)
        old_area = entry["area_hint"]
        entry["area_hint"] = new_area
        area_counts[new_area] += 1
        conf_counts[conf] += 1

        # Update backlog file
        key = (entry["repo"], entry["path"])
        bl = backlog_by_path.get(key)
        slug = None
        if bl:
            bf, b = bl
            slug = b["slug"]
            b["area"] = new_area
            # Update target_path: docs/<area>/<slug>.md (if not unknown)
            if new_area != "unknown":
                b["target_path"] = f"docs/{new_area}/{slug}.md"
            new_dir = f"{BACKLOG}/{new_area}" if new_area != "unknown" else f"{BACKLOG}/_unknown"
            os.makedirs(new_dir, exist_ok=True)
            # Collision-safe slug: if a file already exists at the target (and is a different doc),
            # append a numeric suffix.
            target_slug = slug
            new_bf = f"{new_dir}/{target_slug}.json"
            n = 2
            # Search across ALL area dirs (not just new_dir) to prevent shared-basename confusion
            def slug_taken(s):
                for area_dir in os.listdir(BACKLOG):
                    p = f"{BACKLOG}/{area_dir}/{s}.json"
                    if os.path.exists(p) and p != bf:
                        return True
                return False
            while slug_taken(target_slug):
                target_slug = f"{slug}-{n}"
                n += 1
            new_bf = f"{new_dir}/{target_slug}.json"
            if target_slug != slug:
                b["slug"] = target_slug
                if new_area != "unknown":
                    b["target_path"] = f"docs/{new_area}/{target_slug}.md"
                slug = target_slug
            with open(new_bf, "w") as f:
                json.dump(b, f, indent=2, ensure_ascii=False)
                f.write("\n")
            if new_bf != bf:
                os.remove(bf)
        log.append({
            "slug": slug,
            "title": entry.get("title"),
            "path": entry["path"],
            "old_area": old_area,
            "new_area": new_area,
            "matched_terms": terms,
            "confidence": conf,
            "note": note,
        })

    with open(INDEX, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    with open(LOG, "w") as f:
        json.dump(log, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print("Area counts:")
    for a, c in area_counts.most_common():
        print(f"  {a}: {c}")
    print("Confidence counts:")
    for a, c in conf_counts.most_common():
        print(f"  {a}: {c}")

    # Cleanup empty _unknown dir
    unk_dir = f"{BACKLOG}/_unknown"
    if os.path.isdir(unk_dir) and not os.listdir(unk_dir):
        os.rmdir(unk_dir)
        print("removed empty _unknown dir")

if __name__ == "__main__":
    main()
