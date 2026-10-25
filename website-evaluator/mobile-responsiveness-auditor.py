"""
Mobile Responsiveness & Touch UX Auditor
========================================
Automated crawling and evaluation engine for Mobile-First Indexing, Touch Ergonomics,
Responsive Layout Reflow, Mobile Navigation, and Local Conversion Actionability.

Evaluates websites across:
1. Touch Targets & Thumb Ergonomics (44x44px target standards, spacing, thumb zones)
2. Viewport Configuration & Responsive Layout Reflow (horizontal scroll, viewport meta, fluid media)
3. Mobile Navigation & Sticky Header Real Estate (hamburger nesting depth, header height consumption)
4. Mobile Click-to-Call & Local Directions Integration (tap-to-call tel: links, tap-to-navigate map links)
5. Mobile Form Ergonomics & Font Auto-Zoom Prevention (input font-size >= 16px, virtual keyboards)
6. Mobile Interstitials & Overlay Friction (full-screen modal blocking, tiny close buttons)

Generates a standardized 'mobile-ux-report.txt' audit report.
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
    soup: BeautifulSoup = field(init=False)

    def __post_init__(self):
        self.soup = BeautifulSoup(self.html, "html.parser")


class MobileUXEvaluator:
    """Evaluates crawled pages for Mobile Responsiveness, Touch UX, and Navigation Ergonomics."""

    PHONE_REGEX = re.compile(
        r'(?:\+?1[-.\s]?)?\(?([2-9]\d{2})\)?[-.\s]?(\d{3})[-.\s]?(\d{4})\b'
    )

    ADDRESS_KEYWORD_REGEX = re.compile(
        r'\b\d{1,5}\s+[A-Za-z0-9\s.,#-]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Way|Suite|Ste|Floor|Fl|Highway|Hwy|Pkwy|Parkway)\b',
        re.IGNORECASE
    )

    EMAIL_REGEX = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')

    def __init__(self, base_url: str, pages: List[CrawledPage]):
        self.base_url = base_url
        self.pages = pages

    def evaluate_touch_targets(self) -> SectionResult:
        """Section 1: Touch Targets & Thumb Ergonomics."""
        title = "Touch Targets & Thumb Ergonomics"
        action_items: List[ActionItem] = []
        score = 10

        for page in self.pages:
            soup = page.soup

            # 1. Interactive controls with explicit undersized inline dimensions (< 44px)
            interactive_tags = soup.find_all(["button", "a", "input", "select"])
            undersized_count = 0

            for tag in interactive_tags:
                style = (tag.get("style") or "").lower()
                classes = " ".join(tag.get("class", [])).lower()

                # Check inline width/height < 44px
                w_match = re.search(r'(?:^|;)\s*width\s*:\s*(\d+)px', style)
                h_match = re.search(r'(?:^|;)\s*height\s*:\s*(\d+)px', style)

                is_undersized = False
                if w_match and int(w_match.group(1)) < 44:
                    is_undersized = True
                if h_match and int(h_match.group(1)) < 44:
                    is_undersized = True

                # Check small classes
                if any(c in classes for c in ["btn-xs", "p-0", "h-6", "h-7", "h-8", "w-6", "w-7", "w-8"]):
                    is_undersized = True

                if is_undersized and tag.name in ["button", "a"] and undersized_count < 3:
                    undersized_count += 1
                    score -= 1
                    text_label = tag.get_text(strip=True)[:25] or tag.get("aria-label") or tag.name
                    action_items.append(
                        ActionItem(
                            url=page.url,
                            issue=f"Interactive touch target '{text_label}' measures below the 44x44px mobile touch threshold (Apple HIG / Android Material guidelines)",
                            selector=f"CSS: {generate_css_selector(tag)}"
                        )
                    )

            # 2. Clustered pagination or tag links with tight spacing
            pagination = soup.find(class_=lambda c: c and "pagination" in str(c).lower())
            if pagination:
                page_links = pagination.find_all("a")
                if len(page_links) > 3:
                    score -= 1
                    action_items.append(
                        ActionItem(
                            url=page.url,
                            issue="Pagination links are tightly packed on mobile viewports; ensure minimum 8px margin/padding between adjacent tap targets",
                            selector=f"CSS: {generate_css_selector(pagination)}"
                        )
                    )

        score = max(0, min(10, score))
        return SectionResult(title=title, score=score, action_items=action_items)

    def evaluate_viewport_and_reflow(self) -> SectionResult:
        """Section 2: Viewport Configuration & Responsive Layout Reflow."""
        title = "Viewport Configuration & Responsive Layout Reflow"
        action_items: List[ActionItem] = []
        score = 10

        for page in self.pages:
            soup = page.soup

            # 1. Viewport Meta tag check
            viewport = soup.find("meta", attrs={"name": "viewport"})
            if not viewport:
                score -= 4
                action_items.append(
                    ActionItem(
                        url=page.url,
                        issue="Page lacks a '<meta name=\"viewport\">' tag; mobile browsers will render the desktop view zoomed out",
                        selector="XPath: /html/head"
                    )
                )
            else:
                content = (viewport.get("content") or "").lower()
                if "width=device-width" not in content:
                    score -= 2
                    action_items.append(
                        ActionItem(
                            url=page.url,
                            issue="Viewport meta tag is missing 'width=device-width', preventing fluid responsive layout scaling",
                            selector="XPath: /html/head/meta[@name='viewport']"
                        )
                    )
                if "user-scalable=no" in content or "maximum-scale=1.0" in content:
                    score -= 2
                    action_items.append(
                        ActionItem(
                            url=page.url,
                            issue="Viewport meta disables pinch-to-zoom ('user-scalable=no' or 'maximum-scale=1.0'), harming mobile accessibility and readability",
                            selector="XPath: /html/head/meta[@name='viewport']"
                        )
                    )

            # 2. Fixed-width elements forcing horizontal scrolling
            fixed_tags = soup.find_all(
                style=lambda s: s and re.search(r'(?:^|;)\s*(min-width|width)\s*:\s*([5-9]\d{2}|[1-9]\d{3})px', str(s).lower())
            )
            for el in fixed_tags[:2]:
                score -= 2
                action_items.append(
                    ActionItem(
                        url=page.url,
                        issue="Fixed-width container forces horizontal viewport overflow and awkward side-scrolling on mobile devices",
                        selector=f"XPath: {generate_xpath(el)}"
                    )
                )

            # 3. Unconstrained media elements (images without max-width)
            unconstrained_tables = soup.find_all("table")
            for tbl in unconstrained_tables[:1]:
                tbl_style = (tbl.get("style") or "").lower()
                parent_style = (tbl.parent.get("style") if tbl.parent else "") or ""
                if "overflow-x: auto" not in (tbl_style + parent_style).lower() and not any(
                    "table-responsive" in str(c) for c in (tbl.get("class", []) + (tbl.parent.get("class", []) if tbl.parent else []))
                ):
                    score -= 1
                    action_items.append(
                        ActionItem(
                            url=page.url,
                            issue="Data <table> is not wrapped in an overflow-x scroll container, breaking mobile screen boundary",
                            selector=f"CSS: {generate_css_selector(tbl)}"
                        )
                    )

        score = max(0, min(10, score))
        return SectionResult(title=title, score=score, action_items=action_items)

    def evaluate_mobile_navigation(self) -> SectionResult:
        """Section 3: Mobile Navigation & Sticky Header Real Estate."""
        title = "Mobile Navigation & Sticky Header Real Estate"
        action_items: List[ActionItem] = []
        score = 10

        for page in self.pages:
            soup = page.soup

            # 1. Sticky / Fixed header height consumption
            sticky_headers = soup.find_all(
                lambda t: t.name in ['header', 'nav', 'div'] and any(
                    k in " ".join(t.get('class', [])).lower() or k in (t.get('style') or '').lower()
                    for k in ['sticky', 'fixed-top', 'position: fixed', 'position: sticky']
                )
            )

            for sh in sticky_headers[:1]:
                style = (sh.get("style") or "").lower()
                classes = " ".join(sh.get("class", [])).lower()

                # Check for oversized height
                h_match = re.search(r'(?:^|;)\s*height\s*:\s*(\d+)px', style)
                oversized_height = False
                measured_h = ""
                if h_match and int(h_match.group(1)) > 90:
                    oversized_height = True
                    measured_h = f"{h_match.group(1)}px"
                elif any(c in classes for c in ["h-28", "h-32", "h-36", "h-40", "h-48"]):
                    oversized_height = True
                    measured_h = ">100px"

                if oversized_height:
                    score -= 2
                    action_items.append(
                        ActionItem(
                            url=page.url,
                            issue=f"Sticky mobile header height ({measured_h}) consumes more than 20% of the mobile viewport, crowding reading real estate",
                            selector=f"CSS: {generate_css_selector(sh)}"
                        )
                    )

            # 2. Deeply nested hamburger menus (>2 levels of submenus)
            navs = soup.find_all(["nav", "div"], class_=lambda c: c and any(x in str(c).lower() for x in ["nav", "menu", "drawer"]))
            for nav in navs:
                # Check for 3 levels of nested <ul> or <ol>
                deep_nesting = nav.find(lambda t: t.name in ['ul', 'ol'] and t.find_parent(lambda p: p.name in ['ul', 'ol'] and p.find_parent(lambda p2: p2.name in ['ul', 'ol'])))
                if deep_nesting:
                    score -= 2
                    action_items.append(
                        ActionItem(
                            url=page.url,
                            issue="Mobile navigation contains deeply nested sub-menus (3+ levels deep), causing cognitive friction and navigation fatigue",
                            selector=f"XPath: {generate_xpath(deep_nesting)}"
                        )
                    )
                    break

            # 3. Check hamburger toggle button accessibility & presence
            hamburger_btn = soup.find(
                lambda t: t.name in ['button', 'a', 'div'] and any(
                    k in " ".join(t.get('class', [])).lower() or k in (t.get('id') or '').lower()
                    for k in ['hamburger', 'navbar-toggler', 'menu-toggle', 'mobile-toggle']
                )
            )
            if hamburger_btn:
                if not hamburger_btn.get("aria-expanded") and not hamburger_btn.get("aria-label"):
                    score -= 1
                    action_items.append(
                        ActionItem(
                            url=page.url,
                            issue="Mobile hamburger toggle button lacks 'aria-expanded' and 'aria-label' accessibility attributes",
                            selector=f"CSS: {generate_css_selector(hamburger_btn)}"
                        )
                    )

        score = max(0, min(10, score))
        return SectionResult(title=title, score=score, action_items=action_items)

    def evaluate_click_to_call_and_directions(self) -> SectionResult:
        """Section 4: Mobile Click-to-Call & Local Directions Integration."""
        title = "Mobile Click-to-Call & Local Directions Integration"
        action_items: List[ActionItem] = []
        score = 10

        for page in self.pages:
            soup = page.soup

            # 1. Detect phone numbers in text vs clickable <a href="tel:...">
            tel_links = [a.get("href") for a in soup.find_all("a", href=True) if a["href"].startswith("tel:")]

            # Look for unlinked phone numbers in plain text
            text_blocks = soup.find_all(["p", "div", "span", "li", "td", "address"])
            unlinked_phones = []

            for block in text_blocks:
                # If block already contains a tel: link, skip
                if block.find("a", href=lambda h: h and h.startswith("tel:")):
                    continue

                text = block.get_text(strip=True)
                match = self.PHONE_REGEX.search(text)
                if match:
                    phone_str = match.group(0)
                    # Exclude dates or common number patterns
                    if len(phone_str) >= 10:
                        unlinked_phones.append((block, phone_str))

            if unlinked_phones and not tel_links:
                score -= 3
                block, phone_str = unlinked_phones[0]
                action_items.append(
                    ActionItem(
                        url=page.url,
                        issue=f"Phone number '{phone_str}' is rendered as static plain text; missing clickable '<a href=\"tel:...\">' tap-to-call link for mobile users",
                        selector=f"XPath: {generate_xpath(block)}"
                    )
                )

            # 2. Detect physical street addresses vs tap-to-navigate links
            map_links = [
                a.get("href") for a in soup.find_all("a", href=True)
                if any(m in a["href"].lower() for m in ["maps.google", "google.com/maps", "maps.apple", "geo:"])
            ]

            unlinked_addresses = []
            for block in text_blocks:
                if block.find("a", href=lambda h: h and any(m in h.lower() for m in ["maps.google", "google.com/maps", "maps.apple", "geo:"])):
                    continue

                text = block.get_text(strip=True)
                match = self.ADDRESS_KEYWORD_REGEX.search(text)
                if match:
                    addr_str = match.group(0)
                    if len(addr_str) > 12:
                        unlinked_addresses.append((block, addr_str))

            if unlinked_addresses and not map_links:
                score -= 2
                block, addr_str = unlinked_addresses[0]
                action_items.append(
                    ActionItem(
                        url=page.url,
                        issue=f"Physical address '{addr_str}' is rendered as plain text; missing tap-to-navigate link to Google/Apple Maps",
                        selector=f"CSS: {generate_css_selector(block)}"
                    )
                )

            # 3. Detect unlinked email addresses in text
            mailto_links = [a.get("href") for a in soup.find_all("a", href=True) if a["href"].startswith("mailto:")]
            unlinked_emails = []
            for block in text_blocks:
                if block.find("a", href=lambda h: h and h.startswith("mailto:")):
                    continue
                text = block.get_text(strip=True)
                match = self.EMAIL_REGEX.search(text)
                if match and not any(ext in match.group(0) for ext in [".png", ".jpg", ".js"]):
                    unlinked_emails.append((block, match.group(0)))

            if unlinked_emails and not mailto_links:
                score -= 1
                block, email_str = unlinked_emails[0]
                action_items.append(
                    ActionItem(
                        url=page.url,
                        issue=f"Email address '{email_str}' is rendered as plain text without an interactive '<a href=\"mailto:...\">' link",
                        selector=f"CSS: {generate_css_selector(block)}"
                    )
                )

        score = max(0, min(10, score))
        return SectionResult(title=title, score=score, action_items=action_items)

    def evaluate_mobile_form_ergonomics(self) -> SectionResult:
        """Section 5: Mobile Form Ergonomics & Font Auto-Zoom Prevention."""
        title = "Mobile Form Ergonomics & Font Auto-Zoom Prevention"
        action_items: List[ActionItem] = []
        score = 10

        for page in self.pages:
            soup = page.soup
            inputs = soup.find_all(["input", "select", "textarea"])

            for inp in inputs:
                inp_type = (inp.get("type") or "text").lower()
                if inp_type in ["hidden", "submit", "button", "reset"]:
                    continue

                style = (inp.get("style") or "").lower()
                classes = " ".join(inp.get("class", [])).lower()

                # 1. Font size < 16px triggering iOS Safari auto-zoom
                font_match = re.search(r'font-size\s*:\s*(\d+)px', style)
                triggers_autozoom = False
                if font_match and int(font_match.group(1)) < 16:
                    triggers_autozoom = True
                elif any(c in classes for c in ["text-xs", "text-sm", "input-sm"]):
                    triggers_autozoom = True

                if triggers_autozoom:
                    score -= 1
                    action_items.append(
                        ActionItem(
                            url=page.url,
                            issue="Input field font-size is below 16px, triggering disruptive automatic viewport zooming in iOS Safari on focus",
                            selector=f"CSS: {generate_css_selector(inp)}"
                        )
                    )
                    break

                # 2. Missing telephone keypad on phone field
                inp_name = (inp.get("name") or inp.get("id") or "").lower()
                if "phone" in inp_name or "tel" in inp_name:
                    if inp_type not in ["tel", "number"]:
                        score -= 1
                        action_items.append(
                            ActionItem(
                                url=page.url,
                                issue="Phone number field uses 'type=\"text\"' instead of 'type=\"tel\"', failing to invoke the mobile numeric keypad",
                                selector=f"CSS: {generate_css_selector(inp)}"
                            )
                        )

        score = max(0, min(10, score))
        return SectionResult(title=title, score=score, action_items=action_items)

    def evaluate_mobile_interstitials(self) -> SectionResult:
        """Section 6: Mobile Interstitials & Overlay Friction."""
        title = "Mobile Interstitials & Overlay Friction"
        action_items: List[ActionItem] = []
        score = 10

        for page in self.pages:
            soup = page.soup

            # Check for modal / popup containers
            modals = soup.find_all(
                class_=lambda c: c and any(x in str(c).lower() for x in ["modal-dialog", "popup-overlay", "promo-popup", "newsletter-modal"])
            )

            for m in modals[:1]:
                # Check for tiny close button
                close_btn = m.find(lambda t: t.name in ['button', 'a'] and any(k in " ".join(t.get('class', [])).lower() for k in ["close", "dismiss", "exit"]))
                if close_btn:
                    style = (close_btn.get("style") or "").lower()
                    h_match = re.search(r'height\s*:\s*(\d+)px', style)
                    if h_match and int(h_match.group(1)) < 30:
                        score -= 2
                        action_items.append(
                            ActionItem(
                                url=page.url,
                                issue="Mobile modal close button is undersized (<30px), making dismissal difficult for finger touch interactions",
                                selector=f"CSS: {generate_css_selector(close_btn)}"
                            )
                        )

            # Check for excessive cookie banner height
            cookie_banners = soup.find_all(
                class_=lambda c: c and any(x in str(c).lower() for x in ["cookie-banner", "cookie-notice", "consent-banner", "cc-banner"])
            )
            for cb in cookie_banners[:1]:
                # If banner lacks accept button or is heavy
                accept_btn = cb.find(["button", "a"], text=re.compile(r'(accept|agree|allow)', re.I))
                if not accept_btn:
                    score -= 1
                    action_items.append(
                        ActionItem(
                            url=page.url,
                            issue="Mobile cookie consent banner lacks a prominent one-tap 'Accept All' dismissal button",
                            selector=f"CSS: {generate_css_selector(cb)}"
                        )
                    )

        score = max(0, min(10, score))
        return SectionResult(title=title, score=score, action_items=action_items)

    def run_full_audit(self) -> List[SectionResult]:
        """Execute all mobile responsiveness and touch UX evaluation modules."""
        return [
            self.evaluate_touch_targets(),
            self.evaluate_viewport_and_reflow(),
            self.evaluate_mobile_navigation(),
            self.evaluate_click_to_call_and_directions(),
            self.evaluate_mobile_form_ergonomics(),
            self.evaluate_mobile_interstitials(),
        ]


def crawl_website(base_url: str, sub_paths: Optional[List[str]] = None) -> List[CrawledPage]:
    """Crawl website using a mobile handset user-agent."""
    if not base_url.startswith("http://") and not base_url.startswith("https://"):
        base_url = "https://" + base_url

    # Mobile Safari / iPhone user-agent to simulate mobile viewport rendering
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1 MobileUXAuditor/1.0"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    session = requests.Session()
    session.headers.update(headers)

    crawled_pages: List[CrawledPage] = []
    urls_to_visit = [base_url]

    if sub_paths:
        for p in sub_paths:
            full = urllib.parse.urljoin(base_url, p.strip())
            if full not in urls_to_visit:
                urls_to_visit.append(full)

    print(f"[*] Crawling target site with Mobile User-Agent: {base_url}")
    for u in urls_to_visit:
        try:
            print(f"    Fetching {u} ...")
            resp = session.get(u, timeout=12, allow_redirects=True)
            if resp.status_code == 200:
                crawled_pages.append(
                    CrawledPage(
                        url=u,
                        html=resp.text,
                        status_code=resp.status_code,
                    )
                )
            else:
                print(f"    [!] Received HTTP status {resp.status_code} for {u}")
        except Exception as e:
            print(f"    [!] Error crawling {u}: {e}")

    # Auto-discover mobile sub-pages if only 1 page crawled
    if len(crawled_pages) == 1 and not sub_paths:
        home_soup = crawled_pages[0].soup
        discovered_paths = []
        target_keywords = ["contact", "location", "about", "services", "menu", "directions"]
        for a in home_soup.find_all("a", href=True):
            href = a["href"].strip()
            if href.startswith("#") or href.startswith("mailto:") or href.startswith("tel:"):
                continue
            for kw in target_keywords:
                if kw in href.lower():
                    full_link = urllib.parse.urljoin(base_url, href)
                    parsed_link = urllib.parse.urlparse(full_link)
                    parsed_base = urllib.parse.urlparse(base_url)
                    existing_urls = [p.url for p in crawled_pages]
                    if parsed_link.netloc == parsed_base.netloc and full_link not in existing_urls and full_link not in discovered_paths:
                        discovered_paths.append(full_link)
                    break

        for link in discovered_paths[:3]:
            try:
                print(f"    Auto-discovered mobile sub-page: {link} ...")
                resp = session.get(link, timeout=10, allow_redirects=True)
                if resp.status_code == 200:
                    crawled_pages.append(
                        CrawledPage(
                            url=link,
                            html=resp.text,
                            status_code=resp.status_code,
                        )
                    )
            except Exception as e:
                print(f"    [!] Error fetching discovered page {link}: {e}")

    return crawled_pages


def format_report(base_url: str, section_results: List[SectionResult]) -> str:
    """Format audit findings into standardized Mobile UX report."""
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
        "MOBILE RESPONSIVENESS & TOUCH UX AUDIT REPORT",
        f"Target Site: {base_url}",
        "Generated By: Agency AI Mobile UX Auditor Agent",
        "Benchmark: Google Mobile-First Indexing & Touch Ergonomics Guidelines",
        "============================================================",
        "",
    ]

    all_action_items = []

    for section in section_results:
        lines.append(f"{section.title}: {section.score}/10")
        if section.action_items:
            for item in section.action_items:
                lines.append(item.to_line())
                all_action_items.append(item)
        else:
            lines.append(f"{base_url} | Meets all mobile touch and responsiveness criteria.")
        lines.append("")

    lines.append("============================================================")
    lines.append("OVERALL SUMMARY & RECOMMENDATIONS")
    lines.append(f"Overall Mobile UX Score: {total_score}/10")
    lines.append(f"Mobile Usability Risk Level: {risk_level}")
    lines.append("Primary Mobile UX Bottlenecks:")

    # Identify top bottlenecks from lowest scoring sections
    sorted_sections = sorted(section_results, key=lambda s: s.score)
    bottleneck_idx = 1
    for s in sorted_sections[:2]:
        if s.action_items:
            lines.append(f"{bottleneck_idx}. [{s.title}] {s.action_items[0].issue}")
            bottleneck_idx += 1

    if bottleneck_idx == 1:
        lines.append("1. None identified; mobile interface adheres to touch standards.")

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
        lines.append("1. Maintain current mobile-first viewport design patterns.")

    lines.append("============================================================")
    lines.append("END OF REPORT")
    lines.append("============================================================")

    return "\n".join(lines)


def run_audit(target_url: str, sub_paths: Optional[List[str]] = None, output_file: str = "mobile-ux-report.txt") -> str:
    """Main mobile audit execution pipeline."""
    crawled_pages = crawl_website(target_url, sub_paths)
    if not crawled_pages:
        raise RuntimeError(f"Unable to crawl target URL: {target_url}")

    evaluator = MobileUXEvaluator(base_url=target_url, pages=crawled_pages)
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
        print("Mobile Responsiveness & Touch UX Auditor Agent")
        print("----------------------------------------------")
        target = input("Enter target website base URL (e.g., https://example.com): ").strip()
        if target:
            subs_input = input("Enter optional comma-separated sub-paths: ").strip()
            subs = [s.strip() for s in subs_input.split(",") if s.strip()] if subs_input else None
            report = run_audit(target, subs)
            print("\n" + report)
        else:
            print("No URL provided. Exiting.")
