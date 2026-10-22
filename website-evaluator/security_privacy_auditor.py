"""
Security, Privacy & Web Hygiene Auditor
========================================
Automated crawling and evaluation engine for Defensive Security, SSL/TLS & Mixed Content,
Privacy Compliance (GDPR/CCPA), Software Version Disclosure & CMS Hygiene, HTTP Defensive
Security Headers, Form Transmission & Input Security, and Cookie Security & Attribute Hygiene.

Evaluates websites across:
1. SSL/TLS Configuration & Mixed Content Integrity (HTTPS enforcement, active/passive mixed content)
2. Privacy Compliance & Legal Consent Frameworks (GDPR/CCPA, Privacy Policy, Terms, Cookie Consent, CCPA opt-out)
3. Software Version Disclosure & CMS Hygiene (generator tags, plugin ?ver= leaks, Server/X-Powered-By)
4. HTTP Defensive Security Headers Hygiene (HSTS, CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy)
5. Form Transmission & Input Security (insecure HTTP action, GET method on sensitive forms, password autocomplete, CSRF tokens)
6. Cookie Security & Attribute Hygiene (Secure, HttpOnly, and SameSite attributes on cookies)

Generates a standardized 'security-privacy-report.txt' audit report.
"""

import sys
import os
import re
import urllib.parse
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Set
import requests
from bs4 import BeautifulSoup, Tag


@dataclass
class ActionItem:
    url: str
    issue: str
    selector: str

    def to_line(self) -> str:
        if self.selector:
            return f"{self.url} | {self.issue} at {self.selector}"
        return f"{self.url} | {self.issue}"


@dataclass
class SectionResult:
    title: str
    score: int
    action_items: List[ActionItem] = field(default_factory=list)


def generate_css_selector(tag: Tag) -> str:
    """Generate a readable, accurate CSS selector for an HTML element."""
    if not tag or not hasattr(tag, 'name'):
        return "body"

    tag_id = tag.get("id")
    if tag_id and isinstance(tag_id, str) and not re.search(r'\d{6,}', tag_id):
        return f"#{tag_id}"

    classes = tag.get("class", [])
    if isinstance(classes, list) and classes:
        clean_classes = [c for c in classes if not re.search(r'(:|\[|\]|\$|\d{6,})', c)]
        if clean_classes:
            selector = f"{tag.name}.{'.'.join(clean_classes[:2])}"
            if tag.parent and tag.parent.name not in ['[document]', 'html', 'body']:
                parent_id = tag.parent.get("id")
                if parent_id and isinstance(parent_id, str):
                    return f"#{parent_id} > {selector}"
            return selector

    name = tag.name
    if tag.parent and tag.parent.name not in ['[document]', 'html']:
        p_id = tag.parent.get("id")
        if p_id and isinstance(p_id, str):
            return f"#{p_id} > {name}"
        p_cls = tag.parent.get("class")
        if p_cls and isinstance(p_cls, list) and len(p_cls) > 0:
            return f".{p_cls[0]} {name}"
    return name


def generate_xpath(tag: Tag) -> str:
    """Generate a clean structural XPath for an element."""
    if not tag or not hasattr(tag, 'name'):
        return "/html/body"

    parts = []
    curr = tag
    while curr and curr.name not in ['[document]', None]:
        tag_id = curr.get("id") if hasattr(curr, 'get') else None
        if tag_id and isinstance(tag_id, str) and not re.search(r'\d{6,}', tag_id):
            parts.insert(0, f"//*[@id=\"{tag_id}\"]")
            break

        name = curr.name
        idx = 1
        sibling = curr.previous_sibling
        while sibling:
            if hasattr(sibling, 'name') and sibling.name == name:
                idx += 1
            sibling = sibling.previous_sibling

        parts.insert(0, f"{name}[{idx}]")
        curr = curr.parent

    if parts and parts[0].startswith("//"):
        return "/".join(parts)
    return "/" + "/".join(parts)


@dataclass
class CrawledPage:
    url: str
    html: str
    status_code: int
    headers: Dict[str, str] = field(default_factory=dict)
    raw_set_cookies: List[str] = field(default_factory=list)
    redirect_chain: List[Tuple[int, str]] = field(default_factory=list)
    soup: BeautifulSoup = field(init=False)

    def __post_init__(self):
        self.soup = BeautifulSoup(self.html, "html.parser")


