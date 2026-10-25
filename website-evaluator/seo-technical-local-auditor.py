"""
Technical & Local SEO Health Auditor
====================================
Automated crawling and evaluation engine for Google Search Essentials, On-Page SEO,
Structured Data (Schema.org), Link & Redirect Hygiene, and Local Pack Visibility.

Evaluates websites across:
1. Metadata & SERP Snippet Optimization (title tags, meta descriptions, Open Graph)
2. Document Heading Hierarchy (H1-H6 outline, single H1, no skipped levels)
3. Structured Data (Schema.org) & Rich Snippets (LocalBusiness, Organization, Service, Product, FAQPage)
4. Broken Links, HTTP Status & Redirect Hygiene (404s, 302 vs 301 redirects, mixed content)
5. Indexing Directives & Canonicalization (rel="canonical", noindex warnings, robots meta)
6. Local SEO Citations & NAP Consistency (Name, Address, Phone, Google Maps embeds, local keywords)

Generates a standardized 'seo-health-report.txt' audit report.
"""

import sys
import os
import re
import json
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
    redirect_chain: List[Tuple[int, str]] = field(default_factory=list)
    soup: BeautifulSoup = field(init=False)

    def __post_init__(self):
        self.soup = BeautifulSoup(self.html, "html.parser")


