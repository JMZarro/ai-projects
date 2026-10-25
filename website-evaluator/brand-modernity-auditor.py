"""
Brand Modernity & Content Freshness Auditor
===========================================
Automated crawling and evaluation engine for Brand Modernity, Content Freshness,
Visual Trust Signals, and High-DPI / Retina Asset Clarity.

Evaluates websites across:
1. Visual Trust Clues: Copyright Year & Maintenance Recency (outdated copyright years, stale notices)
2. Social Channel Integrity & Active Community Links (placeholder social links, broken/defunct handles)
3. Visual Trend Modernity & Skeuomorphic Anti-Patterns (harsh drop shadows, deprecated HTML, stock tropes)
4. Cross-Browser & Retina Clarity: High-DPI Assets (blurry raster logos/icons, missing SVG vector assets)
5. Content Freshness & Publication Recency (abandoned blog recency, stale case studies)
6. Modern Typography & Color Contrast Standards (font family bloat, low-contrast whisper text)

Generates a standardized 'brand-modernity-report.txt' audit report.
"""

import sys
import os
import re
import urllib.parse
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Set
import requests
from bs4 import BeautifulSoup, Tag


CURRENT_YEAR = 2026


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


class BrandModernityEvaluator:
    """Evaluates crawled pages for Brand Modernity, Content Freshness, and Visual Trust."""

    SOCIAL_DOMAINS = [
        "facebook.com", "instagram.com", "twitter.com", "x.com",
        "linkedin.com", "youtube.com", "tiktok.com", "pinterest.com"
    ]

    PLACEHOLDER_SUBSTRINGS = [
        "yourhandle", "yourpage", "yourcompany", "company_name", "example",
        "username", "#", "javascript:void(0)", "insert_link"
    ]

    DATED_STOCK_TERMS = [
        "handshake", "call-center", "thumbs-up", "businessmen", "business-meeting",
        "happy-customer", "smiling-agent", "clipart"
    ]

    def __init__(self, base_url: str, pages: List[CrawledPage], tested_social: Optional[Dict[str, int]] = None):
        self.base_url = base_url
        self.pages = pages
        self.tested_social = tested_social or {}

    def evaluate_copyright_and_maintenance(self) -> SectionResult:
        """Section 1: Visual Trust Clues: Copyright Year & Maintenance Recency."""
        title = "Visual Trust Clues: Copyright Year & Maintenance Recency"
        action_items: List[ActionItem] = []
        score = 10

        copyright_found = False

        for page in self.pages:
            soup = page.soup
            footer = soup.find("footer") or soup.find(id=re.compile(r'footer', re.I)) or soup.find(class_=re.compile(r'footer', re.I))
            search_area = footer if footer else soup

            # Search for copyright strings
            text = search_area.get_text()
            matches = re.findall(r'(?:©|&copy;|copyright)\s*(?:20\d\d\s*[-–]\s*)?(20[0-2][0-9])', text, re.IGNORECASE)

            if matches:
                copyright_found = True
                latest_year = max(int(m) for m in matches)
                if latest_year < CURRENT_YEAR:
                    years_outdated = CURRENT_YEAR - latest_year
                    score -= min(6, 2 * years_outdated)
                    target_tag = footer if footer else soup.find("body")
                    action_items.append(
                        ActionItem(
                            url=page.url,
                            issue=f"Footer displays an outdated copyright year ('(c) {latest_year}'); stale copyright ({years_outdated} years old) signals brand abandonment or neglected site maintenance to prospective buyers",
                            selector=f"XPath: {generate_xpath(target_tag)}"
                        )
                    )

            # Check for stale pandemic or old promotional notices
            stale_banners = soup.find_all(
                lambda t: any(k in t.get_text().lower() for k in ["covid-19 update", "holiday 202", "sale 2021", "sale 2022", "sale 2023"])
            )
            for b in stale_banners[:1]:
                score -= 2
                action_items.append(
                    ActionItem(
                        url=page.url,
                        issue=f"Promotional or advisory text references stale outdated events ('{b.get_text(strip=True)[:45]}...')",
                        selector=f"CSS: {generate_css_selector(b)}"
                    )
                )

        if not copyright_found:
            score -= 2
            action_items.append(
                ActionItem(
                    url=self.base_url,
                    issue="No copyright statement or publication year detected in footer; missing standard digital trust anchor",
                    selector="XPath: //footer"
                )
            )

        score = max(0, min(10, score))
        return SectionResult(title=title, score=score, action_items=action_items)

    def evaluate_social_channels(self) -> SectionResult:
        """Section 2: Social Channel Integrity & Active Community Links."""
        title = "Social Channel Integrity & Active Community Links"
        action_items: List[ActionItem] = []
        score = 10

        social_links_found = False

        for page in self.pages:
            soup = page.soup
            anchors = soup.find_all("a", href=True)

            for a in anchors:
                href = a["href"].strip().lower()
                for domain in self.SOCIAL_DOMAINS:
                    if domain in href:
                        social_links_found = True

                        # 1. Check for placeholder links
                        if any(p in href for p in self.PLACEHOLDER_SUBSTRINGS) or href in ["#", "/#"]:
                            score -= 2
                            action_items.append(
                                ActionItem(
                                    url=page.url,
                                    issue=f"Social link for {domain} points to an unconfigured template placeholder ('{a['href']}'); damages credibility with prospective customers",
                                    selector=f"CSS: {generate_css_selector(a)}"
                                )
                            )

                        # 2. Check for legacy Twitter URL (twitter.com instead of x.com)
                        if "twitter.com" in href and "x.com" not in href:
                            score -= 1
                            action_items.append(
                                ActionItem(
                                    url=page.url,
                                    issue="Social profile link retains legacy 'twitter.com' domain and obsolete bird icon instead of contemporary X branding",
                                    selector=f"XPath: {generate_xpath(a)}"
                                )
                            )

        # 3. Check tested social links for 404s
        for link, status in self.tested_social.items():
            if status in [404, 410]:
                score -= 3
                action_items.append(
                    ActionItem(
                        url=self.base_url,
                        issue=f"Social media link '{link}' returns HTTP {status} (Dead / Deleted Account)",
                        selector=f"a[href*='{urllib.parse.urlparse(link).netloc}']"
                    )
                )

        if not social_links_found:
            score -= 2
            action_items.append(
                ActionItem(
                    url=self.base_url,
                    issue="Website has zero links to verified social media channels, missing an essential external proof-of-life trust signal",
                    selector="XPath: //footer"
                )
            )

        score = max(0, min(10, score))
        return SectionResult(title=title, score=score, action_items=action_items)

    def evaluate_visual_modernity(self) -> SectionResult:
        """Section 3: Visual Trend Modernity & Skeuomorphic Anti-Patterns."""
        title = "Visual Trend Modernity & Skeuomorphic Anti-Patterns"
        action_items: List[ActionItem] = []
        score = 10

        for page in self.pages:
            soup = page.soup

            # 1. Deprecated HTML tags (<marquee>, <font>, <center>, <blink>)
            deprecated_tags = soup.find_all(["marquee", "font", "center", "blink", "frameset"])
            for dep in deprecated_tags[:2]:
                score -= 2
                action_items.append(
                    ActionItem(
                        url=page.url,
                        issue=f"Page utilizes obsolete, deprecated HTML markup (<{dep.name}>); reflects antiquated 1990s/2000s codebase construction",
                        selector=f"XPath: {generate_xpath(dep)}"
                    )
                )

            # 2. Harsh drop shadows & skeuomorphic styling in inline styles
            styled_elements = soup.find_all(style=True)
            for el in styled_elements:
                style = el["style"].lower()
                # Check for harsh black box shadows
                if "box-shadow" in style:
                    if re.search(r'box-shadow\s*:\s*\d+px\s+\d+px\s+[0-4]px\s+(?:#000|black|rgba\(0,\s*0,\s*0,\s*1\))', style):
                        score -= 1
                        action_items.append(
                            ActionItem(
                                url=page.url,
                                issue="Element uses harsh, un-diffused black drop shadow ('box-shadow') instead of subtle, contemporary elevation styling",
                                selector=f"CSS: {generate_css_selector(el)}"
                            )
                        )
                        break

            # 3. Dated stock photo naming conventions
            images = soup.find_all("img")
            for img in images:
                src = (img.get("src") or "").lower()
                alt = (img.get("alt") or "").lower()
                for term in self.DATED_STOCK_TERMS:
                    if term in src or term in alt:
                        score -= 1
                        action_items.append(
                            ActionItem(
                                url=page.url,
                                issue=f"Image reflects generic, dated stock photography tropes ('{term}'); replace with authentic product imagery or modern editorial photography",
                                selector=f"XPath: {generate_xpath(img)}"
                            )
                        )
                        break

        score = max(0, min(10, score))
        return SectionResult(title=title, score=score, action_items=action_items)

    def evaluate_retina_and_icon_clarity(self) -> SectionResult:
        """Section 4: Cross-Browser & Retina Clarity: High-DPI Assets."""
        title = "Cross-Browser & Retina Clarity: High-DPI Assets"
        action_items: List[ActionItem] = []
        score = 10

        for page in self.pages:
            soup = page.soup

            # 1. Primary brand logo format check
            logo = soup.find(lambda t: t.name in ['img', 'svg'] and any(
                k in " ".join(t.get('class', [])).lower() or k in (t.get('id') or '').lower() or k in (t.get('alt') or '').lower()
                for k in ['logo', 'brand']
            ))

            if not logo:
                header = soup.find("header") or soup.find("nav")
                if header:
                    header_imgs = header.find_all("img")
                    if header_imgs:
                        logo = header_imgs[0]

            if logo and logo.name == "img":
                src = (logo.get("src") or "").lower()
                clean_src = src.split("?")[0]
                has_srcset = bool(logo.get("srcset"))

                if clean_src.endswith((".png", ".jpg", ".jpeg")):
                    if not has_srcset:
                        score -= 3
                        logo_name = src.split("/")[-1].split("?")[0]
                        action_items.append(
                            ActionItem(
                                url=page.url,
                                issue=f"Brand logo uses low-DPI raster format ('{logo_name}') without a Retina '@2x' srcset or SVG vector equivalent; appears blurry/pixelated on high-DPI displays",
                                selector=f"CSS: {generate_css_selector(logo)}"
                            )
                        )

            # 2. UI icons raster check
            icons = soup.find_all(
                lambda t: t.name == "img" and any(k in (t.get("src") or "").lower() for k in ["icon", "bullet", "arrow"])
            )
            for ico in icons[:2]:
                isrc = (ico.get("src") or "").lower().split("?")[0]
                if isrc.endswith((".gif", ".png", ".jpg")):
                    score -= 1
                    icon_name = isrc.split("/")[-1]
                    action_items.append(
                        ActionItem(
                            url=page.url,
                            issue=f"UI icon uses low-resolution raster graphic ('{icon_name}'); replace with crisp SVG vector graphics or inline SVG sprites",
                            selector=f"XPath: {generate_xpath(ico)}"
                        )
                    )
                    break

            # 3. High-resolution touch icon & SVG Favicon check
            favicons = soup.find_all("link", attrs={"rel": lambda r: r and "icon" in str(r).lower()})
            has_apple_touch = any("apple-touch-icon" in str(l.get("rel", "")).lower() for l in favicons)
            has_svg_favicon = any("svg" in str(l.get("type", "")).lower() or str(l.get("href", "")).endswith(".svg") for l in favicons)

            if not has_apple_touch and not has_svg_favicon:
                score -= 1
                action_items.append(
                    ActionItem(
                        url=page.url,
                        issue="Missing modern high-DPI touch icon ('apple-touch-icon' 180x180px) and scalable SVG favicon; browser tab appears fuzzy on 4K screens",
                        selector="CSS: head"
                    )
                )

        score = max(0, min(10, score))
        return SectionResult(title=title, score=score, action_items=action_items)

    def evaluate_content_freshness(self) -> SectionResult:
        """Section 5: Content Freshness & Publication Recency."""
        title = "Content Freshness & Publication Recency"
        action_items: List[ActionItem] = []
        score = 10

        all_years = []

        for page in self.pages:
            soup = page.soup

            # Check article dates in <time> or post date classes
            date_tags = soup.find_all(["time", "span", "p"], class_=lambda c: c and any(x in str(c).lower() for x in ["date", "post-date", "published", "time"]))
            for dt in date_tags:
                txt = dt.get_text()
                years = re.findall(r'\b(201[0-9]|202[0-6])\b', txt)
                all_years.extend([int(y) for y in years])

        # If blog or news pages were crawled and dates were found
        if all_years:
            newest_year = max(all_years)
            if newest_year < CURRENT_YEAR - 1:  # e.g. newest post is from 2024 or earlier
                years_stale = CURRENT_YEAR - newest_year
                score -= min(5, years_stale * 2)
                action_items.append(
                    ActionItem(
                        url=self.base_url,
                        issue=f"Blog or news section appears abandoned; most recent publication date found is from {newest_year} ({years_stale} years old), creating an impression of corporate stagnation",
                        selector="CSS: article, .blog-grid, .post"
                    )
                )

        score = max(0, min(10, score))
        return SectionResult(title=title, score=score, action_items=action_items)

    def evaluate_typography_and_contrast(self) -> SectionResult:
        """Section 6: Modern Typography & Color Contrast Standards."""
        title = "Modern Typography & Color Contrast Standards"
        action_items: List[ActionItem] = []
        score = 10

        for page in self.pages:
            soup = page.soup

            # 1. Count imported font families
            font_links = soup.find_all("link", href=lambda h: h and "fonts.googleapis.com" in h)
            imported_families = set()
            for l in font_links:
                href = l["href"]
                families = re.findall(r'family=([^&:]+)', href)
                for f in families:
                    imported_families.add(urllib.parse.unquote_plus(f))

            if len(imported_families) > 3:
                score -= 2
                action_items.append(
                    ActionItem(
                        url=page.url,
                        issue=f"Page loads {len(imported_families)} distinct external font families ({', '.join(list(imported_families)[:4])}); excessive font variety harms brand visual cohesion and slows rendering",
                        selector="CSS: head"
                    )
                )

            # 2. Whisper gray low-contrast text in inline styles
            subdued_tags = soup.find_all(
                style=lambda s: s and re.search(r'color\s*:\s*(#(?:a0a0a0|b0b0b0|cccccc|ccc|999999|999|e0e0e0|d3d3d3))', str(s).lower())
            )
            for el in subdued_tags[:1]:
                score -= 2
                action_items.append(
                    ActionItem(
                        url=page.url,
                        issue="Text uses low-contrast 'whisper gray' color styling, violating modern readability and visual hierarchy guidelines",
                        selector=f"CSS: {generate_css_selector(el)}"
                    )
                )

        score = max(0, min(10, score))
        return SectionResult(title=title, score=score, action_items=action_items)

    def run_full_audit(self) -> List[SectionResult]:
        """Execute all brand modernity and content freshness evaluation modules."""
        return [
            self.evaluate_copyright_and_maintenance(),
            self.evaluate_social_channels(),
            self.evaluate_visual_modernity(),
            self.evaluate_retina_and_icon_clarity(),
            self.evaluate_content_freshness(),
            self.evaluate_typography_and_contrast(),
        ]


