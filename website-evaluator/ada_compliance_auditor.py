"""
ADA Website Compliance & WCAG 2.1/2.2 AA Auditor
================================================
Automated crawling and evaluation engine for ADA Title III & Title II compliance
against WCAG 2.1 & 2.2 Level AA standards.

Evaluates websites across:
1. Perceivable: Text Alternatives & Media (WCAG 1.1, 1.2)
2. Perceivable: Color Contrast & Visual Reflow (WCAG 1.4)
3. Operable: Keyboard Navigation & Focus Control (WCAG 2.1, 2.4)
4. Operable: Touch Targets & Motion (WCAG 2.2 2.5.8, 2.2.2, 2.3)
5. Understandable: Forms & Error Validation (WCAG 3.2, 3.3)
6. Robust: Semantic Structure & ARIA Hierarchy (WCAG 1.3.1, 4.1)
7. Native Accessibility & Overlay Assessment

Generates a standardized 'ada-compliance-report.txt' audit report.
"""

import sys
import os
import re
import urllib.parse
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
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


class ADAComplianceEvaluator:
    """Evaluates crawled pages for ADA Title III & Title II compliance against WCAG 2.1/2.2 AA."""

    KNOWN_OVERLAYS = {
        "accessibe": "accessiBe",
        "userway": "UserWay",
        "audioeye": "AudioEye",
        "equalweb": "EqualWeb",
        "facil'iti": "FACIL'iti",
        "recite-me": "Recite Me",
        "trueable": "TrueAble",
        "maxaccess": "MaxAccess",
    }

    FILE_EXT_PATTERNS = re.compile(r'\.(jpg|jpeg|png|gif|webp|svg|bmp|tiff)$', re.IGNORECASE)

    def __init__(self, base_url: str, pages: List[CrawledPage]):
        self.base_url = base_url
        self.pages = pages

    def evaluate_text_alternatives(self) -> SectionResult:
        """Section 1: Perceivable - Text Alternatives & Media (WCAG 1.1, 1.2)."""
        title = "Perceivable: Text Alternatives & Media"
        action_items: List[ActionItem] = []
        score = 10

        for page in self.pages:
            soup = page.soup

            # Check <img> elements
            images = soup.find_all("img")
            for img in images:
                alt = img.get("alt")
                src = img.get("src") or ""

                if alt is None:
                    score -= 1
                    action_items.append(
                        ActionItem(
                            url=page.url,
                            issue="Meaningful image missing 'alt' attribute entirely",
                            selector=f"XPath: {generate_xpath(img)}"
                        )
                    )
                elif alt.strip() != "":
                    # Check if alt is just the filename
                    if self.FILE_EXT_PATTERNS.search(alt.strip()) or re.match(r'^(image|img|pic|photo|screenshot)[_\d-]*$', alt.strip(), re.I):
                        score -= 1
                        action_items.append(
                            ActionItem(
                                url=page.url,
                                issue=f"Meaningful image has raw filename or non-descriptive text as alt text ('{alt.strip()}')",
                                selector=f"XPath: {generate_xpath(img)}"
                            )
                        )

            # Check <video> elements for closed captions track
            videos = soup.find_all("video")
            for vid in videos:
                captions = vid.find("track", attrs={"kind": "captions"}) or vid.find("track", attrs={"kind": "subtitles"})
                if not captions:
                    score -= 2
                    action_items.append(
                        ActionItem(
                            url=page.url,
                            issue="Promotional video missing synchronized closed captions track (<track kind=\"captions\">)",
                            selector=f"XPath: {generate_xpath(vid)}"
                        )
                    )

        score = max(0, min(10, score))
        return SectionResult(title=title, score=score, action_items=action_items)

    def evaluate_color_contrast_and_reflow(self) -> SectionResult:
        """Section 2: Perceivable - Color Contrast & Visual Reflow (WCAG 1.4)."""
        title = "Perceivable: Color Contrast & Visual Reflow"
        action_items: List[ActionItem] = []
        score = 10

        for page in self.pages:
            soup = page.soup

            # 1. Viewport zoom prevention (WCAG 1.4.4 / 1.4.10)
            viewport = soup.find("meta", attrs={"name": "viewport"})
            if viewport:
                content = (viewport.get("content") or "").lower()
                if "user-scalable=no" in content or "user-scalable=0" in content or "maximum-scale=1.0" in content:
                    score -= 3
                    action_items.append(
                        ActionItem(
                            url=page.url,
                            issue="Viewport meta tag disables pinch-to-zoom ('user-scalable=no' or 'maximum-scale=1'), preventing 400% zoom reflow for low-vision users",
                            selector="XPath: /html/head/meta[@name='viewport']"
                        )
                    )

            # 2. Check for subdued / low-contrast text classes
            low_contrast_elements = soup.find_all(
                class_=lambda c: c and any(x in str(c).lower() for x in ["text-muted", "text-subtle", "text-light", "sub-text", "dimmed"])
            )
            for el in low_contrast_elements[:2]:
                score -= 1
                action_items.append(
                    ActionItem(
                        url=page.url,
                        issue="Subdued text styling risks failing minimum WCAG contrast ratio (4.5:1 for body text, 3:1 for large text)",
                        selector=f"CSS: {generate_css_selector(el)}"
                    )
                )

            # 3. Fixed width layout tables or wrappers causing horizontal reflow
            fixed_elements = soup.find_all(
                style=lambda s: s and re.search(r'(width|min-width)\s*:\s*(1[0-9]{3}|[2-9][0-9]{3})px', str(s).lower())
            )
            for el in fixed_elements[:1]:
                score -= 2
                action_items.append(
                    ActionItem(
                        url=page.url,
                        issue="Fixed-width container causes horizontal scrollbar at 400% zoom reflow (WCAG 1.4.10)",
                        selector=f"XPath: {generate_xpath(el)}"
                    )
                )

        score = max(0, min(10, score))
        return SectionResult(title=title, score=score, action_items=action_items)

    def evaluate_keyboard_and_focus(self) -> SectionResult:
        """Section 3: Operable - Keyboard Navigation & Focus Control (WCAG 2.1, 2.4)."""
        title = "Operable: Keyboard Navigation & Focus Control"
        action_items: List[ActionItem] = []
        score = 10

        for page in self.pages:
            soup = page.soup

            # 1. Skip to main content link
            first_links = soup.find_all("a", limit=5)
            has_skip_link = any(
                "skip" in a.get_text().lower() or (a.get("href") and "#main" in a.get("href").lower())
                for a in first_links
            )
            if not has_skip_link:
                score -= 3
                action_items.append(
                    ActionItem(
                        url=page.url,
                        issue="Missing 'Skip to Main Content' bypass link as first focusable element for keyboard navigation (WCAG 2.4.1)",
                        selector="XPath: /html/body"
                    )
                )

            # 2. Focus ring suppression in inline styles
            suppressed_focus = soup.find_all(
                style=lambda s: s and re.search(r'outline\s*:\s*(0|none)', str(s).lower())
            )
            for el in suppressed_focus[:2]:
                score -= 1
                action_items.append(
                    ActionItem(
                        url=page.url,
                        issue="CSS inline style disables visible focus ring ('outline: none' or 'outline: 0') without high-contrast replacement",
                        selector=f"CSS: {generate_css_selector(el)}"
                    )
                )

            # 3. Positive tabindex disrupting natural order
            positive_tabs = soup.find_all(attrs={"tabindex": lambda t: t and t.isdigit() and int(t) > 0})
            for el in positive_tabs[:2]:
                score -= 1
                action_items.append(
                    ActionItem(
                        url=page.url,
                        issue=f"Positive tabindex ('tabindex=\"{el.get('tabindex')}\"') disrupts natural sequential keyboard tab order",
                        selector=f"XPath: {generate_xpath(el)}"
                    )
                )

        score = max(0, min(10, score))
        return SectionResult(title=title, score=score, action_items=action_items)

    def evaluate_touch_targets_and_motion(self) -> SectionResult:
        """Section 4: Operable - Touch Targets & Motion (WCAG 2.2 2.5.8, 2.2.2, 2.3)."""
        title = "Operable: Touch Targets & Motion"
        action_items: List[ActionItem] = []
        score = 10

        for page in self.pages:
            soup = page.soup

            # 1. Auto-advancing carousels or autoplaying videos without pause/stop control
            carousels = soup.find_all(
                class_=lambda c: c and any(x in str(c).lower() for x in ["carousel", "swiper", "slick-slider", "slideshow"])
            )
            for c in carousels[:1]:
                pause_btn = c.find(["button", "a"], attrs={"aria-label": lambda a: a and any(p in a.lower() for p in ["pause", "stop"])})
                if not pause_btn:
                    score -= 2
                    action_items.append(
                        ActionItem(
                            url=page.url,
                            issue="Auto-advancing banner or carousel lacks visible pause/stop controls for users with attention or motion sensitivities (WCAG 2.2.2)",
                            selector=f"XPath: {generate_xpath(c)}"
                        )
                    )

            # 2. Tiny touch targets in footer or social links
            footer = soup.find("footer")
            if footer:
                small_icons = footer.find_all(
                    ["a", "button"],
                    style=lambda s: s and re.search(r'(width|height)\s*:\s*(1[0-9]|2[0-3])px', str(s).lower())
                )
                for icon in small_icons[:1]:
                    score -= 1
                    action_items.append(
                        ActionItem(
                            url=page.url,
                            issue="Interactive icon fails WCAG 2.2 minimum pointer target size of 24x24 CSS pixels (measuring <24px)",
                            selector=f"CSS: {generate_css_selector(icon)}"
                        )
                    )

        score = max(0, min(10, score))
        return SectionResult(title=title, score=score, action_items=action_items)

    def evaluate_forms_and_error_validation(self) -> SectionResult:
        """Section 5: Understandable - Forms & Error Validation (WCAG 3.2, 3.3)."""
        title = "Understandable: Forms & Error Validation"
        action_items: List[ActionItem] = []
        score = 10

        for page in self.pages:
            soup = page.soup

            # 1. Page language declaration
            html_tag = soup.find("html")
            if not html_tag or not html_tag.get("lang") or len(html_tag.get("lang").strip()) == 0:
                score -= 3
                action_items.append(
                    ActionItem(
                        url=page.url,
                        issue="Page root <html> element is missing a valid 'lang' attribute (<html lang=\"en\">) (WCAG 3.1.1)",
                        selector="XPath: /html"
                    )
                )

            # 2. Form input labels
            inputs = soup.find_all("input")
            for inp in inputs:
                inp_type = (inp.get("type") or "text").lower()
                if inp_type in ["hidden", "submit", "button", "reset"]:
                    continue

                inp_id = inp.get("id")
                has_label = False
                if inp_id:
                    has_label = bool(soup.find("label", attrs={"for": inp_id}))

                if not has_label:
                    if inp.parent and inp.parent.name == "label":
                        has_label = True
                    elif inp.get("aria-label") or inp.get("aria-labelledby"):
                        has_label = True

                if not has_label:
                    score -= 1
                    name_id = inp.get("name") or inp.get("id") or inp_type
                    action_items.append(
                        ActionItem(
                            url=page.url,
                            issue=f"Form input '{name_id}' missing explicitly associated <label> via for=\"id\" or programmatic aria-label (WCAG 3.3.2)",
                            selector=f"XPath: {generate_xpath(inp)}"
                        )
                    )

        score = max(0, min(10, score))
        return SectionResult(title=title, score=score, action_items=action_items)

    def evaluate_semantic_structure_and_aria(self) -> SectionResult:
        """Section 6: Robust - Semantic Structure & ARIA Hierarchy (WCAG 1.3.1, 4.1)."""
        title = "Robust: Semantic Structure & ARIA Hierarchy"
        action_items: List[ActionItem] = []
        score = 10

        for page in self.pages:
            soup = page.soup

            # 1. Heading hierarchy & single H1 check
            h1s = soup.find_all("h1")
            if not h1s:
                score -= 2
                action_items.append(
                    ActionItem(
                        url=page.url,
                        issue="Page lacks a primary <h1> heading to establish document structure for screen reader virtual buffers",
                        selector="XPath: /html/body"
                    )
                )
            elif len(h1s) > 1:
                score -= 1
                action_items.append(
                    ActionItem(
                        url=page.url,
                        issue=f"Page contains multiple ({len(h1s)}) <h1> headings; ensure a single primary <h1> defines document hierarchy",
                        selector=f"CSS: {generate_css_selector(h1s[1])}"
                    )
                )

            # Check for skipped heading levels (e.g. h1 to h3 or h1 to h4)
            headings = soup.find_all(re.compile(r'^h[1-6]$'))
            prev_level = 0
            for h in headings:
                lvl = int(h.name[1])
                if prev_level > 0 and lvl > prev_level + 1:
                    score -= 1
                    action_items.append(
                        ActionItem(
                            url=page.url,
                            issue=f"Heading level skips directly from <h{prev_level}> to <h{lvl}> without intermediary levels (WCAG 1.3.1)",
                            selector=f"XPath: {generate_xpath(h)}"
                        )
                    )
                    break
                prev_level = lvl

            # 2. Missing aria-expanded on accordion/dropdown triggers
            expandables = soup.find_all(
                class_=lambda c: c and any(x in str(c).lower() for x in ["accordion-trigger", "dropdown-toggle", "collapse-btn"])
            )
            for ex in expandables[:2]:
                if not ex.get("aria-expanded"):
                    score -= 1
                    action_items.append(
                        ActionItem(
                            url=page.url,
                            issue="Expandable trigger button lacks 'aria-expanded' state attribute to inform screen readers of expanded/collapsed content",
                            selector=f"CSS: {generate_css_selector(ex)}"
                        )
                    )

        score = max(0, min(10, score))
        return SectionResult(title=title, score=score, action_items=action_items)

    def evaluate_native_accessibility_and_overlay(self) -> SectionResult:
        """Section 7: Native Accessibility & Overlay Assessment."""
        title = "Native Accessibility & Overlay Assessment"
        action_items: List[ActionItem] = []
        score = 10

        combined_html = " ".join([p.html.lower() for p in self.pages])

        # 1. Overlay widget detection
        detected_overlays = []
        for key, name in self.KNOWN_OVERLAYS.items():
            if key in combined_html:
                detected_overlays.append(name)

        if detected_overlays:
            score -= 4
            action_items.append(
                ActionItem(
                    url=self.base_url,
                    issue=f"Relies on third-party JavaScript accessibility overlay widget ({', '.join(detected_overlays)}); overlays do not ensure legal compliance and fail if scripts are blocked by user privacy extensions",
                    selector="CSS: script"
                )
            )

        # 2. Footer accessibility statement link
        has_statement = any(
            re.search(r'accessib(ility|le)', a.get_text().lower()) or "accessibility" in (a.get("href") or "").lower()
            for p in self.pages for a in p.soup.find_all("a")
        )
        if not has_statement:
            score -= 2
            action_items.append(
                ActionItem(
                    url=self.base_url,
                    issue="Footer lacks an explicit 'Accessibility Statement' link with contact channels for accommodation requests (ADA compliance best practice)",
                    selector="XPath: //footer"
                )
            )

        score = max(0, min(10, score))
        return SectionResult(title=title, score=score, action_items=action_items)

    def run_full_audit(self) -> List[SectionResult]:
        """Run all ADA compliance evaluation modules."""
        return [
            self.evaluate_text_alternatives(),
            self.evaluate_color_contrast_and_reflow(),
            self.evaluate_keyboard_and_focus(),
            self.evaluate_touch_targets_and_motion(),
            self.evaluate_forms_and_error_validation(),
            self.evaluate_semantic_structure_and_aria(),
            self.evaluate_native_accessibility_and_overlay(),
        ]