class SecurityPrivacyEvaluator:
    """Evaluates crawled pages for Defensive Security, SSL/TLS, Privacy, and Web Hygiene."""

    # Common third-party marketing and analytics trackers
    TRACKER_PATTERNS = [
        "google-analytics.com", "googletagmanager.com", "gtag(", "ga(",
        "connect.facebook.net", "fbevents.js", "fbq(",
        "analytics.tiktok.com", "snap.licdn.com", "ads-twitter.com",
        "static.hotjar.com", "clarity.ms", "crazyegg.com"
    ]

    # CMP / Cookie consent patterns in scripts, classes, and IDs
    CMP_PATTERNS = [
        "onetrust", "cookiebot", "complianz", "termly", "iubenda",
        "usercentrics", "cookieyes", "trustarc", "klaro", "didomi",
        "quantcast", "osano", "axeptio", "civicuk", "cookie-consent",
        "cookie-banner", "cookie-notice", "cookie-popup", "cookie-law",
        "gdpr-banner", "privacy-banner", "cc-banner", "consent-banner",
        "cookie-bar", "accept-cookies"
    ]

    def __init__(
        self,
        base_url: str,
        pages: List[CrawledPage],
        http_redirects_to_https: bool = True,
        http_redirect_issue: Optional[str] = None
    ):
        self.base_url = base_url
        self.pages = pages
        self.http_redirects_to_https = http_redirects_to_https
        self.http_redirect_issue = http_redirect_issue

    def evaluate_ssl_and_mixed_content(self) -> SectionResult:
        """Section 1: SSL/TLS Configuration & Mixed Content Integrity."""
        title = "SSL/TLS Configuration & Mixed Content Integrity"
        action_items: List[ActionItem] = []
        score = 10

        # Check HTTP to HTTPS redirect enforcement
        if not self.http_redirects_to_https:
            issue_msg = (
                self.http_redirect_issue
                or f"Plain HTTP request ('{self.base_url.replace('https://', 'http://')}') fails to automatically redirect to HTTPS, leaving initial connection unencrypted"
            )
            action_items.append(
                ActionItem(
                    url=self.base_url,
                    issue=issue_msg,
                    selector="Network: HTTP Protocol"
                )
            )
            score -= 3

        active_mixed_count = 0
        passive_mixed_count = 0

        for page in self.pages:
            parsed = urllib.parse.urlparse(page.url)
            if parsed.scheme.lower() != "https":
                # If page itself is served over HTTP, flag it
                action_items.append(
                    ActionItem(
                        url=page.url,
                        issue="Page is served over unencrypted HTTP protocol; exposes user traffic to interception and tampering",
                        selector="Network: Transport Layer"
                    )
                )
                score -= 3
                continue

            soup = page.soup

            # Active mixed content: scripts, stylesheets, iframes, objects, embeds
            # Scripts
            for script in soup.find_all("script", src=True):
                src = script["src"].strip()
                if src.startswith("http://"):
                    active_mixed_count += 1
                    sel = generate_css_selector(script)
                    action_items.append(
                        ActionItem(
                            url=page.url,
                            issue=f"Active mixed content: External script '{src}' loaded over unencrypted HTTP on an HTTPS page",
                            selector=f"CSS: {sel}"
                        )
                    )

            # Stylesheets
            for link in soup.find_all("link", rel=lambda r: r and "stylesheet" in r):
                href = link.get("href", "").strip()
                if href.startswith("http://"):
                    active_mixed_count += 1
                    sel = generate_css_selector(link)
                    action_items.append(
                        ActionItem(
                            url=page.url,
                            issue=f"Active mixed content: External stylesheet '{href}' loaded over unencrypted HTTP on an HTTPS page",
                            selector=f"CSS: {sel}"
                        )
                    )

            # Iframes
            for iframe in soup.find_all("iframe", src=True):
                src = iframe["src"].strip()
                if src.startswith("http://"):
                    active_mixed_count += 1
                    sel = generate_css_selector(iframe)
                    action_items.append(
                        ActionItem(
                            url=page.url,
                            issue=f"Active mixed content: Iframe source '{src}' loaded over unencrypted HTTP on an HTTPS page",
                            selector=f"CSS: {sel}"
                        )
                    )

            # Passive mixed content: images, audio, video
            for img in soup.find_all("img", src=True):
                src = img["src"].strip()
                if src.startswith("http://"):
                    passive_mixed_count += 1
                    xpath = generate_xpath(img)
                    action_items.append(
                        ActionItem(
                            url=page.url,
                            issue=f"Passive mixed content: Image '{src}' loaded over unencrypted HTTP",
                            selector=f"XPath: {xpath}"
                        )
                    )

            for media in soup.find_all(["audio", "video"]):
                src = media.get("src", "").strip()
                if src.startswith("http://"):
                    passive_mixed_count += 1
                    xpath = generate_xpath(media)
                    action_items.append(
                        ActionItem(
                            url=page.url,
                            issue=f"Passive mixed content: Media asset '{src}' loaded over unencrypted HTTP",
                            selector=f"XPath: {xpath}"
                        )
                    )
                for source in media.find_all("source", src=True):
                    ssrc = source["src"].strip()
                    if ssrc.startswith("http://"):
                        passive_mixed_count += 1
                        xpath = generate_xpath(source)
                        action_items.append(
                            ActionItem(
                                url=page.url,
                                issue=f"Passive mixed content: Media source '{ssrc}' loaded over unencrypted HTTP",
                                selector=f"XPath: {xpath}"
                            )
                        )

        # Apply scoring deductions for mixed content
        if active_mixed_count > 0:
            deduction = min(5, active_mixed_count * 2)
            score -= deduction

        if passive_mixed_count > 0:
            deduction = min(3, passive_mixed_count * 1)
            score -= deduction

        score = max(0, min(10, score))
        return SectionResult(title=title, score=score, action_items=action_items)

    def evaluate_privacy_compliance(self) -> SectionResult:
        """Section 2: Privacy Compliance & Legal Consent Frameworks (GDPR/CCPA)."""
        title = "Privacy Compliance & Legal Consent Frameworks (GDPR/CCPA)"
        action_items: List[ActionItem] = []
        score = 10

        privacy_link_found = False
        terms_link_found = False
        ccpa_optout_found = False

        privacy_keywords = [
            "privacy", "privacy policy", "datenschutz", "politique de confidentialité",
            "aviso de privacidad", "data protection"
        ]
        terms_keywords = [
            "terms", "terms of service", "terms of use", "conditions of use",
            "terms & conditions", "terms and conditions", "tos"
        ]
        ccpa_keywords = [
            "do not sell", "do not sell or share", "do not sell my personal info",
            "your privacy choices", "ccpa", "cpra"
        ]

        # Scan all pages for compliance links
        for page in self.pages:
            soup = page.soup
            footer = (
                soup.find("footer")
                or soup.find(id=re.compile(r'footer', re.I))
                or soup.find(class_=re.compile(r'footer', re.I))
            )

            # Check footer and entire page
            links = soup.find_all("a", href=True)
            for a in links:
                href = a.get("href", "").lower()
                text = a.get_text().strip().lower()
                combined = f"{href} {text}"

                if any(kw in combined for kw in privacy_keywords):
                    privacy_link_found = True
                if any(kw in combined for kw in terms_keywords):
                    terms_link_found = True
                if any(kw in combined for kw in ccpa_keywords):
                    ccpa_optout_found = True

        # Check main page footer specifically for Privacy Policy
        main_page = self.pages[0] if self.pages else None
        if main_page:
            main_footer = (
                main_page.soup.find("footer")
                or main_page.soup.find(id=re.compile(r'footer', re.I))
                or main_page.soup.find(class_=re.compile(r'footer', re.I))
            )
            footer_has_privacy = False
            if main_footer:
                for a in main_footer.find_all("a", href=True):
                    comb = f"{a.get('href', '').lower()} {a.get_text().strip().lower()}"
                    if any(kw in comb for kw in privacy_keywords):
                        footer_has_privacy = True
                        break

            if not privacy_link_found:
                action_items.append(
                    ActionItem(
                        url=main_page.url,
                        issue="Site footer lacks a dedicated 'Privacy Policy' link; violates GDPR Art. 13 and CalOPPA/CCPA transparency mandates",
                        selector="XPath: //footer"
                    )
                )
                score -= 4
            elif not footer_has_privacy:
                action_items.append(
                    ActionItem(
                        url=main_page.url,
                        issue="Privacy Policy link is present on site but missing from global footer navigation where users expect compliance documentation",
                        selector="XPath: //footer"
                    )
                )
                score -= 1

            if not terms_link_found:
                action_items.append(
                    ActionItem(
                        url=main_page.url,
                        issue="Website lacks a visible 'Terms of Service' / 'Terms of Use' agreement establishing legal boundaries and acceptable use",
                        selector="XPath: //footer"
                    )
                )
                score -= 2

            if not ccpa_optout_found:
                action_items.append(
                    ActionItem(
                        url=main_page.url,
                        issue="Website lacks a 'Do Not Sell or Share My Personal Information' or 'Your Privacy Choices' link required under CCPA/CPRA",
                        selector="XPath: //footer"
                    )
                )
                score -= 1

            # Check for tracking scripts vs Cookie Consent Banner (GDPR prior-consent)
            has_trackers = False
            full_html = main_page.html.lower()

            for tracker in self.TRACKER_PATTERNS:
                if tracker.lower() in full_html:
                    has_trackers = True
                    break

            has_cmp = False
            for cmp_pat in self.CMP_PATTERNS:
                if cmp_pat.lower() in full_html:
                    has_cmp = True
                    break

            # Also check if any script tag or element id/class references CMP
            if not has_cmp:
                for elem in main_page.soup.find_all(attrs={"class": True}):
                    cls_str = " ".join(elem.get("class", [])).lower()
                    if any(p in cls_str for p in ["cookie", "consent", "gdpr", "privacy-banner"]):
                        has_cmp = True
                        break

            if has_trackers and not has_cmp:
                action_items.append(
                    ActionItem(
                        url=main_page.url,
                        issue="Non-essential third-party marketing/analytics trackers execute before user grants cookie consent; violates GDPR prior-consent mandate",
                        selector="CSS: head"
                    )
                )
                score -= 3

        score = max(0, min(10, score))
        return SectionResult(title=title, score=score, action_items=action_items)

    def evaluate_software_vulnerabilities(self) -> SectionResult:
        """Section 3: Software Version Disclosure & CMS Hygiene."""
        title = "Software Version Disclosure & CMS Hygiene"
        action_items: List[ActionItem] = []
        score = 10

        generator_flagged = False
        ver_query_flagged = 0
        server_header_flagged = False

        for page in self.pages:
            soup = page.soup

            # 1. Generator meta tag check
            generator_meta = soup.find("meta", attrs={"name": re.compile(r'^generator$', re.I)})
            if generator_meta and not generator_flagged:
                content = generator_meta.get("content", "").strip()
                # Check if it discloses version number (e.g. WordPress 6.2, Drupal 9, etc.)
                version_match = re.search(r'\b\d+(\.\d+)+\b', content)
                if version_match:
                    generator_flagged = True
                    action_items.append(
                        ActionItem(
                            url=page.url,
                            issue=f"Public HTML exposes exact CMS version ('<meta name=\"generator\" content=\"{content}\">'); assists automated botnets scanning for known CVE exploits",
                            selector="CSS: head > meta[name=\"generator\"]"
                        )
                    )
                    score -= 3
                elif content:
                    action_items.append(
                        ActionItem(
                            url=page.url,
                            issue=f"HTML discloses CMS platform in generator meta tag ('{content}'); recommend removing to minimize reconnaissance footprint",
                            selector="CSS: head > meta[name=\"generator\"]"
                        )
                    )
                    score -= 1

            # 2. Asset ?ver= query string version leaks
            scripts_and_links = []
            for sc in soup.find_all("script", src=True):
                scripts_and_links.append((sc["src"], "script", generate_css_selector(sc)))
            for lk in soup.find_all("link", href=True):
                scripts_and_links.append((lk["href"], "link", generate_css_selector(lk)))

            for asset_url, tag_type, sel in scripts_and_links:
                parsed_asset = urllib.parse.urlparse(asset_url)
                query_params = urllib.parse.parse_qs(parsed_asset.query)
                if "ver" in query_params:
                    ver_val = query_params["ver"][0]
                    # Check if ver value is a semantic version (e.g. 5.4.1, 6.2)
                    if re.match(r'^\d+(\.\d+)+', ver_val) and ver_query_flagged < 2:
                        ver_query_flagged += 1
                        clean_asset = asset_url.split("/")[-1][:40]
                        action_items.append(
                            ActionItem(
                                url=page.url,
                                issue=f"Public {tag_type} URL reveals specific installed version query ('{clean_asset}'); reveals software stack revisions to external scanners",
                                selector=f"CSS: {sel}"
                            )
                        )
                        score -= 1

            # 3. HTTP Server and X-Powered-By header disclosures
            if not server_header_flagged:
                server_hdr = page.headers.get("server", "")
                if server_hdr and re.search(r'\d+\.\d+', server_hdr):
                    server_header_flagged = True
                    action_items.append(
                        ActionItem(
                            url=page.url,
                            issue=f"HTTP response header exposes backend server software and version ('Server: {server_hdr}'); facilitates targeted exploits",
                            selector="HTTP Header: Server"
                        )
                    )
                    score -= 1

                x_powered = page.headers.get("x-powered-by", "")
                if x_powered:
                    action_items.append(
                        ActionItem(
                            url=page.url,
                            issue=f"HTTP response header discloses runtime framework ('X-Powered-By: {x_powered}'); should be disabled in production",
                            selector="HTTP Header: X-Powered-By"
                        )
                    )
                    score -= 1

        score = max(0, min(10, score))
        return SectionResult(title=title, score=score, action_items=action_items)

    def evaluate_security_headers(self) -> SectionResult:
        """Section 4: HTTP Defensive Security Headers Hygiene."""
        title = "HTTP Defensive Security Headers Hygiene"
        action_items: List[ActionItem] = []
        score = 10

        main_page = self.pages[0] if self.pages else None
        if not main_page:
            return SectionResult(title=title, score=score, action_items=action_items)

        headers = {k.lower(): v for k, v in main_page.headers.items()}
        page_url = main_page.url

        # 1. Strict-Transport-Security (HSTS)
        hsts = headers.get("strict-transport-security", "")
        if not hsts:
            action_items.append(
                ActionItem(
                    url=page_url,
                    issue="Missing 'Strict-Transport-Security' (HSTS) response header; leaves users vulnerable to SSL stripping attacks",
                    selector="HTTP Header: Strict-Transport-Security"
                )
            )
            score -= 2
        else:
            max_age_match = re.search(r'max-age=(\d+)', hsts, re.IGNORECASE)
            max_age = int(max_age_match.group(1)) if max_age_match else 0
            if max_age < 15552000 or "includesubdomains" not in hsts.lower():
                action_items.append(
                    ActionItem(
                        url=page_url,
                        issue="HSTS header is present but lacks 'includeSubDomains' directive or has duration under 6 months (recommended: max-age=31536000; includeSubDomains; preload)",
                        selector="HTTP Header: Strict-Transport-Security"
                    )
                )
                score -= 1

        # 2. Content-Security-Policy (CSP)
        csp = headers.get("content-security-policy", "")
        if not csp:
            action_items.append(
                ActionItem(
                    url=page_url,
                    issue="Missing 'Content-Security-Policy' (CSP) header; browsers have no defense against malicious script injection or data exfiltration",
                    selector="HTTP Header: Content-Security-Policy"
                )
            )
            score -= 3
        else:
            # Check for insecure CSP directives
            if "'unsafe-inline'" in csp and "nonce-" not in csp and "sha256-" not in csp:
                action_items.append(
                    ActionItem(
                        url=page_url,
                        issue="'Content-Security-Policy' uses overly permissive ''unsafe-inline'' without nonce or hash validation, reducing XSS mitigation efficacy",
                        selector="HTTP Header: Content-Security-Policy"
                    )
                )
                score -= 1
            if "'unsafe-eval'" in csp:
                action_items.append(
                    ActionItem(
                        url=page_url,
                        issue="'Content-Security-Policy' permits ''unsafe-eval'', allowing runtime string-to-code execution",
                        selector="HTTP Header: Content-Security-Policy"
                    )
                )
                score -= 1

        # 3. X-Frame-Options (Clickjacking mitigation)
        xfo = headers.get("x-frame-options", "").upper()
        frame_ancestors = "frame-ancestors" in csp.lower()
        if not xfo and not frame_ancestors:
            action_items.append(
                ActionItem(
                    url=page_url,
                    issue="Missing 'X-Frame-Options' header; site can be embedded inside invisible iframes for clickjacking attacks",
                    selector="HTTP Header: X-Frame-Options"
                )
            )
            score -= 2
        elif xfo and xfo not in ["DENY", "SAMEORIGIN"]:
            action_items.append(
                ActionItem(
                    url=page_url,
                    issue=f"Non-standard 'X-Frame-Options' header value ('{xfo}'); should be 'DENY' or 'SAMEORIGIN'",
                    selector="HTTP Header: X-Frame-Options"
                )
            )
            score -= 1

        # 4. X-Content-Type-Options (MIME sniffing prevention)
        xcto = headers.get("x-content-type-options", "").lower()
        if xcto != "nosniff":
            action_items.append(
                ActionItem(
                    url=page_url,
                    issue="Missing 'X-Content-Type-Options: nosniff' header; permits browsers to MIME-sniff response payloads into executable formats",
                    selector="HTTP Header: X-Content-Type-Options"
                )
            )
            score -= 1

        # 5. Referrer-Policy
        ref_pol = headers.get("referrer-policy", "").lower()
        if not ref_pol:
            action_items.append(
                ActionItem(
                    url=page_url,
                    issue="Missing privacy-preserving 'Referrer-Policy' header; exposes full URL paths in cross-origin request headers (recommended: 'strict-origin-when-cross-origin')",
                    selector="HTTP Header: Referrer-Policy"
                )
            )
            score -= 1
        elif ref_pol in ["unsafe-url", "no-referrer-when-downgrade"]:
            action_items.append(
                ActionItem(
                    url=page_url,
                    issue=f"Weak 'Referrer-Policy: {ref_pol}' header leaks full URL path and query parameters on cross-origin requests",
                    selector="HTTP Header: Referrer-Policy"
                )
            )
            score -= 1

        # 6. Permissions-Policy
        perm_pol = headers.get("permissions-policy", "") or headers.get("feature-policy", "")
        if not perm_pol:
            action_items.append(
                ActionItem(
                    url=page_url,
                    issue="Missing 'Permissions-Policy' header; does not restrict browser access to sensitive client hardware features (camera, microphone, geolocation)",
                    selector="HTTP Header: Permissions-Policy"
                )
            )
            score -= 1

        score = max(0, min(10, score))
        return SectionResult(title=title, score=score, action_items=action_items)

    def evaluate_form_security(self) -> SectionResult:
        """Section 5: Form Transmission & Input Security."""
        title = "Form Transmission & Input Security"
        action_items: List[ActionItem] = []
        score = 10

        total_forms = 0

        for page in self.pages:
            soup = page.soup
            forms = soup.find_all("form")
            total_forms += len(forms)

            for form in forms:
                sel = generate_css_selector(form)
                action = form.get("action", "").strip()
                method = form.get("method", "GET").strip().upper()

                # 1. Insecure form action destination
                if action.startswith("http://"):
                    action_items.append(
                        ActionItem(
                            url=page.url,
                            issue=f"Form submits user contact data to an insecure HTTP destination ('action=\"{action}\"')",
                            selector=f"CSS: {sel}"
                        )
                    )
                    score -= 4

                # 2. Check for sensitive inputs (password, credit card, email)
                inputs = form.find_all("input")
                has_password = any(inp.get("type", "").lower() == "password" for inp in inputs)
                has_sensitive_pii = any(
                    inp.get("type", "").lower() in ["password", "email", "tel"]
                    or any(k in inp.get("name", "").lower() for k in ["card", "ssn", "pass", "credit", "cvv"])
                    for inp in inputs
                )

                # Form method check: sensitive forms using GET
                if has_sensitive_pii and method == "GET":
                    action_items.append(
                        ActionItem(
                            url=page.url,
                            issue="Sensitive form uses HTTP GET method instead of POST; exposes credentials and PII in browser history and server query logs",
                            selector=f"CSS: {sel}"
                        )
                    )
                    score -= 3

                # Password input autocomplete checks
                for inp in inputs:
                    if inp.get("type", "").lower() == "password":
                        inp_sel = generate_css_selector(inp)
                        autocomplete = inp.get("autocomplete", "").lower()
                        if not autocomplete or autocomplete not in ["current-password", "new-password"]:
                            action_items.append(
                                ActionItem(
                                    url=page.url,
                                    issue="Password input field lacks 'autocomplete=\"current-password\"' or 'new-password' attribute for secure password manager integration",
                                    selector=f"CSS: {inp_sel}"
                                )
                            )
                            score -= 1

                # 3. Check for CSRF tokens on POST forms
                if method == "POST":
                    hidden_inputs = form.find_all("input", type="hidden")
                    csrf_found = any(
                        any(csrf_k in (h.get("name") or "").lower() for csrf_k in [
                            "csrf", "xsrf", "token", "_token", "authenticity_token",
                            "wp_nonce", "__requestverificationtoken"
                        ])
                        for h in hidden_inputs
                    )
                    if not csrf_found:
                        action_items.append(
                            ActionItem(
                                url=page.url,
                                issue="State-changing POST form lacks an identifiable CSRF anti-forgery token input",
                                selector=f"CSS: {sel}"
                            )
                        )
                        score -= 2

        score = max(0, min(10, score))
        return SectionResult(title=title, score=score, action_items=action_items)

    def evaluate_cookie_security(self) -> SectionResult:
        """Section 6: Cookie Security & Attribute Hygiene."""
        title = "Cookie Security & Attribute Hygiene"
        action_items: List[ActionItem] = []
        score = 10

        all_cookie_headers: List[Tuple[str, str]] = []
        for page in self.pages:
            for sc in page.raw_set_cookies:
                all_cookie_headers.append((page.url, sc))

        if not all_cookie_headers:
            return SectionResult(title=title, score=score, action_items=action_items)

        auth_cookie_patterns = [
            "sess", "auth", "token", "jwt", "id", "user", "login",
            "key", "phpsessid", "jsessionid", "connect.sid", "laravel_session"
        ]

        evaluated_cookie_names: Set[str] = set()

        for page_url, cookie_str in all_cookie_headers:
            parts = [p.strip() for p in cookie_str.split(";")]
            if not parts:
                continue

            name_val = parts[0]
            cookie_name = name_val.split("=")[0].strip() if "=" in name_val else name_val

            if cookie_name in evaluated_cookie_names:
                continue
            evaluated_cookie_names.add(cookie_name)

            lower_parts = [p.lower() for p in parts]
            attributes = set()
            samesite_val = None

            for part in lower_parts:
                if part == "secure":
                    attributes.add("secure")
                elif part == "httponly":
                    attributes.add("httponly")
                elif part.startswith("samesite"):
                    attributes.add("samesite")
                    if "=" in part:
                        samesite_val = part.split("=")[1].strip()

            is_auth_cookie = any(p in cookie_name.lower() for p in auth_cookie_patterns)

            # Check Secure attribute (if page is HTTPS)
            is_https = page_url.startswith("https://") or self.base_url.startswith("https://")
            if is_https and "secure" not in attributes:
                action_items.append(
                    ActionItem(
                        url=page_url,
                        issue=f"Cookie '{cookie_name}' is missing the 'Secure' attribute; allows transmission over unencrypted connections",
                        selector="HTTP Header: Set-Cookie"
                    )
                )
                score -= 3

            # Check HttpOnly attribute (critical for auth / session tokens)
            if is_auth_cookie and "httponly" not in attributes:
                action_items.append(
                    ActionItem(
                        url=page_url,
                        issue=f"Session/auth cookie '{cookie_name}' is missing the 'HttpOnly' flag; vulnerable to theft via Cross-Site Scripting (XSS)",
                        selector="HTTP Header: Set-Cookie"
                    )
                )
                score -= 3
            elif "httponly" not in attributes and len(all_cookie_headers) <= 3:
                # Minor note for general cookies lacking HttpOnly
                action_items.append(
                    ActionItem(
                        url=page_url,
                        issue=f"Cookie '{cookie_name}' lacks the 'HttpOnly' flag; accessible to client-side scripts",
                        selector="HTTP Header: Set-Cookie"
                    )
                )
                score -= 1

            # Check SameSite attribute
            if "samesite" not in attributes:
                action_items.append(
                    ActionItem(
                        url=page_url,
                        issue=f"Cookie '{cookie_name}' is missing the 'SameSite' attribute (recommended: 'Lax' or 'Strict'); increases vulnerability to CSRF",
                        selector="HTTP Header: Set-Cookie"
                    )
                )
                score -= 2
            elif samesite_val == "none" and "secure" not in attributes:
                action_items.append(
                    ActionItem(
                        url=page_url,
                        issue=f"Cookie '{cookie_name}' specifies 'SameSite=None' without the mandatory 'Secure' attribute",
                        selector="HTTP Header: Set-Cookie"
                    )
                )
                score -= 2

        score = max(0, min(10, score))
        return SectionResult(title=title, score=score, action_items=action_items)

    def run_full_audit(self) -> List[SectionResult]:
        """Execute all six Security, Privacy & Hygiene audit sections."""
        return [
            self.evaluate_ssl_and_mixed_content(),
            self.evaluate_privacy_compliance(),
            self.evaluate_software_vulnerabilities(),
            self.evaluate_security_headers(),
            self.evaluate_form_security(),
            self.evaluate_cookie_security(),
        ]


