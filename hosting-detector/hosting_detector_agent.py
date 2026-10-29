"""
Hosting Platform Detector Agent
================================
An intelligent agent that identifies the web hosting platform, cloud infrastructure,
or website builder behind any given website URL or domain name.

Example:
    User input: "www.example1.com"
    Output:     "www.example1.com" hosted by 'Hostinger' (https://www.hostinger.com/)

Features & Architecture:
- Multi-layer fingerprinting:
    1. DNS & Infrastructure (DoH - DNS over HTTPS, NS, CNAME, A/AAAA, TXT/SPF, SOA)
    2. HTTP/HTTPS Response Headers & Cookies (Server, X-Powered-By, provider tokens)
    3. HTML Inspection (meta generator tags, distinctive static CDN assets, footers)
    4. IP Geolocation, ASN, and Reverse DNS / PTR
    5. CDN & Reverse-Proxy Disambiguation (e.g. Hostinger / Shopify behind Cloudflare)
- Compliance with Project GEMINI.md Learned Rules:
    - Rule 1: Thread-safe logging with threading.Lock() and immediate flush.
    - Rule 2: Per-line json.JSONDecodeError handling when reading JSONL logs.
    - Rule 3: Subprocess fallback to curl.exe on 429/403 or TLS fingerprint blocks.
    - Rule 4: Dynamic module loading via importlib.util.spec_from_file_location.
- Command-line interface with interactive, one-shot, batch, verbose, and JSON modes.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import socket
import subprocess
import sys
import threading
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

# Optional third-party imports with graceful fallbacks
try:
    import requests
except ImportError:
    requests = None

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None


# ==============================================================================
# Thread-safe logger and status recorder (Rule 1 & Rule 2)
# ==============================================================================

class ThreadSafeStatusLogger:
    """Thread-safe status logger that flushes immediately to disk (Rule 1)."""
    def __init__(self, log_path: Optional[str] = None):
        self.log_path = log_path
        self._lock = threading.Lock()

    def log_event(self, event: Dict[str, Any]) -> None:
        if not self.log_path:
            return
        with self._lock:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(event, ensure_ascii=False) + "\n")
                f.flush()

    @staticmethod
    def read_jsonl_safely(file_path: str) -> List[Dict[str, Any]]:
        """Read a JSONL file line-by-line handling malformed lines safely (Rule 2)."""
        records: List[Dict[str, Any]] = []
        if not os.path.exists(file_path):
            return records
        with open(file_path, "r", encoding="utf-8") as f:
            for line_no, line in enumerate(f, start=1):
                clean_line = line.strip()
                if not clean_line:
                    continue
                try:
                    records.append(json.loads(clean_line))
                except json.JSONDecodeError:
                    # Never crash the reader on malformed lines
                    continue
        return records


# ==============================================================================
# Dynamic Module Loader (Rule 4)
# ==============================================================================

def load_agent_module(module_path: str, module_name: Optional[str] = None):
    """
    Dynamically loads a module from a file path (including kebab-case names)
    using importlib.util.spec_from_file_location (GEMINI.md Rule 4).
    """
    path = Path(module_path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"Module file not found: {path}")

    mod_name = module_name or path.stem.replace("-", "_")
    spec = importlib.util.spec_from_file_location(mod_name, str(path))
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load module specification from: {path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = module
    spec.loader.exec_module(module)
    return module


# ==============================================================================
# Hosting Provider Knowledge Base
# ==============================================================================

@dataclass
class HostingProviderSignature:
    name: str
    url: str
    category: str = "Hosting"  # Hosting, Cloud, SiteBuilder, ECommerce, CDN
    ns_patterns: List[str] = field(default_factory=list)
    cname_patterns: List[str] = field(default_factory=list)
    header_patterns: Dict[str, str] = field(default_factory=dict)
    cookie_patterns: List[str] = field(default_factory=list)
    meta_generators: List[str] = field(default_factory=list)
    asset_domains: List[str] = field(default_factory=list)
    asn_patterns: List[str] = field(default_factory=list)
    ptr_patterns: List[str] = field(default_factory=list)
    soa_patterns: List[str] = field(default_factory=list)
    txt_patterns: List[str] = field(default_factory=list)


HOSTING_PROVIDERS: List[HostingProviderSignature] = [
    # --- Primary Shared & Managed Hosting ---
    HostingProviderSignature(
        name="Hostinger",
        url="https://www.hostinger.com/",
        category="Hosting",
        ns_patterns=[
            r"hostinger\.", r"main-hosting\.com", r"dns-parking\.com",
            r"hostingermail\.com"
        ],
        cname_patterns=[r"hostinger\.", r"main-hosting\.com"],
        header_patterns={
            "x-hostinger-cache": r".+",
            "x-h-cache": r".+",
            "x-h-client-ip": r".+",
            "server": r"litespeed",  # LiteSpeed with Hostinger indicators
        },
        cookie_patterns=[r"hostinger", r"hostingerDeviceId"],
        asset_domains=[r"hostinger\.", r"assets\.hostinger\.com"],
        asn_patterns=[r"hostinger", r"as47583", r"as206300"],
        ptr_patterns=[r"hostinger\.", r"main-hosting\.com"],
        soa_patterns=[r"hostinger\.", r"main-hosting\.com"],
        txt_patterns=[r"spf\.hostinger\.com", r"spf\.main-hosting\.com"],
    ),
    HostingProviderSignature(
        name="Shopify",
        url="https://www.shopify.com/",
        category="ECommerce",
        cname_patterns=[r"shops\.myshopify\.com", r"myshopify\.com"],
        header_patterns={
            "x-shopify-stage": r".+",
            "x-sorting-hat-podid": r".+",
            "x-storefront-renderer-rendered": r".+",
            "x-shopid": r".+",
        },
        meta_generators=[r"shopify"],
        asset_domains=[r"cdn\.shopify\.com", r"shopify\.com"],
        asn_patterns=[r"shopify"],
    ),
    HostingProviderSignature(
        name="Vercel",
        url="https://vercel.com/",
        category="Cloud",
        ns_patterns=[r"vercel-dns\.com"],
        cname_patterns=[r"cname\.vercel-dns\.com", r"vercel\.app"],
        header_patterns={
            "server": r"^vercel$",
            "x-vercel-id": r".+",
            "x-vercel-cache": r".+",
        },
        asn_patterns=[r"vercel"],
    ),
    HostingProviderSignature(
        name="Netlify",
        url="https://www.netlify.com/",
        category="Cloud",
        ns_patterns=[r"netlify\.com", r"nsone\.net"],
        cname_patterns=[r"netlify\.app", r"netlify\.com"],
        header_patterns={
            "server": r"^netlify$",
            "x-nf-request-id": r".+",
        },
        asn_patterns=[r"netlify"],
    ),
    HostingProviderSignature(
        name="Wix",
        url="https://www.wix.com/",
        category="SiteBuilder",
        ns_patterns=[r"wixdns\.net"],
        cname_patterns=[r"pointdns\.wix\.com", r"wixsite\.com"],
        header_patterns={
            "server": r"(wix\.com|pepyaka)",
            "x-wix-request-id": r".+",
        },
        meta_generators=[r"wix\.com", r"wix"],
        asset_domains=[r"static\.wixstatic\.com", r"parastorage\.com"],
        asn_patterns=[r"wix"],
    ),
    HostingProviderSignature(
        name="Squarespace",
        url="https://www.squarespace.com/",
        category="SiteBuilder",
        ns_patterns=[r"squarespacedns\.com"],
        cname_patterns=[r"ext-cust\.squarespace\.com", r"squarespace\.com"],
        header_patterns={
            "server": r"^squarespace$",
            "x-served-by": r"squarespace",
        },
        cookie_patterns=[r"SS_MID", r"SS_cvr"],
        meta_generators=[r"squarespace"],
        asset_domains=[r"assets\.squarespace\.com", r"static1\.squarespace\.com"],
        asn_patterns=[r"squarespace"],
    ),
    HostingProviderSignature(
        name="Webflow",
        url="https://webflow.com/",
        category="SiteBuilder",
        cname_patterns=[r"proxy-ssl\.webflow\.com", r"webflow\.io"],
        header_patterns={
            "server": r"^webflow$",
        },
        meta_generators=[r"webflow"],
        asset_domains=[r"assets\.website-files\.com", r"assets-global\.website-files\.com"],
    ),
    HostingProviderSignature(
        name="WP Engine",
        url="https://wpengine.com/",
        category="Hosting",
        ns_patterns=[r"wpengine\.com"],
        cname_patterns=[r"wpenginepowered\.com", r"wpeproxy\.com", r"wpengine\.com"],
        header_patterns={
            "x-powered-by": r"wp engine",
            "wpe-backend": r".+",
        },
        asn_patterns=[r"wp engine"],
    ),
    HostingProviderSignature(
        name="Kinsta",
        url="https://kinsta.com/",
        category="Hosting",
        ns_patterns=[r"kinstadns\.com"],
        cname_patterns=[r"kinsta\.cloud"],
        header_patterns={
            "server": r"^kinsta$",
            "x-kinsta-cache": r".+",
        },
        asn_patterns=[r"kinsta"],
    ),
    HostingProviderSignature(
        name="GitHub Pages",
        url="https://pages.github.com/",
        category="Cloud",
        cname_patterns=[r"github\.io"],
        header_patterns={
            "server": r"github\.com",
            "x-github-request-id": r".+",
        },
        asn_patterns=[r"github"],
    ),
    HostingProviderSignature(
        name="GitLab Pages",
        url="https://about.gitlab.com/",
        category="Cloud",
        cname_patterns=[r"gitlab\.io"],
        header_patterns={
            "gitlab-pages": r".+",
        },
    ),
    HostingProviderSignature(
        name="SiteGround",
        url="https://www.siteground.com/",
        category="Hosting",
        ns_patterns=[r"siteground\.biz", r"siteground\.net", r"sgvps\.net"],
        header_patterns={
            "x-siteground-cache": r".+",
            "x-proxy-cache": r".+",
        },
        ptr_patterns=[r"siteground\.biz", r"siteground\.net"],
        asn_patterns=[r"siteground", r"as49453", r"as60476"],
    ),
    HostingProviderSignature(
        name="Bluehost",
        url="https://www.bluehost.com/",
        category="Hosting",
        ns_patterns=[r"bluehost\.com", r"hostmonster\.com"],
        ptr_patterns=[r"bluehost\.com"],
        asn_patterns=[r"unified layer", r"bluehost"],
    ),
    HostingProviderSignature(
        name="HostGator",
        url="https://www.hostgator.com/",
        category="Hosting",
        ns_patterns=[r"hostgator\.com"],
        ptr_patterns=[r"hostgator\.com"],
        asn_patterns=[r"hostgator"],
    ),
    HostingProviderSignature(
        name="GoDaddy",
        url="https://www.godaddy.com/",
        category="Hosting",
        ns_patterns=[r"domaincontrol\.com", r"godaddy\.com"],
        header_patterns={
            "server": r"godaddy\.com",
        },
        ptr_patterns=[r"secureserver\.net"],
        asn_patterns=[r"godaddy", r"as26496", r"as398101"],
        txt_patterns=[r"secureserver\.net"],
    ),
    HostingProviderSignature(
        name="Namecheap",
        url="https://www.namecheap.com/",
        category="Hosting",
        ns_patterns=[r"registrar-servers\.com", r"namecheaphosting\.com"],
        asn_patterns=[r"namecheap", r"as22612"],
    ),
    HostingProviderSignature(
        name="DreamHost",
        url="https://www.dreamhost.com/",
        category="Hosting",
        ns_patterns=[r"dreamhost\.com"],
        header_patterns={
            "x-data-host": r".+",
        },
        ptr_patterns=[r"dreamhost\.com"],
        asn_patterns=[r"dreamhost", r"as26347"],
    ),
    HostingProviderSignature(
        name="A2 Hosting",
        url="https://www.a2hosting.com/",
        category="Hosting",
        ns_patterns=[r"a2hosting\.com"],
        header_patterns={
            "x-served-by": r"a2 hosting",
        },
        asn_patterns=[r"a2 hosting"],
    ),
    HostingProviderSignature(
        name="InMotion Hosting",
        url="https://www.inmotionhosting.com/",
        category="Hosting",
        ns_patterns=[r"inmotionhosting\.com"],
        asn_patterns=[r"inmotion"],
    ),
    HostingProviderSignature(
        name="Liquid Web",
        url="https://www.liquidweb.com/",
        category="Hosting",
        ns_patterns=[r"liquidweb\.com"],
        asn_patterns=[r"liquid web"],
    ),
    HostingProviderSignature(
        name="Amazon Web Services (AWS)",
        url="https://aws.amazon.com/",
        category="Cloud",
        ns_patterns=[r"awsdns-.*\.com", r"awsdns-.*\.net", r"awsdns-.*\.org", r"awsdns-.*\.co\.uk"],
        cname_patterns=[
            r"amazonaws\.com", r"cloudfront\.net", r"elasticbeanstalk\.com",
            r"s3-website-.*\.amazonaws\.com"
        ],
        header_patterns={
            "server": r"(amazons3|cloudfront)",
            "x-amz-cf-id": r".+",
            "x-amzn-trace-id": r".+",
        },
        ptr_patterns=[r"compute-1\.amazonaws\.com", r"cloudfront\.net"],
        asn_patterns=[r"amazon\.com", r"amazon data services", r"as16509", r"as14618"],
    ),
    HostingProviderSignature(
        name="Google Cloud Platform (GCP)",
        url="https://cloud.google.com/",
        category="Cloud",
        ns_patterns=[r"googledomains\.com"],
        cname_patterns=[
            r"appspot\.com", r"c\.storage\.googleapis\.com", r"run\.app",
            r"ghs\.googlehosted\.com"
        ],
        header_patterns={
            "server": r"(google frontend|gse|gws)",
        },
        ptr_patterns=[r"bc\.googleusercontent\.com", r"1e100\.net"],
        asn_patterns=[r"google llc", r"google cloud", r"as15169", r"as396982"],
    ),
    HostingProviderSignature(
        name="Microsoft Azure",
        url="https://azure.microsoft.com/",
        category="Cloud",
        cname_patterns=[
            r"azurewebsites\.net", r"azureedge\.net", r"trafficmanager\.net",
            r"azurefd\.net"
        ],
        header_patterns={
            "x-azure-ref": r".+",
            "x-ms-request-id": r".+",
        },
        asn_patterns=[r"microsoft corporation", r"as8075"],
    ),
    HostingProviderSignature(
        name="DigitalOcean",
        url="https://www.digitalocean.com/",
        category="Cloud",
        ns_patterns=[r"digitalocean\.com"],
        ptr_patterns=[r"digitalocean\.com"],
        asn_patterns=[r"digitalocean", r"as14061"],
    ),
    HostingProviderSignature(
        name="Linode (Akamai)",
        url="https://www.linode.com/",
        category="Cloud",
        ns_patterns=[r"linode\.com"],
        ptr_patterns=[r"linode\.com", r"members\.linode\.com"],
        asn_patterns=[r"linode", r"akamai connected cloud", r"as63949"],
    ),
    HostingProviderSignature(
        name="Hetzner",
        url="https://www.hetzner.com/",
        category="Hosting",
        ns_patterns=[r"hetzner\.com", r"hetzner\.de"],
        ptr_patterns=[r"your-server\.de", r"hetzner\.de"],
        asn_patterns=[r"hetzner", r"as24940"],
    ),
    HostingProviderSignature(
        name="OVHcloud",
        url="https://www.ovhcloud.com/",
        category="Hosting",
        ns_patterns=[r"ovh\.net"],
        ptr_patterns=[r"ovh\.net"],
        asn_patterns=[r"ovh sas", r"ovh", r"as16276"],
    ),
    HostingProviderSignature(
        name="Vultr",
        url="https://www.vultr.com/",
        category="Cloud",
        ns_patterns=[r"vultr\.com"],
        ptr_patterns=[r"vultr\.com"],
        asn_patterns=[r"the constant company", r"vultr", r"as20473"],
    ),
    HostingProviderSignature(
        name="Contabo",
        url="https://contabo.com/",
        category="Hosting",
        ptr_patterns=[r"contabo\.host", r"contabo\.net"],
        asn_patterns=[r"contabo", r"as51167"],
    ),
    HostingProviderSignature(
        name="IONOS by 1&1",
        url="https://www.ionos.com/",
        category="Hosting",
        ns_patterns=[r"ui-dns\.com", r"ui-dns\.de", r"ionos\.com"],
        asn_patterns=[r"1&1 ionos", r"schlund \+ partner", r"as8560"],
    ),
    HostingProviderSignature(
        name="Heroku",
        url="https://www.heroku.com/",
        category="Cloud",
        cname_patterns=[r"herokuapp\.com"],
        header_patterns={
            "via": r"1\.1 vegur",
            "server": r"^cowboy$",
        },
    ),
    HostingProviderSignature(
        name="Render",
        url="https://render.com/",
        category="Cloud",
        cname_patterns=[r"onrender\.com"],
        header_patterns={
            "server": r"^render$",
            "x-render-origin-server": r".+",
        },
    ),
    HostingProviderSignature(
        name="Fly.io",
        url="https://fly.io/",
        category="Cloud",
        cname_patterns=[r"fly\.dev"],
        header_patterns={
            "server": r"^fly/",
            "fly-request-id": r".+",
        },
        asn_patterns=[r"fly\.io"],
    ),
    HostingProviderSignature(
        name="Pantheon",
        url="https://pantheon.io/",
        category="Hosting",
        cname_patterns=[r"pantheonsite\.io"],
        header_patterns={
            "x-pantheon-endpoint": r".+",
            "x-pantheon-sty": r".+",
        },
    ),
    HostingProviderSignature(
        name="HubSpot CMS",
        url="https://www.hubspot.com/",
        category="SiteBuilder",
        cname_patterns=[r"hubspotpagebuilder\.com"],
        header_patterns={
            "x-hubspot-correlation-id": r".+",
        },
    ),
    HostingProviderSignature(
        name="Framer",
        url="https://www.framer.com/",
        category="SiteBuilder",
        cname_patterns=[r"sites\.framer\.app", r"framer\.wiki"],
        header_patterns={
            "server": r"^framer$",
        },
        meta_generators=[r"framer"],
    ),
    HostingProviderSignature(
        name="Carrd",
        url="https://carrd.co/",
        category="SiteBuilder",
        cname_patterns=[r"carrd\.co"],
        header_patterns={
            "server": r"^carrd$",
        },
    ),
    HostingProviderSignature(
        name="Ghost(Pro)",
        url="https://ghost.org/",
        category="Publishing",
        cname_patterns=[r"ghost\.io"],
        header_patterns={
            "x-ghost-cache-status": r".+",
        },
    ),
    HostingProviderSignature(
        name="WordPress.com",
        url="https://wordpress.com/",
        category="Hosting",
        ns_patterns=[r"wordpress\.com", r"automattic\.com"],
        header_patterns={
            "x-hacker": r"automattic",
            "x-nananana": r"bat-cache",
        },
        asn_patterns=[r"automattic", r"as2635"],
    ),
    HostingProviderSignature(
        name="Firebase Hosting",
        url="https://firebase.google.com/products/hosting",
        category="Cloud",
        cname_patterns=[r"firebaseapp\.com", r"web\.app"],
    ),
    HostingProviderSignature(
        name="Fastly",
        url="https://www.fastly.com/",
        category="CDN",
        header_patterns={
            "x-fastly-request-id": r".+",
            "fastly-restarts": r".+",
        },
        asn_patterns=[r"fastly", r"as54113"],
    ),
    HostingProviderSignature(
        name="Cloudflare",
        url="https://www.cloudflare.com/",
        category="CDN",
        ns_patterns=[r"cloudflare\.com"],
        header_patterns={
            "server": r"^cloudflare$",
            "cf-ray": r".+",
        },
        asn_patterns=[r"cloudflare", r"as13335"],
    ),
]


# ==============================================================================
# Detection Result Data Structure
# ==============================================================================

@dataclass
class HostingDetectionResult:
    target_input: str
    normalized_domain: str
    platform_name: str
    platform_url: str
    confidence: float
    evidence: List[str] = field(default_factory=list)
    resolved_ips: List[str] = field(default_factory=list)
    nameservers: List[str] = field(default_factory=list)
    cnames: List[str] = field(default_factory=list)
    reverse_dns: List[str] = field(default_factory=list)
    asn_org: str = ""
    http_headers: Dict[str, str] = field(default_factory=dict)
    cdn_proxy: Optional[str] = None

    def format_summary(self) -> str:
        """
        Returns the clean, exact output format requested by user:
        "www.example1.com" hosted by 'Hostinger' (https://www.hostinger.com/)
        """
        return f'"{self.target_input}" hosted by \'{self.platform_name}\' ({self.platform_url})'

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ==============================================================================
# Core Hosting Detector Agent
# ==============================================================================

class HostingDetectorAgent:
    """
    Autonomous agent for discovering and attributing website hosting providers.
    Uses multi-layer heuristics, DNS-over-HTTPS (DoH), HTTP probe with curl.exe fallback,
    reverse DNS, and ASN lookup.
    """

    USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )

    def __init__(
        self,
        timeout: float = 6.0,
        status_logger: Optional[ThreadSafeStatusLogger] = None,
        verbose: bool = False,
    ):
        self.timeout = timeout
        self.status_logger = status_logger
        self.verbose = verbose

    # --------------------------------------------------------------------------
    # URL & Domain Normalization
    # --------------------------------------------------------------------------

    @staticmethod
    def normalize_input(raw_input: str) -> Tuple[str, str]:
        """
        Normalizes arbitrary user input into:
        (clean_target, hostname)
        e.g. "https://www.example.com/blog/" -> ("www.example.com", "www.example.com")
             "www.example.com" -> ("www.example.com", "www.example.com")
        """
        cleaned = raw_input.strip()
        if not cleaned:
            return "", ""

        # Remove surrounding quotes if user entered them
        cleaned = cleaned.strip("\"' \t\r\n")

        # Ensure scheme for urllib parsing
        candidate = cleaned
        if not re.match(r"^[a-zA-Z]+://", candidate):
            candidate = "http://" + candidate

        parsed = urlparse(candidate)
        hostname = (parsed.hostname or "").lower()

        # Clean display target
        target_display = cleaned
        # Strip protocol from display target if user provided plain host
        if not re.match(r"^[a-zA-Z]+://", cleaned):
            # user typed www.example.com
            target_display = cleaned.split("/")[0].split("?")[0]

        return target_display, hostname

    # --------------------------------------------------------------------------
    # DNS Resolution (DoH with Local & Subprocess Fallback)
    # --------------------------------------------------------------------------

    def query_doh(self, name: str, record_type: str) -> List[str]:
        """
        Queries DNS-over-HTTPS (DoH) via Google or Cloudflare.
        Returns list of string data values.
        """
        endpoints = [
            f"https://dns.google/resolve?name={name}&type={record_type}",
            f"https://cloudflare-dns.com/dns-query?name={name}&type={record_type}",
        ]
        results: List[str] = []

        for endpoint in endpoints:
            try:
                # Use requests if available, else urllib
                headers = {"Accept": "application/dns-json", "User-Agent": "curl/8.0"}
                data = None
                if requests:
                    resp = requests.get(endpoint, headers=headers, timeout=self.timeout)
                    if resp.status_code == 200:
                        data = resp.json()
                else:
                    import urllib.request
                    req = urllib.request.Request(endpoint, headers=headers)
                    with urllib.request.urlopen(req, timeout=self.timeout) as r:
                        data = json.loads(r.read().decode("utf-8"))

                if data and "Answer" in data:
                    for ans in data["Answer"]:
                        val = ans.get("data", "").strip()
                        if val:
                            results.append(val)
                    if results:
                        break
            except Exception:
                continue

        return results

    def resolve_dns_records(self, domain: str) -> Dict[str, List[str]]:
        """
        Resolves NS, CNAME, A, AAAA, SOA, and TXT records for both
        the given domain and its apex domain if subdomain is present.
        """
        records: Dict[str, List[str]] = {
            "A": [],
            "AAAA": [],
            "NS": [],
            "CNAME": [],
            "SOA": [],
            "TXT": [],
        }

        # Query primary domain
        for rtype in ["A", "NS", "CNAME", "SOA", "TXT"]:
            answers = self.query_doh(domain, rtype)
            records[rtype].extend(answers)

        # If domain has www or subdomain, also query apex domain for NS & SOA
        parts = domain.split(".")
        if len(parts) > 2:
            apex = ".".join(parts[-2:])
            if not records["NS"]:
                apex_ns = self.query_doh(apex, "NS")
                records["NS"].extend(apex_ns)
            if not records["SOA"]:
                apex_soa = self.query_doh(apex, "SOA")
                records["SOA"].extend(apex_soa)

        # Fallback to local socket resolution for A records if DoH yielded none
        if not records["A"]:
            try:
                _, _, ip_list = socket.gethostbyname_ex(domain)
                records["A"].extend(ip_list)
            except Exception:
                pass

        # Deduplicate records
        for k in records:
            records[k] = list(dict.fromkeys(records[k]))

        return records

    # --------------------------------------------------------------------------
    # Reverse DNS (PTR)
    # --------------------------------------------------------------------------

    @staticmethod
    def resolve_ptr(ip: str) -> str:
        """Looks up PTR hostname for a given IP address."""
        try:
            host, _, _ = socket.gethostbyaddr(ip)
            return host
        except Exception:
            return ""

    # --------------------------------------------------------------------------
    # IP Geolocation & ASN Query (RDAP / IP-API)
    # --------------------------------------------------------------------------

    def query_ip_asn(self, ip: str) -> Dict[str, str]:
        """Queries IP-API to discover ISP, ASN, and Organization."""
        if not ip or ip.startswith("127.") or ip == "0.0.0.0":
            return {}

        url = f"http://ip-api.com/json/{ip}?fields=status,isp,org,as,asname,reverse"
        try:
            headers = {"User-Agent": "curl/8.0"}
            if requests:
                resp = requests.get(url, headers=headers, timeout=self.timeout)
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("status") == "success":
                        return data
            else:
                import urllib.request
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=self.timeout) as r:
                    data = json.loads(r.read().decode("utf-8"))
                    if data.get("status") == "success":
                        return data
        except Exception:
            pass
        return {}

    # --------------------------------------------------------------------------
    # HTTP Probing with curl.exe Fallback (Rule 3)
    # --------------------------------------------------------------------------

    def fetch_http_fingerprint(self, domain: str) -> Tuple[Dict[str, str], str, str]:
        """
        Fetches HTTP response headers and a snippet of HTML for fingerprinting.
        Complies strictly with GEMINI.md Rule 3:
        Always provides a fallback to curl.exe via subprocess when requests encounters
        HTTP 429/403 or TLS fingerprint blocks against Cloudflare or Shopify.

        Returns: (headers_lower_dict, html_text_snippet, final_url)
        """
        target_url = f"https://{domain}"
        headers_found: Dict[str, str] = {}
        html_snippet = ""
        final_url = target_url

        use_curl_fallback = False

        # Attempt 1: Python requests
        if requests:
            try:
                session = requests.Session()
                session.headers.update({"User-Agent": self.USER_AGENT})
                response = session.get(
                    target_url,
                    timeout=self.timeout,
                    allow_redirects=True,
                    verify=True,
                )
                # Check status code for blocking
                if response.status_code in (403, 429):
                    use_curl_fallback = True
                else:
                    final_url = response.url
                    for k, v in response.headers.items():
                        headers_found[k.lower()] = v
                    html_snippet = response.text[:65536]
            except (requests.exceptions.SSLError, requests.exceptions.ConnectionError):
                use_curl_fallback = True
            except Exception:
                use_curl_fallback = True
        else:
            use_curl_fallback = True

        # Attempt 2: Fallback to curl.exe via subprocess (Rule 3)
        if use_curl_fallback:
            curl_res = self._run_curl_probe(target_url)
            if not curl_res and not target_url.startswith("http://"):
                # Try http://
                curl_res = self._run_curl_probe(f"http://{domain}")

            if curl_res:
                curl_headers, curl_body, curl_url = curl_res
                if curl_headers:
                    headers_found.update(curl_headers)
                if curl_body:
                    html_snippet = curl_body
                if curl_url:
                    final_url = curl_url

        return headers_found, html_snippet, final_url

    def _run_curl_probe(self, url: str) -> Optional[Tuple[Dict[str, str], str, str]]:
        """Executes curl.exe via subprocess to retrieve headers and initial body."""
        try:
            # -ILs follows redirects and prints headers, -k ignores SSL errors if self-signed
            cmd = [
                "curl.exe",
                "-ILs",
                "--max-time", str(int(self.timeout)),
                "-A", self.USER_AGENT,
                url
            ]
            proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=self.timeout + 2)
            if proc.returncode != 0 and not proc.stdout:
                return None

            header_text = proc.stdout
            headers: Dict[str, str] = {}
            for line in header_text.splitlines():
                if ":" in line:
                    key, val = line.split(":", 1)
                    headers[key.strip().lower()] = val.strip()

            # Optional fetch of first 16KB of body
            body_cmd = [
                "curl.exe",
                "-Ls",
                "--max-time", str(int(self.timeout)),
                "-r", "0-16384",
                "-A", self.USER_AGENT,
                url
            ]
            body_proc = subprocess.run(body_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=self.timeout + 2)
            body = body_proc.stdout or ""

            return headers, body, url
        except Exception:
            return None

    # --------------------------------------------------------------------------
    # Fingerprint Matching Engine
    # --------------------------------------------------------------------------

    def evaluate_signals(
        self,
        domain: str,
        dns_records: Dict[str, List[str]],
        headers: Dict[str, str],
        html_snippet: str,
        ptrs: List[str],
        asn_info: Dict[str, str],
    ) -> Tuple[HostingProviderSignature, float, List[str], Optional[str]]:
        """
        Scores all provider signatures against the collected signals.
        Returns: (winning_provider, confidence_score, evidence_list, cdn_proxy_detected)
        """
        scores: Dict[str, float] = {}
        evidence_map: Dict[str, List[str]] = {}

        # Look for generator in HTML
        meta_generator = ""
        if BeautifulSoup and html_snippet:
            try:
                soup = BeautifulSoup(html_snippet, "html.parser")
                gen_tag = soup.find("meta", attrs={"name": re.compile(r"generator", re.I)})
                if gen_tag and gen_tag.get("content"):
                    meta_generator = gen_tag["content"].strip().lower()
            except Exception:
                pass
        elif html_snippet:
            match = re.search(r'<meta[^>]+name=["\']generator["\'][^>]+content=["\']([^"\']+)["\']', html_snippet, re.I)
            if match:
                meta_generator = match.group(1).strip().lower()

        asn_str = (
            f"{asn_info.get('isp', '')} {asn_info.get('org', '')} "
            f"{asn_info.get('as', '')} {asn_info.get('asname', '')}"
        ).lower()

        ptr_str = " ".join(ptrs).lower()
        ns_str = " ".join(dns_records.get("NS", [])).lower()
        cname_str = " ".join(dns_records.get("CNAME", [])).lower()
        soa_str = " ".join(dns_records.get("SOA", [])).lower()
        txt_str = " ".join(dns_records.get("TXT", [])).lower()

        # Track CDN detection separately
        cdn_proxy_detected: Optional[str] = None
        if "cloudflare" in headers.get("server", "").lower() or "cf-ray" in headers:
            cdn_proxy_detected = "Cloudflare"
        elif "cloudfront" in headers.get("server", "").lower() or "x-amz-cf-id" in headers:
            cdn_proxy_detected = "Amazon CloudFront"
        elif "fastly" in headers.get("server", "").lower() or "x-fastly-request-id" in headers:
            cdn_proxy_detected = "Fastly"

        for provider in HOSTING_PROVIDERS:
            p_score = 0.0
            p_evidence: List[str] = []

            # 1. Direct Specific Headers (Score: +10.0)
            for header_name, pattern in provider.header_patterns.items():
                if header_name in headers:
                    val = headers[header_name]
                    if re.search(pattern, val, re.I):
                        # Special case: 'server: litespeed' only counts strongly for Hostinger
                        # if other Hostinger cues or LiteSpeed markers are present
                        if provider.name == "Hostinger" and header_name == "server" and "litespeed" in val.lower():
                            if any("hostinger" in s for s in [ns_str, asn_str, ptr_str, soa_str]):
                                p_score += 6.0
                                p_evidence.append(f"HTTP Server: LiteSpeed with Hostinger network")
                        else:
                            p_score += 10.0
                            p_evidence.append(f"HTTP header '{header_name}: {val}' matches {provider.name}")

            # 2. CNAME Record Match (Score: +9.0)
            for cp in provider.cname_patterns:
                if re.search(cp, cname_str, re.I):
                    p_score += 9.0
                    p_evidence.append(f"CNAME alias matches pattern '{cp}'")
                    break

            # 3. Nameserver (NS) Record Match (Score: +7.0)
            for np in provider.ns_patterns:
                if re.search(np, ns_str, re.I):
                    p_score += 7.0
                    p_evidence.append(f"Nameserver matches pattern '{np}'")
                    break

            # 4. Reverse DNS (PTR) Match (Score: +7.0)
            for pp in provider.ptr_patterns:
                if re.search(pp, ptr_str, re.I):
                    p_score += 7.0
                    p_evidence.append(f"Reverse DNS (PTR) matches '{pp}'")
                    break

            # 5. IP ASN / Organization Match (Score: +6.0)
            for ap in provider.asn_patterns:
                if re.search(ap, asn_str, re.I):
                    p_score += 6.0
                    p_evidence.append(f"IP ASN/ISP matches '{ap}' ({asn_info.get('as', '')})")
                    break

            # 6. HTML Meta Generator (Score: +6.0)
            for mg in provider.meta_generators:
                if meta_generator and re.search(mg, meta_generator, re.I):
                    p_score += 6.0
                    p_evidence.append(f"HTML meta generator '{meta_generator}'")
                    break

            # 7. SOA Record Match (Score: +5.0)
            for sp in provider.soa_patterns:
                if re.search(sp, soa_str, re.I):
                    p_score += 5.0
                    p_evidence.append(f"DNS SOA record indicates '{sp}'")
                    break

            # 8. TXT / SPF Match (Score: +5.0)
            for tp in provider.txt_patterns:
                if re.search(tp, txt_str, re.I):
                    p_score += 5.0
                    p_evidence.append(f"DNS TXT/SPF record indicates '{tp}'")
                    break

            # 9. Asset Domain footprint (Score: +4.0)
            for ad in provider.asset_domains:
                if re.search(ad, html_snippet, re.I):
                    p_score += 4.0
                    p_evidence.append(f"Asset / script domain matches '{ad}'")
                    break

            # 10. Cookie footprints (Score: +3.0)
            set_cookie_header = headers.get("set-cookie", "")
            for ck in provider.cookie_patterns:
                if re.search(ck, set_cookie_header, re.I):
                    p_score += 3.0
                    p_evidence.append(f"Cookie footprint '{ck}'")
                    break

            if p_score > 0:
                scores[provider.name] = p_score
                evidence_map[provider.name] = p_evidence

        # Disambiguation:
        # If an origin host is found alongside Cloudflare/Fastly CDN, prioritize the origin host!
        non_cdn_scores = {
            k: v for k, v in scores.items()
            if next((p.category for p in HOSTING_PROVIDERS if p.name == k), "") != "CDN"
        }

        chosen_provider_name: str
        if non_cdn_scores:
            # Pick highest scoring non-CDN provider
            chosen_provider_name = max(non_cdn_scores, key=lambda k: non_cdn_scores[k])
        elif scores:
            # Only CDN / Edge provider was detected
            chosen_provider_name = max(scores, key=lambda k: scores[k])
        else:
            # Unknown / Generic hosting fallback
            if asn_info.get("org") or asn_info.get("isp"):
                # Use ISP / ASN as fallback hosting
                org_name = asn_info.get("org") or asn_info.get("isp") or "Unknown"
                fallback_prov = HostingProviderSignature(
                    name=org_name,
                    url=f"https://www.google.com/search?q={org_name.replace(' ', '+')}+hosting",
                )
                return fallback_prov, 0.4, [f"Inferred from IP ASN: {org_name}"], cdn_proxy_detected

            fallback_prov = HostingProviderSignature(
                name="Unknown Hosting Platform",
                url="https://www.google.com/",
            )
            return fallback_prov, 0.0, ["No distinctive hosting signatures detected"], cdn_proxy_detected

        provider_obj = next(p for p in HOSTING_PROVIDERS if p.name == chosen_provider_name)
        raw_score = scores[chosen_provider_name]
        confidence = min(1.0, round(raw_score / 15.0, 2))
        return provider_obj, confidence, evidence_map[chosen_provider_name], cdn_proxy_detected

    # --------------------------------------------------------------------------
    # Main Agent Detection Method
    # --------------------------------------------------------------------------

    def detect(self, user_input: str) -> HostingDetectionResult:
        """
        Main agent entrypoint.
        Given a URL or domain string (e.g. 'www.example1.com'),
        returns a HostingDetectionResult object.
        """
        target_display, hostname = self.normalize_input(user_input)

        if not hostname:
            return HostingDetectionResult(
                target_input=user_input,
                normalized_domain="",
                platform_name="Invalid URL",
                platform_url="",
                confidence=0.0,
                evidence=["Empty or unparseable website URL provided"],
            )

        if self.verbose:
            print(f"[+] Inspecting target: {target_display} (Host: {hostname})")

        # 1. Resolve DNS records via DoH
        dns_records = self.resolve_dns_records(hostname)
        resolved_ips = dns_records.get("A", [])

        # 2. Reverse DNS lookup on resolved IPs
        ptrs: List[str] = []
        for ip in resolved_ips[:3]:
            ptr_name = self.resolve_ptr(ip)
            if ptr_name:
                ptrs.append(ptr_name)

        # 3. ASN and Organization lookup
        asn_info: Dict[str, str] = {}
        if resolved_ips:
            asn_info = self.query_ip_asn(resolved_ips[0])

        # 4. HTTP Headers and HTML Fingerprint
        headers, html_snippet, _ = self.fetch_http_fingerprint(hostname)

        # 5. Evaluate and Score Signatures
        provider, confidence, evidence, cdn_proxy = self.evaluate_signals(
            domain=hostname,
            dns_records=dns_records,
            headers=headers,
            html_snippet=html_snippet,
            ptrs=ptrs,
            asn_info=asn_info,
        )

        # Construct final result
        result = HostingDetectionResult(
            target_input=target_display,
            normalized_domain=hostname,
            platform_name=provider.name,
            platform_url=provider.url,
            confidence=confidence,
            evidence=evidence,
            resolved_ips=resolved_ips,
            nameservers=dns_records.get("NS", []),
            cnames=dns_records.get("CNAME", []),
            reverse_dns=ptrs,
            asn_org=f"{asn_info.get('as', '')} {asn_info.get('org', '')}".strip(),
            http_headers=headers,
            cdn_proxy=cdn_proxy,
        )

        # Log event if logger is attached (Rule 1)
        if self.status_logger:
            self.status_logger.log_event({
                "target": target_display,
                "platform": provider.name,
                "url": provider.url,
                "confidence": confidence,
                "evidence": evidence,
            })

        return result


# ==============================================================================
# CLI and Interactive Runner
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Hosting Platform Detector Agent - Identifies the hosting provider for any website URL.",
    )
    parser.add_argument(
        "url",
        nargs="?",
        help="Website URL or domain (e.g. 'www.example1.com'). If omitted, interactive mode starts.",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Print verbose detection steps and technical evidence.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON detection data.",
    )
    parser.add_argument(
        "--log-file",
        help="Path to an optional .jsonl status log file (thread-safe, Rule 1 compliant).",
    )
    parser.add_argument(
        "--file",
        help="Process a text file containing website URLs line-by-line.",
    )

    args = parser.parse_args()

    status_logger = ThreadSafeStatusLogger(args.log_file) if args.log_file else None
    agent = HostingDetectorAgent(verbose=args.verbose, status_logger=status_logger)

    # Mode 1: Batch file processing
    if args.file:
        file_path = Path(args.file)
        if not file_path.exists():
            print(f"Error: File '{args.file}' not found.", file=sys.stderr)
            sys.exit(1)

        with open(file_path, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]

        print(f"Processing {len(lines)} URLs from {args.file}...\n")
        for line in lines:
            res = agent.detect(line)
            if args.json:
                print(json.dumps(res.to_dict(), ensure_ascii=False))
            else:
                print(res.format_summary())
        return

    # Mode 2: Single URL provided via command line argument
    if args.url:
        result = agent.detect(args.url)
        if args.json:
            print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
        else:
            print(result.format_summary())
            if args.verbose:
                print("\nDetection Breakdown:")
                print(f"  Confidence: {result.confidence * 100:.0f}%")
                if result.cdn_proxy:
                    print(f"  CDN / Edge Proxy: {result.cdn_proxy}")
                if result.resolved_ips:
                    print(f"  IPs: {', '.join(result.resolved_ips)}")
                if result.asn_org:
                    print(f"  ASN/Org: {result.asn_org}")
                if result.nameservers:
                    print(f"  Nameservers: {', '.join(result.nameservers)}")
                if result.cnames:
                    print(f"  CNAMEs: {', '.join(result.cnames)}")
                if result.evidence:
                    print("  Evidence:")
                    for ev in result.evidence:
                        print(f"    - {ev}")
        return

    # Mode 3: Interactive Agent Loop
    print("=" * 60)
    print("🌐 Hosting Platform Detector Agent")
    print("Identifies the web hosting platform behind any website URL.")
    print("Type 'q' or 'exit' to quit.")
    print("=" * 60)

    try:
        while True:
            try:
                user_input = input("\nEnter website URL: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nGoodbye!")
                break

            if not user_input:
                continue

            if user_input.lower() in ("q", "quit", "exit"):
                print("Goodbye!")
                break

            result = agent.detect(user_input)

            if args.json:
                print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
            else:
                # Output exactly as requested by user
                print(result.format_summary())

                if args.verbose and result.evidence:
                    print("  Evidence:")
                    for ev in result.evidence:
                        print(f"    • {ev}")
    except KeyboardInterrupt:
        print("\nExiting.")


if __name__ == "__main__":
    main()