def crawl_website(base_url: str, sub_paths: Optional[List[str]] = None) -> Tuple[List[CrawledPage], Dict[str, int]]:
    """Crawl website and sample social media channels for 404 dead ends."""
    if not base_url.startswith("http://") and not base_url.startswith("https://"):
        base_url = "https://" + base_url

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36 BrandModernityAuditor/1.0"
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

    print(f"[*] Crawling target site for Brand Modernity & Freshness: {base_url}")
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

    # Auto-discover blog, about, news sub-pages
    if len(crawled_pages) == 1 and not sub_paths:
        home_soup = crawled_pages[0].soup
        discovered_paths = []
        target_keywords = ["blog", "news", "about", "press", "company", "media"]
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

    # Sample test social links
    tested_social: Dict[str, int] = {}
    sampled_social = set()
    for page in crawled_pages:
        for a in page.soup.find_all("a", href=True):
            h = a["href"].strip()
            for sdom in ["facebook.com", "instagram.com", "twitter.com", "x.com", "linkedin.com", "youtube.com"]:
                if sdom in h.lower() and not any(p in h.lower() for p in ["#", "yourhandle", "company_name"]):
                    sampled_social.add(h)

    for slink in list(sampled_social)[:3]:
        try:
            h_resp = session.head(slink, timeout=5, allow_redirects=True)
            tested_social[slink] = h_resp.status_code
        except Exception:
            pass

    return crawled_pages, tested_social