class SEOTechnicalLocalEvaluator:
    """Evaluates crawled pages for Technical SEO and Local SEO health."""

    LOCAL_BIZ_TYPES = [
        "localbusiness", "organization", "corporation", "professionalservice",
        "medicalbusiness", "restaurant", "store", "automotivebusiness", "legalbusiness",
        "homeandconstructionservice", "financialservice", "dentist", "physician", "plumber"
    ]

    PHONE_REGEX = re.compile(
        r'(?:\+?1[-.\s]?)?\(?([2-9]\d{2})\)?[-.\s]?(\d{3})[-.\s]?(\d{4})\b'
    )

    ADDRESS_KEYWORD_REGEX = re.compile(
        r'\b\d{1,5}\s+[A-Za-z0-9\s.,#-]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Way|Suite|Ste|Floor|Fl|Highway|Hwy|Pkwy|Parkway)\b',
        re.IGNORECASE
    )

    def __init__(self, base_url: str, pages: List[CrawledPage], tested_links: Optional[Dict[str, int]] = None):
        self.base_url = base_url
        self.pages = pages
        self.tested_links = tested_links or {}  # {url: status_code}

    def evaluate_metadata(self) -> SectionResult:
        """Section 1: Metadata & SERP Snippet Optimization."""
        title = "Metadata & SERP Snippet Optimization"
        action_items: List[ActionItem] = []
        score = 10

        seen_titles = {}

        for page in self.pages:
            soup = page.soup

            # 1. Title Tag Check
            title_tag = soup.find("title")
            if not title_tag or not title_tag.get_text(strip=True):
                score -= 3
                action_items.append(
                    ActionItem(
                        url=page.url,
                        issue="Page is missing a '<title>' tag; Google will generate an arbitrary title in search results",
                        selector="XPath: /html/head"
                    )
                )
            else:
                title_text = title_tag.get_text(strip=True)
                title_len = len(title_text)

                if title_len > 60:
                    score -= 1
                    action_items.append(
                        ActionItem(
                            url=page.url,
                            issue=f"Title tag is {title_len} characters long (exceeds 60-character limit) and will be truncated with an ellipsis in Google SERPs ('{title_text}')",
                            selector="XPath: /html/head/title"
                        )
                    )
                elif title_len < 30:
                    score -= 1
                    action_items.append(
                        ActionItem(
                            url=page.url,
                            issue=f"Title tag is under-optimized and too short ({title_len} characters: '{title_text}'); missing secondary keyword or branding",
                            selector="XPath: /html/head/title"
                        )
                    )

                # Duplicate title check
                if title_text in seen_titles:
                    score -= 1
                    action_items.append(
                        ActionItem(
                            url=page.url,
                            issue=f"Duplicate title tag identical to {seen_titles[title_text]} ('{title_text}'); title tags must be unique per page",
                            selector="XPath: /html/head/title"
                        )
                    )
                else:
                    seen_titles[title_text] = page.url

            # 2. Meta Description Check
            meta_desc = soup.find("meta", attrs={"name": re.compile(r'^description$', re.I)})
            if not meta_desc or not meta_desc.get("content", "").strip():
                score -= 3
                action_items.append(
                    ActionItem(
                        url=page.url,
                        issue="Missing '<meta name=\"description\">' tag; search engines will extract random body copy as the snippet",
                        selector="CSS: head"
                    )
                )
            else:
                desc_text = meta_desc.get("content", "").strip()
                desc_len = len(desc_text)

                if desc_len > 160:
                    score -= 1
                    action_items.append(
                        ActionItem(
                            url=page.url,
                            issue=f"Meta description is {desc_len} characters long (exceeds 160 characters) and will truncate on mobile and desktop SERPs",
                            selector="CSS: head > meta[name='description']"
                        )
                    )
                elif desc_len < 70:
                    score -= 1
                    action_items.append(
                        ActionItem(
                            url=page.url,
                            issue=f"Meta description is too short ({desc_len} characters: '{desc_text}'); expand to 120-160 characters with clear call-to-action",
                            selector="CSS: head > meta[name='description']"
                        )
                    )

            # 3. Open Graph Tags
            og_title = soup.find("meta", attrs={"property": "og:title"})
            og_desc = soup.find("meta", attrs={"property": "og:description"})
            og_img = soup.find("meta", attrs={"property": "og:image"})

            if not og_title or not og_desc or not og_img:
                score -= 1
                missing_og = []
                if not og_title: missing_og.append("og:title")
                if not og_desc: missing_og.append("og:description")
                if not og_img: missing_og.append("og:image")
                action_items.append(
                    ActionItem(
                        url=page.url,
                        issue=f"Missing Open Graph social metadata tags ({', '.join(missing_og)}) for rich link previews",
                        selector="CSS: head"
                    )
                )

        score = max(0, min(10, score))
        return SectionResult(title=title, score=score, action_items=action_items)

    def evaluate_heading_hierarchy(self) -> SectionResult:
        """Section 2: Document Heading Hierarchy (H1-H6)."""
        title = "Document Heading Hierarchy (H1-H6)"
        action_items: List[ActionItem] = []
        score = 10

        for page in self.pages:
            soup = page.soup

            # 1. H1 Tag Count
            h1s = soup.find_all("h1")
            if not h1s:
                score -= 3
                action_items.append(
                    ActionItem(
                        url=page.url,
                        issue="Page lacks a primary <h1> heading; search engines cannot establish top-level page topic",
                        selector="XPath: /html/body"
                    )
                )
            elif len(h1s) > 1:
                score -= 2
                h1_texts = [f"'{h.get_text(strip=True)[:30]}'" for h in h1s[:3]]
                action_items.append(
                    ActionItem(
                        url=page.url,
                        issue=f"Multiple ({len(h1s)}) <h1> headings found ({', '.join(h1_texts)}); consolidate to a single authoritative <h1> per page",
                        selector=f"CSS: {generate_css_selector(h1s[1])}"
                    )
                )

            # 2. Skipped Heading Levels & Empty Headings
            headings = soup.find_all(re.compile(r'^h[1-6]$'))
            prev_level = 0
            for h in headings:
                lvl = int(h.name[1])
                text = h.get_text(strip=True)

                if not text:
                    score -= 1
                    action_items.append(
                        ActionItem(
                            url=page.url,
                            issue=f"Heading tag <{h.name}> is empty or contains only whitespace; remove styling tag or add descriptive text",
                            selector=f"XPath: {generate_xpath(h)}"
                        )
                    )

                if prev_level > 0 and lvl > prev_level + 1:
                    score -= 1
                    action_items.append(
                        ActionItem(
                            url=page.url,
                            issue=f"Heading outline skips levels from <h{prev_level}> directly to <h{lvl}> without an intermediary level, breaking document semantic flow",
                            selector=f"XPath: {generate_xpath(h)}"
                        )
                    )
                    break
                prev_level = lvl

        score = max(0, min(10, score))
        return SectionResult(title=title, score=score, action_items=action_items)

    def evaluate_structured_data(self) -> SectionResult:
        """Section 3: Structured Data (Schema.org) & Rich Snippets."""
        title = "Structured Data (Schema.org) & Rich Snippets"
        action_items: List[ActionItem] = []
        score = 10

        schema_found = False

        for page in self.pages:
            soup = page.soup
            json_scripts = soup.find_all("script", attrs={"type": "application/ld+json"})

            found_types = set()
            local_schema_found = False

            for s in json_scripts:
                try:
                    data = json.loads(s.get_text())
                    items = data if isinstance(data, list) else (data.get("@graph") if isinstance(data, dict) and "@graph" in data else [data])
                    for item in items:
                        if isinstance(item, dict):
                            t = item.get("@type", "")
                            if isinstance(t, list):
                                for sub_t in t:
                                    found_types.add(sub_t.lower())
                            elif isinstance(t, str):
                                found_types.add(t.lower())

                            # Check LocalBusiness details
                            if any(lt in str(t).lower() for lt in self.LOCAL_BIZ_TYPES):
                                local_schema_found = True
                                missing_nap = []
                                if not item.get("name"): missing_nap.append("name")
                                if not item.get("telephone"): missing_nap.append("telephone")
                                if not item.get("address"): missing_nap.append("address")
                                if missing_nap:
                                    score -= 2
                                    action_items.append(
                                        ActionItem(
                                            url=page.url,
                                            issue=f"Schema '{t}' is missing required local entity fields ({', '.join(missing_nap)})",
                                            selector=f"CSS: {generate_css_selector(s)}"
                                        )
                                    )
                except Exception:
                    score -= 2
                    action_items.append(
                        ActionItem(
                            url=page.url,
                            issue="JSON-LD structured data script contains malformed JSON syntax and cannot be parsed by Google search crawlers",
                            selector=f"CSS: {generate_css_selector(s)}"
                        )
                    )

            if found_types:
                schema_found = True

            # If page is homepage or contact and has no local / organization schema
            path = urllib.parse.urlparse(page.url).path.lower()
            if path in ["", "/", "/home", "/contact", "/contact-us", "/about"]:
                if not any(t in found_types for t in self.LOCAL_BIZ_TYPES):
                    score -= 2
                    action_items.append(
                        ActionItem(
                            url=page.url,
                            issue="Missing Schema.org 'LocalBusiness' or 'Organization' JSON-LD markup to establish verified entity presence and Google Knowledge Graph identity",
                            selector="CSS: head"
                        )
                    )

            # Check for visual FAQ without FAQPage schema
            faq_elements = soup.find_all(
                class_=lambda c: c and any(x in str(c).lower() for x in ["faq", "frequently-asked", "accordion"])
            )
            if faq_elements and "faqpage" not in found_types:
                score -= 1
                action_items.append(
                    ActionItem(
                        url=page.url,
                        issue="Page displays visual FAQs but lacks corresponding 'FAQPage' Schema.org injection to capture Google SERP rich snippet dropdowns",
                        selector=f"CSS: {generate_css_selector(faq_elements[0])}"
                    )
                )

        if not schema_found:
            score = min(score, 3)

        score = max(0, min(10, score))
        return SectionResult(title=title, score=score, action_items=action_items)

    def evaluate_broken_links_and_redirects(self) -> SectionResult:
        """Section 4: Broken Links, HTTP Status & Redirect Hygiene."""
        title = "Broken Links, HTTP Status & Redirect Hygiene"
        action_items: List[ActionItem] = []
        score = 10

        # 1. Check crawled pages for 302 redirects or non-200 status
        for page in self.pages:
            if page.status_code >= 400:
                score -= 3
                action_items.append(
                    ActionItem(
                        url=page.url,
                        issue=f"Page returns HTTP {page.status_code} (Client/Server Error); broken URL wastes crawl budget and creates dead ends",
                        selector="HTTP Status"
                    )
                )

            # Check redirect chain
            for code, redir_url in page.redirect_chain:
                if code == 302:
                    score -= 2
                    action_items.append(
                        ActionItem(
                            url=page.url,
                            issue=f"URL uses temporary HTTP 302 redirect to '{redir_url}' instead of permanent HTTP 301, failing to transfer full link equity (PageRank)",
                            selector="HTTP Redirect: 302 Found"
                        )
                    )

            # 2. Check internal links on page
            soup = page.soup
            anchors = soup.find_all("a", href=True)
            for a in anchors:
                href = a["href"].strip()
                # Check insecure HTTP on HTTPS site
                if page.url.startswith("https://") and href.startswith("http://"):
                    score -= 1
                    action_items.append(
                        ActionItem(
                            url=page.url,
                            issue=f"Internal link uses insecure 'http://' protocol ('{href}'), triggering unnecessary redirect hops and mixed-security warnings",
                            selector=f"XPath: {generate_xpath(a)}"
                        )
                    )
                    break

        # 3. Check tested links results (if any links returned 404)
        for link_url, status in self.tested_links.items():
            if status == 404:
                score -= 2
                action_items.append(
                    ActionItem(
                        url=self.base_url,
                        issue=f"Internal navigation link '{link_url}' returns HTTP 404 (Not Found)",
                        selector=f"a[href*='{link_url.split('/')[-1]}']"
                    )
                )

        score = max(0, min(10, score))
        return SectionResult(title=title, score=score, action_items=action_items)

    def evaluate_indexing_and_canonicalization(self) -> SectionResult:
        """Section 5: Indexing Directives & Canonicalization."""
        title = "Indexing Directives & Canonicalization"
        action_items: List[ActionItem] = []
        score = 10

        for page in self.pages:
            soup = page.soup

            # 1. Canonical tag check
            canonical = soup.find("link", attrs={"rel": "canonical"})
            if not canonical or not canonical.get("href"):
                score -= 3
                action_items.append(
                    ActionItem(
                        url=page.url,
                        issue="Missing '<link rel=\"canonical\">' tag; search engines may index query parameter variations as duplicate content",
                        selector="CSS: head"
                    )
                )
            else:
                c_href = canonical.get("href").strip()
                parsed_c = urllib.parse.urlparse(c_href)
                parsed_p = urllib.parse.urlparse(page.url)

                # Check domain mismatch
                if parsed_c.netloc and parsed_c.netloc != parsed_p.netloc:
                    score -= 2
                    action_items.append(
                        ActionItem(
                            url=page.url,
                            issue=f"Canonical tag points to external or mismatched domain ('{c_href}'), relinquishing indexation authority",
                            selector="CSS: link[rel='canonical']"
                        )
                    )
                elif parsed_c.path.rstrip("/") != parsed_p.path.rstrip("/"):
                    score -= 1
                    action_items.append(
                        ActionItem(
                            url=page.url,
                            issue=f"Canonical path mismatch: page path '{parsed_p.path}' canonicalizes to different path '{parsed_c.path}'",
                            selector="CSS: link[rel='canonical']"
                        )
                    )

            # 2. Meta robots check for accidental noindex
            robots_meta = soup.find("meta", attrs={"name": re.compile(r'^robots$', re.I)})
            if robots_meta:
                content = (robots_meta.get("content") or "").lower()
                if "noindex" in content:
                    path = urllib.parse.urlparse(page.url).path.lower()
                    if path in ["", "/", "/home", "/about", "/services", "/pricing", "/contact"]:
                        score -= 4
                        action_items.append(
                            ActionItem(
                                url=page.url,
                                issue="Critical landing/service page contains '<meta name=\"robots\" content=\"noindex\">', blocking search engine indexation",
                                selector="CSS: head > meta[name='robots']"
                            )
                        )

        score = max(0, min(10, score))
        return SectionResult(title=title, score=score, action_items=action_items)

    def evaluate_local_seo_citations(self) -> SectionResult:
        """Section 6: Local SEO Citations & NAP Consistency."""
        title = "Local SEO Citations & NAP Consistency"
        action_items: List[ActionItem] = []
        score = 10

        combined_text = " ".join([p.soup.get_text() for p in self.pages])

        # 1. Phone number presence in footer or header
        has_phone = bool(self.PHONE_REGEX.search(combined_text))
        if not has_phone:
            score -= 3
            action_items.append(
                ActionItem(
                    url=self.base_url,
                    issue="Website lacks a clearly visible telephone number in the header or footer, weakening Google Local Trust signals",
                    selector="XPath: //footer"
                )
            )

        # 2. Physical street address presence
        has_address = bool(self.ADDRESS_KEYWORD_REGEX.search(combined_text))
        if not has_address:
            score -= 3
            action_items.append(
                ActionItem(
                    url=self.base_url,
                    issue="Missing physical street address and city/state text in the site footer; essential for Google Local Pack geo-relevance",
                    selector="XPath: //footer"
                )
            )

        # 3. Embedded Google Map or GBP link
        all_iframes = [iframe.get("src", "").lower() for p in self.pages for iframe in p.soup.find_all("iframe")]
        all_links = [a.get("href", "").lower() for p in self.pages for a in p.soup.find_all("a", href=True)]

        has_google_map = any("google.com/maps" in s or "maps.google.com" in s for s in all_iframes)
        has_gbp_link = any("google.com/maps" in l or "maps.google.com" in l or "business.google.com" in l for l in all_links)

        if not has_google_map and not has_gbp_link:
            score -= 2
            action_items.append(
                ActionItem(
                    url=self.base_url,
                    issue="Contact or location section lacks an embedded Google Map or direct link to verified Google Business Profile",
                    selector="CSS: footer, .contact-container"
                )
            )

        score = max(0, min(10, score))
        return SectionResult(title=title, score=score, action_items=action_items)

    def run_full_audit(self) -> List[SectionResult]:
        """Run all Technical and Local SEO audit modules."""
        return [
            self.evaluate_metadata(),
            self.evaluate_heading_hierarchy(),
            self.evaluate_structured_data(),
            self.evaluate_broken_links_and_redirects(),
            self.evaluate_indexing_and_canonicalization(),
            self.evaluate_local_seo_citations(),
        ]


