"""
Tracking & Measurement Architecture Auditor
============================================
Automated crawling and evaluation engine for Web Analytics, Google Tag Manager (GTM),
Google Analytics 4 (GA4), Meta (Facebook) Pixel, Conversion Event Architecture,
DataLayer Integrity, E-Commerce Funnel Measurement, and Google Consent Mode v2.

Evaluates websites across:
1. Core Tag Deployment & Container Hygiene (GTM, GA4, Meta Pixel presence and duplicate execution)
2. Conversion Event Architecture & Micro-Action Tracking (form leads, click-to-call, email, downloads)
3. DataLayer Architecture & State Management (dataLayer declaration order, contextual metadata, array safety)
4. E-Commerce & Funnel Step Measurement (view_item, add_to_cart, begin_checkout, purchase)
5. Google Consent Mode v2 & Privacy-Preserving Measurement (default state, v2 parameters, execution timing)
6. Ad Platform Pixels & Attribution Hygiene (multi-channel pixels, server-side CAPI event_id, zombie tags)

Generates a standardized 'tracking-measurement-report.txt' audit report.
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
    redirect_chain: List[Tuple[int, str]] = field(default_factory=list)
    soup: BeautifulSoup = field(init=False)

    def __post_init__(self):
        self.soup = BeautifulSoup(self.html, "html.parser")


class TrackingMeasurementEvaluator:
    """Evaluates crawled pages for Tracking & Measurement Architecture integrity."""

    DOCUMENT_EXTENSIONS = ('.pdf', '.docx', '.doc', '.xlsx', '.xls', '.zip', '.csv')

    def __init__(self, base_url: str, pages: List[CrawledPage]):
        self.base_url = base_url
        self.pages = pages

    def evaluate_core_tag_deployment(self) -> SectionResult:
        """Section 1: Core Tag Deployment & Container Hygiene (GTM, GA4, Meta Pixel)."""
        title = "Core Tag Deployment & Container Hygiene (GTM, GA4, Meta Pixel)"
        action_items: List[ActionItem] = []
        score = 10

        main_page = self.pages[0] if self.pages else None
        if not main_page:
            return SectionResult(title=title, score=score, action_items=action_items)

        for page in self.pages:
            soup = page.soup
            html = page.html

            # 1. Google Tag Manager (GTM)
            gtm_scripts = []
            for sc in soup.find_all("script"):
                src = sc.get("src", "")
                text = sc.get_text()
                if "googletagmanager.com/gtm.js" in src or "googletagmanager.com/gtm.js" in text:
                    gtm_scripts.append(sc)

            gtm_ids = re.findall(r'GTM-[A-Z0-9]+', html)
            unique_gtm_ids = set(gtm_ids)

            # Check for GTM duplication on the same page
            if len(gtm_scripts) > 1:
                action_items.append(
                    ActionItem(
                        url=page.url,
                        issue=f"Duplicated Google Tag Manager script execution ({len(gtm_scripts)} instances detected on same page); triggers double pageviews and redundant event evaluation",
                        selector="CSS: head > script[src*='gtm.js']"
                    )
                )
                score -= 3

            # Check for multiple distinct GTM containers
            if len(unique_gtm_ids) > 1:
                action_items.append(
                    ActionItem(
                        url=page.url,
                        issue=f"Multiple distinct GTM container IDs detected ({', '.join(sorted(unique_gtm_ids))}); fragmented containers complicate tag governance and create trigger race conditions",
                        selector="CSS: head > script"
                    )
                )
                score -= 2

            # Check for GTM noscript companion iframe
            if gtm_scripts:
                noscript = soup.find("noscript")
                has_gtm_noscript = False
                if noscript:
                    for iframe in noscript.find_all("iframe"):
                        if "googletagmanager.com/ns.html" in iframe.get("src", ""):
                            has_gtm_noscript = True
                            break
                if not has_gtm_noscript:
                    action_items.append(
                        ActionItem(
                            url=page.url,
                            issue="Missing companion Google Tag Manager noscript fallback iframe immediately after opening <body> tag; fails to capture non-JS user sessions",
                            selector="XPath: /html/body/noscript[1]"
                        )
                    )
                    score -= 1

            # 2. Google Analytics 4 (GA4)
            # Find Measurement IDs: G-XXXXXXXXXX
            ga4_ids_in_src = re.findall(r'googletagmanager\.com/gtag/js\?id=(G-[A-Z0-9]+)', html)
            ga4_ids_in_config = re.findall(r"gtag\s*\(\s*['\"]config['\"]\s*,\s*['\"](G-[A-Z0-9]+)['\"]", html)
            all_ga4_ids = list(set(ga4_ids_in_src + ga4_ids_in_config))

            # Check for duplicate initialization of the same GA4 Measurement ID in config
            config_counts: Dict[str, int] = {}
            for gid in ga4_ids_in_config:
                config_counts[gid] = config_counts.get(gid, 0) + 1

            for gid, count in config_counts.items():
                if count > 1:
                    action_items.append(
                        ActionItem(
                            url=page.url,
                            issue=f"Duplicated Google Analytics 4 Measurement ID ('{gid}') initialized {count} times via gtag('config') on same page load; artificially inflates pageviews and distorts engagement metrics",
                            selector="CSS: head > script"
                        )
                    )
                    score -= 3

            # Check for duplicate script src tags
            src_counts: Dict[str, int] = {}
            for gid in ga4_ids_in_src:
                src_counts[gid] = src_counts.get(gid, 0) + 1
            for gid, count in src_counts.items():
                if count > 1:
                    action_items.append(
                        ActionItem(
                            url=page.url,
                            issue=f"Duplicated Google Analytics 4 library script tag ('gtag/js?id={gid}') loaded {count} times on same page load; causes redundant library parsing and network overhead",
                            selector="CSS: head > script[src*='gtag/js']"
                        )
                    )
                    score -= 2

            # 3. Meta (Facebook) Pixel
            # Base script: fbevents.js or fbq('init', '...')
            fb_pixel_scripts = []
            for sc in soup.find_all("script"):
                text = sc.get_text()
                src = sc.get("src", "")
                if "fbevents.js" in src or "fbevents.js" in text or "fbq('init'" in text or 'fbq("init"' in text:
                    fb_pixel_scripts.append(sc)

            pixel_ids = re.findall(r"fbq\s*\(\s*['\"]init['\"]\s*,\s*['\"](\d{10,18})['\"]", html)
            pixel_counts: Dict[str, int] = {}
            for pid in pixel_ids:
                pixel_counts[pid] = pixel_counts.get(pid, 0) + 1

            for pid, count in pixel_counts.items():
                if count > 1:
                    action_items.append(
                        ActionItem(
                            url=page.url,
                            issue=f"Duplicated Meta Pixel ID ('{pid}') initialized {count} times on same page; causes duplicate PageView tracking in Meta Events Manager",
                            selector="CSS: head > script"
                        )
                    )
                    score -= 3

            # 4. Deprecated Universal Analytics (UA) tags
            ua_matches = re.findall(r'\bUA-\d{4,10}-\d+\b', html)
            has_analytics_js = any("analytics.js" in sc.get("src", "") for sc in soup.find_all("script"))

            if ua_matches or has_analytics_js:
                clean_ua = ua_matches[0] if ua_matches else "analytics.js"
                action_items.append(
                    ActionItem(
                        url=page.url,
                        issue=f"Legacy Universal Analytics tracking script detected ('{clean_ua}'); platform was sunsetted by Google and obsolete tag adds unnecessary render latency",
                        selector="CSS: head > script"
                    )
                )
                score -= 2

            # 5. Total absence of primary tracking containers
            if not gtm_scripts and not all_ga4_ids:
                action_items.append(
                    ActionItem(
                        url=page.url,
                        issue="No primary web analytics container (Google Tag Manager or Google Analytics 4) detected; website traffic and user engagement are completely unmeasured",
                        selector="CSS: head"
                    )
                )
                score -= 5

        score = max(0, min(10, score))
        return SectionResult(title=title, score=score, action_items=action_items)

    def evaluate_conversion_events(self) -> SectionResult:
        """Section 2: Conversion Event Architecture & Micro-Action Tracking."""
        title = "Conversion Event Architecture & Micro-Action Tracking"
        action_items: List[ActionItem] = []
        score = 10

        tel_uninstrumented_flagged = False
        mailto_uninstrumented_flagged = False
        downloads_uninstrumented = 0

        for page in self.pages:
            soup = page.soup
            html = page.html

            # 1. Lead Generation Forms
            forms = soup.find_all("form")
            for form in forms:
                action = form.get("action", "").strip()
                form_id = form.get("id", "")
                form_name = form.get("name", "")
                inputs = form.find_all("input")

                # Skip obvious search-only inputs
                is_search_form = any(
                    inp.get("name", "").lower() in ["s", "q", "query", "search"]
                    or inp.get("type", "").lower() == "search"
                    for inp in inputs
                ) or form.get("role", "").lower() == "search"

                if is_search_form:
                    continue

                # Check if form is a lead, contact, or quote form
                is_lead_form = (
                    any(inp.get("type", "").lower() in ["email", "tel"] for inp in inputs)
                    or any(k in (form_id + form_name + action).lower() for k in ["contact", "lead", "quote", "inquiry", "signup", "register"])
                    or len(inputs) >= 2
                )

                if is_lead_form:
                    sel = generate_css_selector(form)
                    # Check for form tracking instrumentation: onsubmit, data-event, or telemetry in page scripts
                    has_onsubmit = bool(form.get("onsubmit"))
                    has_data_track = any(k.startswith("data-track") or k.startswith("data-analytics") or k == "data-event" for k in form.attrs)
                    
                    # Check if script contains explicit form submit event push
                    script_tracks_form = bool(re.search(
                        r"""(?:event|event_name)['"]\s*:\s*['"](?:generate_lead|form_submit|form_submission|contact_submit)['"]"""
                        r"""|gtag\s*\(\s*['"]event['"]\s*,\s*['"](?:generate_lead|form_submit)['"]"""
                        r"""|fbq\s*\(\s*['"]track['"]\s*,\s*['"]Lead['"]"""
                        r"""|dataLayer\.push\s*\(\s*\{[^}]*?['"]event['"]\s*:\s*['"][^'"]*lead""",
                        html,
                        re.IGNORECASE
                    ))

                    if not has_onsubmit and not has_data_track and not script_tracks_form:
                        action_items.append(
                            ActionItem(
                                url=page.url,
                                issue=f"Lead generation form lacks custom event telemetry or dataLayer push on submission ('action=\"{action}\"'); form submissions will not attribute in GA4 or ad platforms",
                                selector=f"CSS: {sel}"
                            )
                        )
                        score -= 2

            # 2. Click-to-Call (Phone) Tracking
            tel_links = soup.find_all("a", href=lambda h: h and h.startswith("tel:"))
            for a in tel_links:
                if tel_uninstrumented_flagged:
                    break
                href = a.get("href", "").strip()
                has_onclick = bool(a.get("onclick"))
                has_data_track = any(k.startswith("data-track") or k.startswith("data-event") or k.startswith("data-analytics") for k in a.attrs)
                script_tracks_phone = bool(re.search(
                    r"""(?:event|event_name)['"]\s*:\s*['"](?:click_to_call|phone_click|call_click)['"]"""
                    r"""|gtag\s*\(\s*['"]event['"]\s*,\s*['"](?:click_to_call|phone_click)['"]"""
                    r"""|dataLayer\.push\s*\(\s*\{[^}]*?['"]event['"]\s*:\s*['"][^'"]*(?:phone|call|tel)""",
                    html,
                    re.IGNORECASE
                ))

                if not has_onclick and not has_data_track and not script_tracks_phone:
                    tel_uninstrumented_flagged = True
                    xpath = generate_xpath(a)
                    action_items.append(
                        ActionItem(
                            url=page.url,
                            issue=f"Click-to-call link ('{href}') has no custom event listener or dataLayer push to track phone inquiries",
                            selector=f"XPath: {xpath}"
                        )
                    )
                    score -= 2

            # 3. Email Click Tracking
            mailto_links = soup.find_all("a", href=lambda h: h and h.startswith("mailto:"))
            for a in mailto_links:
                if mailto_uninstrumented_flagged:
                    break
                href = a.get("href", "").strip()
                has_onclick = bool(a.get("onclick"))
                has_data_track = any(k.startswith("data-track") or k.startswith("data-event") for k in a.attrs)
                script_tracks_email = bool(re.search(
                    r"""(?:event|event_name)['"]\s*:\s*['"](?:click_to_email|email_click)['"]"""
                    r"""|gtag\s*\(\s*['"]event['"]\s*,\s*['"](?:click_to_email|email_click)['"]"""
                    r"""|dataLayer\.push\s*\(\s*\{[^}]*?['"]event['"]\s*:\s*['"][^'"]*email""",
                    html,
                    re.IGNORECASE
                ))

                if not has_onclick and not has_data_track and not script_tracks_email:
                    mailto_uninstrumented_flagged = True
                    xpath = generate_xpath(a)
                    action_items.append(
                        ActionItem(
                            url=page.url,
                            issue=f"Click-to-email link ('{href}') lacks custom event telemetry for message initiation tracking",
                            selector=f"XPath: {xpath}"
                        )
                    )
                    score -= 1

            # 4. File / Resource Download Tracking
            for a in soup.find_all("a", href=True):
                href = a["href"].strip()
                lower_href = href.lower()
                if any(lower_href.endswith(ext) or f"{ext}?" in lower_href for ext in self.DOCUMENT_EXTENSIONS):
                    has_onclick = bool(a.get("onclick"))
                    has_data_track = any(k.startswith("data-track") or k.startswith("data-event") for k in a.attrs)
                    script_tracks_download = bool(re.search(
                        r"""(?:event|event_name)['"]\s*:\s*['"](?:file_download|download)['"]"""
                        r"""|gtag\s*\(\s*['"]event['"]\s*,\s*['"]file_download['"]"""
                        r"""|dataLayer\.push\s*\(\s*\{[^}]*?['"]event['"]\s*:\s*['"][^'"]*download""",
                        html,
                        re.IGNORECASE
                    ))

                    if not has_onclick and not has_data_track and not script_tracks_download and downloads_uninstrumented < 2:
                        downloads_uninstrumented += 1
                        sel = generate_css_selector(a)
                        clean_href = href.split("/")[-1][:40]
                        action_items.append(
                            ActionItem(
                                url=page.url,
                                issue=f"File download link ('{clean_href}') lacks custom event listener or dataLayer push for document downloads",
                                selector=f"CSS: {sel}"
                            )
                        )
                        score -= 1

        score = max(0, min(10, score))
        return SectionResult(title=title, score=score, action_items=action_items)

    def evaluate_datalayer_architecture(self) -> SectionResult:
        """Section 3: DataLayer Architecture & State Management."""
        title = "DataLayer Architecture & State Management"
        action_items: List[ActionItem] = []
        score = 10

        main_page = self.pages[0] if self.pages else None
        if not main_page:
            return SectionResult(title=title, score=score, action_items=action_items)

        html = main_page.html
        soup = main_page.soup

        has_gtm = "googletagmanager.com/gtm.js" in html
        has_datalayer_init = bool(re.search(r'window\.dataLayer\s*=\s*window\.dataLayer\s*\|\|\s*\[\];', html))
        has_datalayer_simple = bool(re.search(r'dataLayer\s*=\s*\[\];', html))

        # Check for dangerous direct array assignment: e.g. "dataLayer = [{" or "window.dataLayer = [{"
        has_direct_overwrite = False
        for match in re.finditer(r'(?:window\.)?dataLayer\s*=\s*\[', html):
            start_pos = match.start()
            preceding = html[max(0, start_pos - 10):start_pos].strip()
            if not preceding.endswith("||"):
                has_direct_overwrite = True
                break

        # Check for direct array overwrite pattern
        if has_direct_overwrite and not has_datalayer_init:
            action_items.append(
                ActionItem(
                    url=main_page.url,
                    issue="Direct array assignment ('window.dataLayer = [...]') detected; overwrites pre-existing push queue and risks dropping tag triggers",
                    selector="CSS: script"
                )
            )
            score -= 2

        if has_gtm:
            # Check GTM vs dataLayer declaration order
            scripts = soup.find_all("script")
            gtm_index = -1
            datalayer_index = -1

            for idx, sc in enumerate(scripts):
                src = sc.get("src", "")
                text = sc.get_text()
                if "googletagmanager.com/gtm.js" in src or "googletagmanager.com/gtm.js" in text:
                    if gtm_index == -1:
                        gtm_index = idx
                if "dataLayer" in text and ("=" in text or "push" in text):
                    if datalayer_index == -1:
                        datalayer_index = idx

            if gtm_index != -1 and datalayer_index != -1 and gtm_index < datalayer_index:
                action_items.append(
                    ActionItem(
                        url=main_page.url,
                        issue="Google Tag Manager script executes before 'window.dataLayer' is initialized in the DOM; triggers race conditions and dropped early pageview events",
                        selector="CSS: head > script[src*='gtm.js']"
                    )
                )
                score -= 3

            # Check if any contextual metadata is pushed to dataLayer
            has_metadata_push = bool(re.search(
                r'dataLayer\.push\s*\(\s*\{.*?(?:page|user|category|logged_in|template|author|post).*?\}\s*\)',
                html,
                re.DOTALL | re.IGNORECASE
            ))

            if not has_metadata_push:
                action_items.append(
                    ActionItem(
                        url=main_page.url,
                        issue="No contextual page metadata (page_type, user_status, category) pushed to dataLayer on initial render; limits segmentation and custom dimension analysis",
                        selector="CSS: head"
                    )
                )
                score -= 1
        else:
            # Non-GTM site check: is dataLayer or gtag initialized?
            if "gtag" not in html and "dataLayer" not in html:
                action_items.append(
                    ActionItem(
                        url=main_page.url,
                        issue="No structured dataLayer architecture or analytics push queue detected; limits scalable event modeling and tag orchestration",
                        selector="CSS: head"
                    )
                )
                score -= 3

        score = max(0, min(10, score))
        return SectionResult(title=title, score=score, action_items=action_items)

    def evaluate_ecommerce_measurement(self) -> SectionResult:
        """Section 4: E-Commerce & Funnel Step Measurement."""
        title = "E-Commerce & Funnel Step Measurement"
        action_items: List[ActionItem] = []
        score = 10

        is_ecommerce_site = False
        all_html = " ".join(p.html for p in self.pages).lower()

        # Detect eCommerce clues across site
        ecommerce_keywords = [
            "/cart", "/checkout", "/product", "/shop", "add to cart", "add-to-cart",
            "woocommerce", "shopify", "buy now", "order confirmation"
        ]
        if any(kw in all_html for kw in ecommerce_keywords):
            is_ecommerce_site = True

        if not is_ecommerce_site:
            return SectionResult(
                title=title,
                score=10,
                action_items=[]
            )

        # Inspect eCommerce pages
        has_view_item = "view_item" in all_html or "viewcontent" in all_html
        has_add_to_cart = "add_to_cart" in all_html or "addtocart" in all_html
        has_begin_checkout = "begin_checkout" in all_html or "initiatecheckout" in all_html
        has_purchase = "purchase" in all_html

        product_page_found = False
        cart_page_found = False
        checkout_page_found = False

        for page in self.pages:
            lower_url = page.url.lower()
            soup = page.soup

            # Product page check
            if any(k in lower_url for k in ["/product", "/item", "/p/"]) or soup.find(class_=re.compile(r'product|item', re.I)):
                product_page_found = True
                if not has_view_item:
                    action_items.append(
                        ActionItem(
                            url=page.url,
                            issue="Product page lacks standard GA4 'view_item' or Meta 'ViewContent' event push containing item parameters (currency, value, item_id)",
                            selector="CSS: main"
                        )
                    )
                    score -= 2

            # Cart / Add to Cart check
            add_to_cart_btn = soup.find(lambda t: t.name in ["button", "a", "input"] and "add to cart" in t.get_text().strip().lower())
            if add_to_cart_btn or "/cart" in lower_url:
                cart_page_found = True
                if not has_add_to_cart:
                    sel = generate_css_selector(add_to_cart_btn) if add_to_cart_btn else "button"
                    action_items.append(
                        ActionItem(
                            url=page.url,
                            issue="Add-to-cart interaction does not trigger standard 'add_to_cart' or 'AddToCart' event telemetry",
                            selector=f"CSS: {sel}"
                        )
                    )
                    score -= 2

            # Checkout initiation check
            if any(k in lower_url for k in ["/checkout", "/order"]):
                checkout_page_found = True
                if not has_begin_checkout:
                    action_items.append(
                        ActionItem(
                            url=page.url,
                            issue="Checkout flow lacks standard GA4 'begin_checkout' or Meta 'InitiateCheckout' event instrumentation",
                            selector="CSS: form"
                        )
                    )
                    score -= 2

                # Thank you / Order confirmation check
                if any(k in lower_url for k in ["order-received", "thank-you", "confirmation", "receipt"]):
                    if not has_purchase:
                        action_items.append(
                            ActionItem(
                                url=page.url,
                                issue="Order confirmation page missing standard GA4 'purchase' payload with transaction_id, revenue value, and item details; critical failure for ROAS attribution",
                                selector="CSS: section"
                            )
                        )
                        score -= 4

        # If eCommerce store detected but zero standard e-commerce events anywhere
        if not has_view_item and not has_add_to_cart and not has_begin_checkout and not has_purchase:
            if not action_items:
                action_items.append(
                    ActionItem(
                        url=self.base_url,
                        issue="E-commerce store detected but lacks all standard GA4/Meta e-commerce event triggers (view_item, add_to_cart, begin_checkout, purchase); disables revenue attribution",
                        selector="CSS: body"
                    )
                )
                score -= 5

        score = max(0, min(10, score))
        return SectionResult(title=title, score=score, action_items=action_items)

    def evaluate_consent_mode_v2(self) -> SectionResult:
        """Section 5: Google Consent Mode v2 & Privacy-Preserving Measurement."""
        title = "Google Consent Mode v2 & Privacy-Preserving Measurement"
        action_items: List[ActionItem] = []
        score = 10

        main_page = self.pages[0] if self.pages else None
        if not main_page:
            return SectionResult(title=title, score=score, action_items=action_items)

        html = main_page.html
        has_google_tags = "googletagmanager.com" in html or "google-analytics.com" in html or "gtag(" in html

        if not has_google_tags:
            return SectionResult(title=title, score=10, action_items=[])

        # Check for Consent Mode default declaration
        consent_default_match = re.search(
            r"gtag\s*\(\s*['\"]consent['\"]\s*,\s*['\"]default['\"]\s*,\s*(\{.*?\})\s*\)",
            html,
            re.DOTALL | re.IGNORECASE
        )

        if not consent_default_match:
            action_items.append(
                ActionItem(
                    url=main_page.url,
                    issue="Google tracking tags (GA4/Google Ads) execute without Google Consent Mode v2 default declaration; violates EU DMA compliance and eliminates ad modeling",
                    selector="CSS: head > script"
                )
            )
            score -= 4
        else:
            consent_payload = consent_default_match.group(1).lower()

            # Check for the mandatory Consent Mode v2 parameters
            required_v2_params = ["ad_user_data", "ad_personalization"]
            missing_v2_params = [p for p in required_v2_params if p not in consent_payload]

            if missing_v2_params:
                action_items.append(
                    ActionItem(
                        url=main_page.url,
                        issue=f"Consent configuration lacks modern Consent Mode v2 parameters ({', '.join(missing_v2_params)}); remarketing audiences and enhanced conversions will be blocked in Google Ads",
                        selector="CSS: head > script"
                    )
                )
                score -= 2

            # Check execution timing: consent default MUST fire BEFORE gtm.js or gtag.js loads
            soup = main_page.soup
            scripts = soup.find_all("script")
            consent_idx = -1
            gtm_or_gtag_idx = -1

            for idx, sc in enumerate(scripts):
                text = sc.get_text()
                src = sc.get("src", "")
                if "consent" in text and "default" in text:
                    if consent_idx == -1:
                        consent_idx = idx
                if "gtm.js" in src or "gtag/js" in src:
                    if gtm_or_gtag_idx == -1:
                        gtm_or_gtag_idx = idx

            if consent_idx != -1 and gtm_or_gtag_idx != -1 and consent_idx > gtm_or_gtag_idx:
                action_items.append(
                    ActionItem(
                        url=main_page.url,
                        issue="Google Consent Mode default command executes after Google Tag Manager or gtag.js has already loaded; tags fire before consent state is evaluated",
                        selector="CSS: script"
                    )
                )
                score -= 2

        score = max(0, min(10, score))
        return SectionResult(title=title, score=score, action_items=action_items)

    def evaluate_ad_pixels_and_attribution(self) -> SectionResult:
        """Section 6: Ad Platform Pixels & Attribution Hygiene."""
        title = "Ad Platform Pixels & Attribution Hygiene"
        action_items: List[ActionItem] = []
        score = 10

        main_page = self.pages[0] if self.pages else None
        if not main_page:
            return SectionResult(title=title, score=score, action_items=action_items)

        html = main_page.html

        # 1. Meta Pixel CAPI Event Deduplication Check
        has_fb_pixel = "fbevents.js" in html or "fbq(" in html
        if has_fb_pixel:
            # Check if custom or standard conversion events send eventID/event_id
            track_calls = re.findall(r"fbq\s*\(\s*['\"]track['\"]\s*,\s*['\"](Lead|Purchase|AddToCart|InitiateCheckout)['\"].*?\)", html)
            for call in track_calls:
                if "eventid" not in call.lower() and "event_id" not in call.lower():
                    action_items.append(
                        ActionItem(
                            url=main_page.url,
                            issue="Meta Pixel executes client-side conversion event without unique 'event_id' parameter; risks duplicate conversion counting if server-side Conversions API (CAPI) is enabled",
                            selector="CSS: script"
                        )
                    )
                    score -= 1
                    break

        # 2. Check for placeholder or unconfigured pixel IDs
        placeholder_matches = re.findall(
            r"(?:GTM-|G-|AW-|\bfbq\(['\"]init['\"],\s*['\"])(YOUR[_\w]+|XXXX[_\w]+|000000|123456789)['\"]",
            html,
            re.IGNORECASE
        )
        if placeholder_matches:
            action_items.append(
                ActionItem(
                    url=main_page.url,
                    issue=f"Placeholder or unconfigured tag ID detected in production HTML ('{placeholder_matches[0]}'); indicates broken or incomplete tracking setup",
                    selector="CSS: head > script"
                )
            )
            score -= 3

        # 3. Inactive / Defunct tracking script detections
        defunct_trackers = [
            ("ads-twitter.com/uwt.js", "Twitter/X legacy Universal Website Tag"),
            ("bat.bing.com/bat.js", "Microsoft Advertising UET"),
            ("analytics.tiktok.com", "TikTok Pixel"),
            ("snap.licdn.com", "LinkedIn Insight Tag")
        ]
        
        # Check for multiple ad scripts on simple non-ad sites or broken script tags
        unresponsive_trackers = 0
        for snippet, tracker_name in defunct_trackers:
            if snippet in html:
                # Flag if pixel script is present but initialization call is absent
                if snippet == "snap.licdn.com" and "_linkedin_partner_id" not in html and "window.lintrk" not in html:
                    action_items.append(
                        ActionItem(
                            url=main_page.url,
                            issue=f"LinkedIn Insight Tag library loaded without partner ID initialization; executes unconfigured script payload",
                            selector="CSS: head > script[src*='snap.licdn.com']"
                        )
                    )
                    score -= 1

        score = max(0, min(10, score))
        return SectionResult(title=title, score=score, action_items=action_items)

    def run_full_audit(self) -> List[SectionResult]:
        """Execute all six Tracking & Measurement Architecture audit sections."""
        return [
            self.evaluate_core_tag_deployment(),
            self.evaluate_conversion_events(),
            self.evaluate_datalayer_architecture(),
            self.evaluate_ecommerce_measurement(),
            self.evaluate_consent_mode_v2(),
            self.evaluate_ad_pixels_and_attribution(),
        ]