def extract_set_cookies(response: requests.Response) -> List[str]:
    """Safely extract all Set-Cookie header strings from a requests.Response."""
    raw_cookies: List[str] = []
    # Try urllib3 raw headers if available
    try:
        if hasattr(response, "raw") and hasattr(response.raw, "headers"):
            raw_cookies = response.raw.headers.getlist("Set-Cookie")
    except Exception:
        pass

    if not raw_cookies:
        sc = response.headers.get("Set-Cookie")
        if sc:
            raw_cookies = [sc]

    return raw_cookies


def crawl_website(
    base_url: str,
    sub_paths: Optional[List[str]] = None
) -> Tuple[List[CrawledPage], bool, Optional[str]]:
    """
    Crawl the target website, discover sub-pages (privacy, terms, login, contact),
    test HTTP-to-HTTPS redirect enforcement, and collect responses with headers and cookies.
    """
    if not base_url.startswith("http://") and not base_url.startswith("https://"):
        base_url = "https://" + base_url

    crawled_pages: List[CrawledPage] = []
    session = requests.Session()
    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    })

    # Test HTTP to HTTPS redirect enforcement
    http_redirects_to_https = True
    http_redirect_issue: Optional[str] = None

    if base_url.startswith("https://"):
        plain_http_url = base_url.replace("https://", "http://", 1)
        try:
            print(f"[*] Testing plain HTTP to HTTPS redirect enforcement at: {plain_http_url} ...")
            redirect_test = session.get(plain_http_url, timeout=8, allow_redirects=False)
            if redirect_test.status_code in [301, 302, 307, 308]:
                location = redirect_test.headers.get("Location", "")
                if not location.startswith("https://"):
                    http_redirects_to_https = False
                    http_redirect_issue = (
                        f"Plain HTTP request ('{plain_http_url}') redirected to insecure destination ('{location}') instead of HTTPS"
                    )
            elif redirect_test.status_code == 200:
                http_redirects_to_https = False
                http_redirect_issue = (
                    f"Plain HTTP request ('{plain_http_url}') responded with HTTP 200 OK without redirecting to HTTPS"
                )
        except Exception as e:
            print(f"    [!] Note: Plain HTTP test returned: {e}")

    # Fetch main base URL
    print(f"[*] Fetching base URL: {base_url} ...")
    try:
        resp = session.get(base_url, timeout=12, allow_redirects=True)
        chain = [(r.status_code, r.url) for r in resp.history]
        raw_cookies = extract_set_cookies(resp)
        crawled_pages.append(
            CrawledPage(
                url=resp.url,
                html=resp.text,
                status_code=resp.status_code,
                headers=dict(resp.headers),
                raw_set_cookies=raw_cookies,
                redirect_chain=chain,
            )
        )
    except Exception as e:
        print(f"[!] Error fetching base URL {base_url}: {e}")
        return crawled_pages, http_redirects_to_https, http_redirect_issue

    main_soup = crawled_pages[0].soup

    # Build queue of pages to crawl
    target_urls: List[str] = []
    if sub_paths:
        for p in sub_paths:
            full_url = urllib.parse.urljoin(base_url, p)
            if full_url not in target_urls and full_url != crawled_pages[0].url:
                target_urls.append(full_url)
    else:
        # Auto-discover relevant sub-pages: privacy, terms, login, contact, checkout
        target_keywords = [
            "privacy", "terms", "legal", "tos", "login", "signin",
            "contact", "checkout", "cart", "account"
        ]
        discovered: List[str] = []
        for a in main_soup.find_all("a", href=True):
            href = a["href"].strip()
            if href.startswith("#") or href.startswith("mailto:") or href.startswith("tel:") or href.startswith("javascript:"):
                continue
            for kw in target_keywords:
                if kw in href.lower():
                    full_link = urllib.parse.urljoin(base_url, href)
                    parsed_link = urllib.parse.urlparse(full_link)
                    parsed_base = urllib.parse.urlparse(base_url)
                    existing = [p.url for p in crawled_pages]
                    if parsed_link.netloc == parsed_base.netloc and full_link not in existing and full_link not in discovered:
                        discovered.append(full_link)
                    break

        target_urls.extend(discovered[:4])

    for link in target_urls:
        try:
            print(f"[*] Crawling compliance sub-page: {link} ...")
            sub_resp = session.get(link, timeout=10, allow_redirects=True)
            sub_chain = [(r.status_code, r.url) for r in sub_resp.history]
            sub_cookies = extract_set_cookies(sub_resp)
            crawled_pages.append(
                CrawledPage(
                    url=sub_resp.url,
                    html=sub_resp.text,
                    status_code=sub_resp.status_code,
                    headers=dict(sub_resp.headers),
                    raw_set_cookies=sub_cookies,
                    redirect_chain=sub_chain,
                )
            )
        except Exception as e:
            print(f"    [!] Error crawling {link}: {e}")

    return crawled_pages, http_redirects_to_https, http_redirect_issue