def crawl_website(base_url: str, sub_paths: Optional[List[str]] = None) -> Tuple[List[CrawledPage], Dict[str, int]]:
    """Crawl the website, record redirect histories, and check a sample of internal links."""
    if not base_url.startswith("http://") and not base_url.startswith("https://"):
        base_url = "https://" + base_url

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36 SEOHealthAuditor/1.0"
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

    print(f"[*] Crawling target site for Technical & Local SEO: {base_url}")
    for u in urls_to_visit:
        try:
            print(f"    Fetching {u} ...")
            resp = session.get(u, timeout=12, allow_redirects=True)
            chain = [(r.status_code, r.url) for r in resp.history]
            crawled_pages.append(
                CrawledPage(
                    url=u,
                    html=resp.text,
                    status_code=resp.status_code,
                    redirect_chain=chain,
                )
            )
        except Exception as e:
            print(f"    [!] Error crawling {u}: {e}")

    # Auto-discover SEO sub-pages if only 1 page crawled
    if len(crawled_pages) == 1 and not sub_paths:
        home_soup = crawled_pages[0].soup
        discovered_paths = []
        target_keywords = ["about", "contact", "services", "locations", "pricing", "faq", "blog"]
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
                print(f"    Auto-discovered SEO sub-page: {link} ...")
                resp = session.get(link, timeout=10, allow_redirects=True)
                chain = [(r.status_code, r.url) for r in resp.history]
                crawled_pages.append(
                    CrawledPage(
                        url=link,
                        html=resp.text,
                        status_code=resp.status_code,
                        redirect_chain=chain,
                    )
                )
            except Exception as e:
                print(f"    [!] Error fetching discovered page {link}: {e}")

    # Sample internal links to check for 404s
    tested_links: Dict[str, int] = {}
    sampled_links = set()
    for page in crawled_pages:
        for a in page.soup.find_all("a", href=True):
            h = a["href"].strip()
            if not h.startswith("#") and not h.startswith("mailto:") and not h.startswith("tel:"):
                full = urllib.parse.urljoin(base_url, h)
                parsed = urllib.parse.urlparse(full)
                if parsed.netloc == urllib.parse.urlparse(base_url).netloc and full not in [p.url for p in crawled_pages]:
                    sampled_links.add(full)
            if len(sampled_links) >= 5:
                break

    for slink in list(sampled_links)[:4]:
        try:
            head_resp = session.head(slink, timeout=6, allow_redirects=True)
            tested_links[slink] = head_resp.status_code
        except Exception:
            pass

    return crawled_pages, tested_links


