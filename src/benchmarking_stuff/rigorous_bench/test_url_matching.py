#!/usr/bin/env python3
"""Test the improved URL matching logic on existing report."""

import json
import re
from pathlib import Path

# Load the existing report
report_path = Path("all_reports/07001/report.md")
report = report_path.read_text()

# Load benchmark data
with open("RigorousBench.jsonl") as f:
    for line in f:
        data = json.loads(line)
        if data["uid"] == "07001":
            query_data = data
            break

# Extract URLs from report
def extract_citations(report: str) -> list[str]:
    """Extract citation URLs from report."""
    url_pattern = r'\[.*?\]\((https?://[^\s\)]+)\)'
    urls = re.findall(url_pattern, report)
    bare_pattern = r'(?<!\[)(https?://[^\s\)]+)'
    bare_urls = re.findall(bare_pattern, report)
    return list(set(urls + bare_urls))

# URL matching logic (improved version)
report_urls = extract_citations(report)
trusted_urls = query_data.get("tsl", [])

EQUIVALENT_DOMAINS = {
    "rfc-editor.org": ["datatracker.ietf.org", "ietf.org"],
    "datatracker.ietf.org": ["rfc-editor.org", "ietf.org"],
}

def normalize_url(url):
    """Normalize URL for comparison"""
    url = url.lower().rstrip("/")
    url = re.sub(r'^https?://(www\.)?', '', url)
    return url

def extract_domain_and_path(url):
    """Extract domain and path from normalized URL"""
    parts = url.split("/", 1)
    domain = parts[0]
    path = "/" + parts[1] if len(parts) > 1 else ""
    return domain, path

def urls_match(trusted_url, report_url):
    """Check if two URLs match, considering equivalent domains"""
    t_domain, t_path = extract_domain_and_path(trusted_url)
    r_domain, r_path = extract_domain_and_path(report_url)
    
    # Direct substring match (original logic)
    if trusted_url in report_url:
        return True
    
    # Check if domains are equivalent
    equivalent_domains = EQUIVALENT_DOMAINS.get(t_domain, [t_domain])
    if r_domain in equivalent_domains or t_domain == r_domain:
        # For RFC documents, match by document identifier
        if "rfc" in t_path.lower() or "draft-ietf" in t_path.lower():
            # Extract RFC/draft number
            rfc_match_t = re.search(r'(rfc\d+|draft-ietf-[\w-]+)', t_path.lower())
            rfc_match_r = re.search(r'(rfc\d+|draft-ietf-[\w-]+)', r_path.lower())
            if rfc_match_t and rfc_match_r:
                return rfc_match_t.group(1) == rfc_match_r.group(1)
        # For other paths, check if one contains the other
        if t_path and r_path and (t_path in r_path or r_path in t_path):
            return True
    
    return False

report_normalized = [normalize_url(u) for u in report_urls]
trusted_normalized = [normalize_url(u) for u in trusted_urls]

# Calculate matches
matches = []
for trusted in trusted_normalized:
    for report in report_normalized:
        if urls_match(trusted, report):
            matches.append((trusted, report))
            break

print(f"📊 URL Matching Test Results")
print(f"=" * 60)
print(f"Trusted URLs (from benchmark): {len(trusted_normalized)}")
print(f"Report URLs (from agent): {len(report_normalized)}")
print(f"Matches found: {len(matches)}")
print(f"TBO Score: {len(matches) / max(len(trusted_normalized), 1):.2%}")
print(f"\n✅ Matched URLs:")
for trusted, report in matches:
    print(f"  • {trusted[:60]}...")
    print(f"    ↔ {report[:60]}...")
print(f"\n❌ Unmatched Trusted URLs:")
for trusted in trusted_normalized:
    if not any(urls_match(trusted, report) for report in report_normalized):
        print(f"  • {trusted}")