def format_report(base_url: str, section_results: List[SectionResult]) -> str:
    """Format audit findings into standardized Security, Privacy & Hygiene report."""
    total_score = round(sum(s.score for s in section_results) / len(section_results), 1)

    if total_score >= 8.5:
        risk_level = "Low"
    elif total_score >= 6.5:
        risk_level = "Moderate"
    elif total_score >= 4.0:
        risk_level = "High"
    else:
        risk_level = "Critical"

    lines = [
        "============================================================",
        "SECURITY, PRIVACY & WEB HYGIENE AUDIT REPORT",
        f"Target Site: {base_url}",
        "Generated By: Agency AI Security & Privacy Auditor Agent",
        "Benchmark: OWASP Top 10, NIST Guidelines & GDPR/CCPA Compliance",
        "============================================================",
        "",
    ]

    all_action_items: List[ActionItem] = []

    for section in section_results:
        lines.append(f"{section.title}: {section.score}/10")
        if section.action_items:
            for item in section.action_items:
                lines.append(item.to_line())
                all_action_items.append(item)
        else:
            lines.append(f"{base_url} | Meets all defensive security and privacy compliance standards for this capability.")
        lines.append("")

    lines.append("============================================================")
    lines.append("OVERALL SUMMARY & RECOMMENDATIONS")
    lines.append(f"Overall Security & Privacy Score: {total_score}/10")
    lines.append(f"Security Vulnerability & Privacy Risk Level: {risk_level}")
    lines.append("Primary Security & Compliance Bottlenecks:")

    # Identify top bottlenecks from lowest scoring sections
    sorted_sections = sorted(section_results, key=lambda s: s.score)
    bottleneck_idx = 1
    for s in sorted_sections[:2]:
        if s.action_items:
            lines.append(f"{bottleneck_idx}. [{s.title}] {s.action_items[0].issue}")
            bottleneck_idx += 1

    if bottleneck_idx == 1:
        lines.append("1. None identified; website meets baseline defensive security and compliance standards.")

    lines.append("Top Remediation Priorities:")
    priority_idx = 1
    seen_issues = set()
    for item in all_action_items:
        clean_issue = item.issue.strip()
        if clean_issue not in seen_issues:
            seen_issues.add(clean_issue)
            lines.append(f"{priority_idx}. {item.issue} (Ref: {item.selector})")
            priority_idx += 1
            if priority_idx > 3:
                break

    if priority_idx == 1:
        lines.append("1. Maintain continuous defensive header and TLS certificate hygiene.")

    lines.append("============================================================")
    lines.append("END OF REPORT")
    lines.append("============================================================")

    return "\n".join(lines)