def format_report(base_url: str, section_results: List[SectionResult]) -> str:
    """Format audit findings into standardized Technical & Local SEO report."""
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
        "TECHNICAL & LOCAL SEO HEALTH AUDIT REPORT",
        f"Target Site: {base_url}",
        "Generated By: Agency AI SEO & Local Search Auditor Agent",
        "Benchmark: Google Search Essentials & Local Pack Ranking Best Practices",
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
            lines.append(f"{base_url} | Meets all technical and local SEO standards for this capability.")
        lines.append("")

    lines.append("============================================================")
    lines.append("OVERALL SUMMARY & RECOMMENDATIONS")
    lines.append(f"Overall SEO Health Score: {total_score}/10")
    lines.append(f"Search Indexing & Ranking Risk Level: {risk_level}")
    lines.append("Primary SEO Bottlenecks:")

    # Identify top bottlenecks from lowest scoring sections
    sorted_sections = sorted(section_results, key=lambda s: s.score)
    bottleneck_idx = 1
    for s in sorted_sections[:2]:
        if s.action_items:
            lines.append(f"{bottleneck_idx}. [{s.title}] {s.action_items[0].issue}")
            bottleneck_idx += 1

    if bottleneck_idx == 1:
        lines.append("1. None identified; website meets Google technical standards.")

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
        lines.append("1. Maintain current on-page SEO metadata and Schema.org markup.")

    lines.append("============================================================")
    lines.append("END OF REPORT")
    lines.append("============================================================")

    return "\n".join(lines)


def run_audit(target_url: str, sub_paths: Optional[List[str]] = None, output_file: str = "seo-health-report.txt") -> str:
    """Main SEO audit execution pipeline."""
    crawled_pages, tested_links = crawl_website(target_url, sub_paths)
    if not crawled_pages:
        raise RuntimeError(f"Unable to crawl target URL: {target_url}")

    evaluator = SEOTechnicalLocalEvaluator(base_url=target_url, pages=crawled_pages, tested_links=tested_links)
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
        print("Technical & Local SEO Health Auditor Agent")
        print("------------------------------------------")
        target = input("Enter target website base URL (e.g., https://example.com): ").strip()
        if target:
            subs_input = input("Enter optional comma-separated sub-paths: ").strip()
            subs = [s.strip() for s in subs_input.split(",") if s.strip()] if subs_input else None
            report = run_audit(target, subs)
            print("\n" + report)
        else:
            print("No URL provided. Exiting.")