def format_report(base_url: str, section_results: List[SectionResult]) -> str:
    """Format audit findings into standardized Brand Modernity report."""
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
        "BRAND MODERNITY & CONTENT FRESHNESS AUDIT REPORT",
        f"Target Site: {base_url}",
        "Generated By: Agency AI Brand Modernity Auditor Agent",
        "Benchmark: Contemporary Web Design & Brand Trust Benchmarks",
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
            lines.append(f"{base_url} | Meets all contemporary brand design and content recency standards.")
        lines.append("")

    lines.append("============================================================")
    lines.append("OVERALL SUMMARY & RECOMMENDATIONS")
    lines.append(f"Overall Brand Modernity Score: {total_score}/10")
    lines.append(f"Brand Trust Degradation Risk Level: {risk_level}")
    lines.append("Primary Brand Obsoletion Bottlenecks:")

    # Identify top bottlenecks from lowest scoring sections
    sorted_sections = sorted(section_results, key=lambda s: s.score)
    bottleneck_idx = 1
    for s in sorted_sections[:2]:
        if s.action_items:
            lines.append(f"{bottleneck_idx}. [{s.title}] {s.action_items[0].issue}")
            bottleneck_idx += 1

    if bottleneck_idx == 1:
        lines.append("1. None identified; brand displays contemporary visual trust signals.")

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
        lines.append("1. Maintain current modern typography and asset delivery standards.")

    lines.append("============================================================")
    lines.append("END OF REPORT")
    lines.append("============================================================")

    return "\n".join(lines)


def run_audit(target_url: str, sub_paths: Optional[List[str]] = None, output_file: str = "brand-modernity-report.txt") -> str:
    """Main brand modernity audit execution pipeline."""
    crawled_pages, tested_social = crawl_website(target_url, sub_paths)
    if not crawled_pages:
        raise RuntimeError(f"Unable to crawl target URL: {target_url}")

    evaluator = BrandModernityEvaluator(base_url=target_url, pages=crawled_pages, tested_social=tested_social)
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
        print("Brand Modernity & Content Freshness Auditor Agent")
        print("-------------------------------------------------")
        target = input("Enter target website base URL (e.g., https://example.com): ").strip()
        if target:
            subs_input = input("Enter optional comma-separated sub-paths: ").strip()
            subs = [s.strip() for s in subs_input.split(",") if s.strip()] if subs_input else None
            report = run_audit(target, subs)
            print("\n" + report)
        else:
            print("No URL provided. Exiting.")