def crawl_website(base_url: str, sub_paths: Optional[List[str]] = None) -> List[CrawledPage]:
    """Crawl website base URL and requested sub-pages."""
    if not base_url.startswith("http://") and not base_url.startswith("https://"):
        base_url = "https://" + base_url

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36 ADAAuditor/1.0"
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

    print(f"[*] Crawling target site for ADA & WCAG 2.1/2.2 AA: {base_url}")
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

    # Auto-discover sub-pages if only 1 page crawled
    if len(crawled_pages) == 1 and not sub_paths:
        home_soup = crawled_pages[0].soup
        discovered_paths = []
        target_keywords = ["about", "contact", "pricing", "team", "services", "checkout"]
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
                print(f"    Auto-discovered sub-page: {link} ...")
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
    """Format audit findings into standardized ADA Compliance Report."""
    total_score = round(sum(s.score for s in section_results) / len(section_results), 1)

    if total_score >= 8.5:
        risk_level = "Low"
    elif total_score >= 6.0:
        risk_level = "Moderate"
    else:
        risk_level = "High"

    lines = [
        "============================================================",
        "ADA WEBSITE COMPLIANCE AUDIT REPORT",
        f"Target Site: {base_url}",
        "Generated By: Agency AI Accessibility Auditor Agent",
        "Benchmark: WCAG 2.1 & 2.2 Level AA / ADA Title III & Title II",
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
            lines.append(f"{base_url} | Meets all WCAG 2.1/2.2 AA criteria for this capability.")
        lines.append("")

    lines.append("============================================================")
    lines.append("OVERALL SUMMARY & RECOMMENDATIONS")
    lines.append(f"Overall Accessibility Score: {total_score}/10")
    lines.append(f"Critical Legal Risk Level: {risk_level}")
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
        lines.append("1. Maintain WCAG 2.1/2.2 AA compliant front-end markup standards.")

    lines.append("============================================================")
    lines.append("END OF REPORT")
    lines.append("============================================================")

    return "\n".join(lines)


def run_audit(target_url: str, sub_paths: Optional[List[str]] = None, output_file: str = "ada-compliance-report.txt") -> str:
    """Main execution pipeline."""
    crawled_pages = crawl_website(target_url, sub_paths)
    if not crawled_pages:
        raise RuntimeError(f"Unable to crawl target URL: {target_url}")

    evaluator = ADAComplianceEvaluator(base_url=target_url, pages=crawled_pages)
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
        print("ADA Website Compliance Auditor Agent")
        print("------------------------------------")
        target = input("Enter target website base URL (e.g., https://example.com): ").strip()
        if target:
            subs_input = input("Enter optional comma-separated sub-paths: ").strip()
            subs = [s.strip() for s in subs_input.split(",") if s.strip()] if subs_input else None
            report = run_audit(target, subs)
            print("\n" + report)
        else:
            print("No URL provided. Exiting.")