def run_audit(
    target_url: str,
    sub_paths: Optional[List[str]] = None,
    output_file: str = "security-privacy-report.txt"
) -> str:
    """Main security and privacy audit execution pipeline."""
    crawled_pages, http_redirects_to_https, http_redirect_issue = crawl_website(target_url, sub_paths)
    if not crawled_pages:
        raise RuntimeError(f"Unable to crawl target URL: {target_url}")

    evaluator = SecurityPrivacyEvaluator(
        base_url=target_url,
        pages=crawled_pages,
        http_redirects_to_https=http_redirects_to_https,
        http_redirect_issue=http_redirect_issue
    )
    results = evaluator.run_full_audit()
    report_text = format_report(base_url=target_url, section_results=results)

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(report_text)

    print(f"\n[+] Audit complete! Report generated at: {os.path.abspath(output_file)}")
    return report_text


if __name__ == "__main__":
    if len(sys.argv) > 1:
        url_arg = sys.argv[1]
        sub_pages_arg = sys.argv[2:] if len(sys.argv) > 2 else None
        report = run_audit(url_arg, sub_pages_arg)
        print("\n" + report)
    else:
        print("Security, Privacy & Web Hygiene Auditor Agent")
        print("---------------------------------------------")
        target = input("Enter target website base URL (e.g., https://example.com): ").strip()
        if target:
            subs_input = input("Enter optional comma-separated sub-paths: ").strip()
            subs = [s.strip() for s in subs_input.split(",") if s.strip()] if subs_input else None
            report = run_audit(target, subs)
            print("\n" + report)
        else:
            print("No URL provided. Exiting.")