def crawl_website(
    base_url: str,
    sub_paths: Optional[List[str]] = None
) -> List[CrawledPage]:
    """
    Crawl the target website, auto-discover conversion and e-commerce sub-pages,
    and collect HTML responses for tracking and telemetry analysis.
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

    print(f"[*] Fetching base URL: {base_url} ...")
    try:
        resp = session.get(base_url, timeout=12, allow_redirects=True)
        chain = [(r.status_code, r.url) for r in resp.history]
        crawled_pages.append(
            CrawledPage(
                url=resp.url,
                html=resp.text,
                status_code=resp.status_code,
                headers=dict(resp.headers),
                redirect_chain=chain,
            )
        )
    except Exception as e:
        print(f"[!] Error fetching base URL {base_url}: {e}")
        return crawled_pages

    main_soup = crawled_pages[0].soup

    # Build list of URLs to crawl
    target_urls: List[str] = []
    if sub_paths:
        for p in sub_paths:
            full_url = urllib.parse.urljoin(base_url, p)
            if full_url not in target_urls and full_url != crawled_pages[0].url:
                target_urls.append(full_url)
    else:
        # Auto-discover relevant tracking & conversion sub-pages:
        # contact, pricing, shop, product, cart, checkout, thank-you, resources
        target_keywords = [
            "contact", "pricing", "quote", "shop", "product",
            "cart", "checkout", "thank-you", "order", "resources", "download"
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
            print(f"[*] Crawling conversion sub-page: {link} ...")
            sub_resp = session.get(link, timeout=10, allow_redirects=True)
            sub_chain = [(r.status_code, r.url) for r in sub_resp.history]
            crawled_pages.append(
                CrawledPage(
                    url=sub_resp.url,
                    html=sub_resp.text,
                    status_code=sub_resp.status_code,
                    headers=dict(sub_resp.headers),
                    redirect_chain=sub_chain,
                )
            )
        except Exception as e:
            print(f"    [!] Error crawling {link}: {e}")

    return crawled_pages


def format_report(base_url: str, section_results: List[SectionResult]) -> str:
    """Format audit findings into standardized Tracking & Measurement Architecture report."""
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
        "TRACKING & MEASUREMENT ARCHITECTURE AUDIT REPORT",
        f"Target Site: {base_url}",
        "Generated By: Agency AI Tracking & Measurement Auditor Agent",
        "Benchmark: Google Analytics 4, Google Tag Manager, Meta Pixel & Consent Mode v2 Standards",
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
            lines.append(f"{base_url} | Meets all tracking, tag hygiene, and measurement architecture standards for this capability.")
        lines.append("")

    lines.append("============================================================")
    lines.append("OVERALL SUMMARY & RECOMMENDATIONS")
    lines.append(f"Overall Tracking & Measurement Score: {total_score}/10")
    lines.append(f"Tracking Integrity & Attribution Risk Level: {risk_level}")
    lines.append("Primary Measurement Bottlenecks:")

    # Identify top bottlenecks from lowest scoring sections
    sorted_sections = sorted(section_results, key=lambda s: s.score)
    bottleneck_idx = 1
    for s in sorted_sections[:2]:
        if s.action_items:
            lines.append(f"{bottleneck_idx}. [{s.title}] {s.action_items[0].issue}")
            bottleneck_idx += 1

    if bottleneck_idx == 1:
        lines.append("1. None identified; website meets baseline tracking and attribution standards.")

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
        lines.append("1. Maintain continuous dataLayer hygiene and Consent Mode v2 synchronization.")

    lines.append("============================================================")
    lines.append("END OF REPORT")
    lines.append("============================================================")

    return "\n".join(lines)


def run_audit(
    target_url: str,
    sub_paths: Optional[List[str]] = None,
    output_file: str = "tracking-measurement-report.txt"
) -> str:
    """Main tracking and measurement audit execution pipeline."""
    crawled_pages = crawl_website(target_url, sub_paths)
    if not crawled_pages:
        raise RuntimeError(f"Unable to crawl target URL: {target_url}")

    evaluator = TrackingMeasurementEvaluator(base_url=target_url, pages=crawled_pages)
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
        print("Tracking & Measurement Architecture Auditor Agent")
        print("-------------------------------------------------")
        target = input("Enter target website base URL (e.g., https://example.com): ").strip()
        if target:
            subs_input = input("Enter optional comma-separated sub-paths: ").strip()
            subs = [s.strip() for s in subs_input.split(",") if s.strip()] if subs_input else None
            report = run_audit(target, subs)
            print("\n" + report)
        else:
            print("No URL provided. Exiting.")
