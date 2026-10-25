"""
CRO & User Flow Auditor
=======================
Automated crawling and evaluation engine for Conversion Rate Optimization (CRO),
User Flow efficiency, and conversion friction analysis.

Evaluates websites across:
1. The 5-Second Test & Value Proposition Clarity
2. Call-to-Action (CTA) Friction & Visual Hierarchy
3. Form Optimization & Funnel Drop-off
4. Trust Elements, Social Proof & Risk Reversal
5. User Flow Continuity & Funnel Navigation
6. Mobile Conversion & Touch Ergonomics

Generates a standardized 'cro-userflow-report.txt' audit report.
"""

import sys
import os
import re
import urllib.parse
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
import requests
from bs4 import BeautifulSoup, Tag


@dataclass
class ActionItem:
    url: str
    issue: str
    selector: str

    def to_line(self) -> str:
        return f"{self.url} | {self.issue} at {self.selector}"


@dataclass
class SectionResult:
    title: str
    score: int
    action_items: List[ActionItem] = field(default_factory=list)


def generate_css_selector(tag: Tag) -> str:
    """Generate a readable, accurate CSS selector for an HTML element."""
    if not tag or not hasattr(tag, 'name'):
        return "body"
    
    # If element has a valid unique ID
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
        # Count preceding siblings of the same name
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


class CROEvaluator:
    """Evaluates crawled pages for CRO & User Flow issues."""

    VAGUE_HEADLINE_PATTERNS = [
        r'\bwelcome\b',
        r'\btransforming\b',
        r'\bunleash\b',
        r'\bempowering\b',
        r'\brevolutionizing\b',
        r'\binnovation\b',
        r'\bthe future of\b',
        r'\bnext-gen\b',
        r'\bparadigm\b',
        r'\bsynergy\b',
        r'\bexcellence\b',
        r'\bleading provider\b',
    ]

    GENERIC_CTA_WORDS = [
        "submit",
        "click here",
        "learn more",
        "read more",
        "view more",
        "go",
        "send",
        "continue",
        "download",
        "button",
    ]

    BENEFIT_CTA_WORDS = [
        "get",
        "start",
        "claim",
        "try",
        "book",
        "create",
        "join",
        "unlock",
        "save",
        "explore",
        "schedule",
        "find",
        "calculate",
    ]

    TRUST_KEYWORDS = [
        "review",
        "rating",
        "testimonial",
        "case study",
        "clients",
        "trusted by",
        "guarantee",
        "money-back",
        "cancel anytime",
        "no credit card",
        "soc 2",
        "iso",
        "hipaa",
        "pci",
        "ssl",
        "secure",
        "certified",
        "g2",
        "trustpilot",
        "capterra",
    ]

    def __init__(self, base_url: str, pages_data: Dict[str, str]):
        self.base_url = base_url
        self.pages_data = pages_data  # {url: html_content}
        self.parsed_pages = {
            url: BeautifulSoup(html, "html.parser")
            for url, html in pages_data.items()
        }

    def evaluate_5_second_test(self) -> SectionResult:
        """Point 1: The 5-Second Test & Value Proposition Clarity."""
        title = "The 5-Second Test & Value Proposition Clarity"
        action_items: List[ActionItem] = []
        score = 10

        for url, soup in self.parsed_pages.items():
            # Check main H1
            h1s = soup.find_all("h1")
            if not h1s:
                score -= 3
                action_items.append(
                    ActionItem(
                        url=url,
                        issue="Page lacks a primary <h1> hero headline above the fold; visitors cannot instantly identify core offering",
                        selector="XPath: /html/body"
                    )
                )
            else:
                for h1 in h1s:
                    h1_text = h1.get_text(strip=True).lower()
                    if len(h1_text) < 10:
                        score -= 1
                        action_items.append(
                            ActionItem(
                                url=url,
                                issue=f"Hero headline '{h1.get_text(strip=True)}' is too terse (<10 chars) to convey what the product or service does",
                                selector=f"CSS: {generate_css_selector(h1)}"
                            )
                        )
                    # Check for empty buzzwords
                    for pat in self.VAGUE_HEADLINE_PATTERNS:
                        if re.search(pat, h1_text):
                            score -= 1
                            action_items.append(
                                ActionItem(
                                    url=url,
                                    issue=f"Hero headline uses vague corporate phrasing ('{h1.get_text(strip=True)}') without clarifying who it serves or specific problem solved",
                                    selector=f"XPath: {generate_xpath(h1)}"
                                )
                            )
                            break

            # Check for hero subhead or paragraph
            hero = soup.find(lambda tag: tag.name in ['section', 'header', 'div'] and any(
                k in (tag.get('class') or []) or k in (tag.get('id') or '')
                for k in ['hero', 'banner', 'intro', 'header-content']
            ))
            if hero:
                p_tags = hero.find_all(['p', 'h2', 'h3'])
                if not p_tags or all(len(p.get_text(strip=True)) < 15 for p in p_tags):
                    score -= 2
                    action_items.append(
                        ActionItem(
                            url=url,
                            issue="Hero section lacks a descriptive supporting subhead explaining target audience and core differentiation",
                            selector=f"CSS: {generate_css_selector(hero)}"
                        )
                    )

            # Check for excessive visual height before value statement
            large_banners = soup.find_all(lambda tag: tag.name in ['div', 'section'] and any(
                'full-height' in c or '100vh' in c or 'h-screen' in c for c in (tag.get('class') or [])
            ))
            for b in large_banners[:1]:
                if not b.find(['h1', 'p']):
                    score -= 2
                    action_items.append(
                        ActionItem(
                            url=url,
                            issue="Full-screen viewport banner pushes core value proposition and primary action below the 800px fold",
                            selector=f"CSS: {generate_css_selector(b)}"
                        )
                    )

        score = max(0, min(10, score))
        return SectionResult(title=title, score=score, action_items=action_items)

    def evaluate_cta_friction(self) -> SectionResult:
        """Point 2: Call-to-Action (CTA) Friction & Visual Hierarchy."""
        title = "Call-to-Action (CTA) Friction & Visual Hierarchy"
        action_items: List[ActionItem] = []
        score = 10

        for url, soup in self.parsed_pages.items():
            # Find all clickable button-like elements
            buttons = soup.find_all(["button", "input"]) + soup.find_all(
                "a",
                class_=lambda c: c and any(x in str(c).lower() for x in ["btn", "button", "cta"])
            )

            primary_ctas = []
            generic_ctas = []

            for btn in buttons:
                if btn.name == "input" and btn.get("type") not in ["submit", "button"]:
                    continue

                text = btn.get_text(strip=True) if btn.name != "input" else (btn.get("value") or "")
                text_lower = text.lower().strip()

                if not text_lower:
                    continue

                # Check if it has primary styling
                classes = " ".join(btn.get("class", [])) if isinstance(btn.get("class"), list) else ""
                if any(k in classes.lower() for k in ["primary", "btn-main", "cta-primary", "action"]):
                    primary_ctas.append((btn, text))

                # Check for passive/generic wording
                if text_lower in self.GENERIC_CTA_WORDS:
                    generic_ctas.append((btn, text))

            # Flag lack of buttons on key pages
            if not buttons:
                score -= 4
                action_items.append(
                    ActionItem(
                        url=url,
                        issue="Page has zero visible call-to-action buttons or anchor CTAs; visitors hit a conversion dead-end",
                        selector="XPath: /html/body"
                    )
                )

            # Flag competing primary CTAs in close proximity
            if len(primary_ctas) > 2:
                first_container = primary_ctas[0][0].parent
                same_parent_count = sum(1 for b, _ in primary_ctas if b.parent == first_container)
                if same_parent_count >= 2:
                    score -= 2
                    action_items.append(
                        ActionItem(
                            url=url,
                            issue=f"Multiple conflicting primary CTAs ({', '.join([t for _, t in primary_ctas[:3]])}) placed side-by-side causing choice paralysis",
                            selector=f"CSS: {generate_css_selector(first_container)}"
                        )
                    )

            # Flag generic CTA copy
            for btn, text in generic_ctas[:3]:
                score -= 1
                action_items.append(
                    ActionItem(
                        url=url,
                        issue=f"CTA button uses passive, low-converting copy '{text}'. Replace with benefit-driven action phrasing (e.g., 'Get Instant Access', 'Start Free Trial')",
                        selector=f"XPath: {generate_xpath(btn)}"
                    )
                )

        score = max(0, min(10, score))
        return SectionResult(title=title, score=score, action_items=action_items)

    def evaluate_form_optimization(self) -> SectionResult:
        """Point 3: Form Optimization & Funnel Drop-off."""
        title = "Form Optimization & Funnel Drop-off"
        action_items: List[ActionItem] = []
        score = 10
        forms_found = False

        for url, soup in self.parsed_pages.items():
            forms = soup.find_all("form")
            if not forms:
                continue

            forms_found = True
            for form in forms:
                inputs = form.find_all(["input", "select", "textarea"])
                # Exclude hidden or csrf inputs
                visible_inputs = [
                    i for i in inputs
                    if i.get("type") not in ["hidden", "submit", "reset", "button"]
                ]

                # Check 1: Excessive field count (> 5 fields on standard form)
                if len(visible_inputs) > 5:
                    score -= 2
                    action_items.append(
                        ActionItem(
                            url=url,
                            issue=f"Form contains {len(visible_inputs)} input fields without multi-step chunking; excessive field count drives high conversion drop-off",
                            selector=f"XPath: {generate_xpath(form)}"
                        )
                    )

                for inp in visible_inputs:
                    inp_name = (inp.get("name") or inp.get("id") or "").lower()
                    inp_type = (inp.get("type") or "text").lower()

                    # Check 2: Missing autocomplete attribute
                    if inp.name == "input" and not inp.get("autocomplete"):
                        common_auto_fields = ["email", "name", "first", "last", "phone", "tel", "zip", "postal", "address", "city"]
                        if any(k in inp_name for k in common_auto_fields):
                            score -= 1
                            action_items.append(
                                ActionItem(
                                    url=url,
                                    issue=f"Input field '{inp.get('name') or inp.get('id')}' is missing HTML5 'autocomplete' attribute, preventing frictionless mobile autofill",
                                    selector=f"CSS: {generate_css_selector(inp)}"
                                )
                            )

                    # Check 3: Semantic mobile keyboards
                    if "phone" in inp_name or "tel" in inp_name:
                        if inp_type not in ["tel", "number"]:
                            score -= 1
                            action_items.append(
                                ActionItem(
                                    url=url,
                                    issue=f"Phone field uses '{inp_type}' instead of 'type=\"tel\"', failing to trigger the numeric keypad on mobile devices",
                                    selector=f"CSS: {generate_css_selector(inp)}"
                                )
                            )
                    elif "email" in inp_name and inp_type != "email":
                        score -= 1
                        action_items.append(
                            ActionItem(
                                url=url,
                                issue=f"Email field uses '{inp_type}' instead of 'type=\"email\"', missing dedicated @ key on mobile keyboard layout",
                                selector=f"CSS: {generate_css_selector(inp)}"
                            )
                        )

                    # Check 4: Missing persistent <label> (placeholder only)
                    inp_id = inp.get("id")
                    has_label = False
                    if inp_id:
                        has_label = bool(soup.find("label", attrs={"for": inp_id}))
                    if not has_label:
                        # Check wrapping label or aria-label
                        if inp.parent and inp.parent.name == "label":
                            has_label = True
                        elif inp.get("aria-label") or inp.get("aria-labelledby"):
                            has_label = True

                    if not has_label and inp.get("placeholder"):
                        score -= 1
                        action_items.append(
                            ActionItem(
                                url=url,
                                issue=f"Input relies solely on disappearing placeholder text '{inp.get('placeholder')}' without a persistent <label> element",
                                selector=f"XPath: {generate_xpath(inp)}"
                            )
                        )

                # Check 5: Inline error validation containers
                validation_tags = form.find_all(
                    class_=lambda c: c and any(x in str(c).lower() for x in ["error", "invalid", "feedback", "validation"])
                )
                if not validation_tags and len(visible_inputs) > 3:
                    score -= 1
                    action_items.append(
                        ActionItem(
                            url=url,
                            issue="Form lacks dedicated inline real-time error containers; risk of frustrating post-submit full page error reloads",
                            selector=f"CSS: {generate_css_selector(form)}"
                        )
                    )

        if not forms_found:
            # If no forms were found across any crawled page, note it
            action_items.append(
                ActionItem(
                    url=self.base_url,
                    issue="No lead capture, sign-up, or contact forms detected across crawled pages; ensure conversion capture mechanism is accessible",
                    selector="XPath: /html/body"
                )
            )

        score = max(0, min(10, score))
        return SectionResult(title=title, score=score, action_items=action_items)

    def evaluate_trust_and_social_proof(self) -> SectionResult:
        """Point 4: Trust Elements, Social Proof & Risk Reversal."""
        title = "Trust Elements, Social Proof & Risk Reversal"
        action_items: List[ActionItem] = []
        score = 10

        combined_text = " ".join([soup.get_text().lower() for soup in self.parsed_pages.values()])
        all_imgs = [img for soup in self.parsed_pages.values() for img in soup.find_all("img")]

        # Check 1: Reviews or third-party proof (G2, Trustpilot, Google reviews)
        has_reviews = any(k in combined_text for k in ["review", "rating", "trustpilot", "g2", "capterra", "google review", "stars"])
        if not has_reviews:
            score -= 3
            action_items.append(
                ActionItem(
                    url=self.base_url,
                    issue="Absence of verified customer reviews, aggregate star ratings, or third-party review widgets (Trustpilot, G2, Google)",
                    selector="XPath: /html/body"
                )
            )

        # Check 2: Customer / client logos
        logo_imgs = [
            img for img in all_imgs
            if any(k in (img.get("alt") or "").lower() or k in " ".join(img.get("class", [])).lower()
                   for k in ["logo", "client", "partner", "customer", "trusted"])
        ]
        if not logo_imgs and not any(k in combined_text for k in ["trusted by", "our clients", "our partners"]):
            score -= 2
            action_items.append(
                ActionItem(
                    url=self.base_url,
                    issue="Missing customer or client logo bar ('Trusted by 1,000+ teams'); lacks immediate B2B social proof anchor",
                    selector="CSS: section.hero, header, main"
                )
            )

        # Check 3: Risk reversal policies (guarantees, free trial terms)
        has_guarantee = any(k in combined_text for k in [
            "guarantee", "money-back", "cancel anytime", "no credit card required", "free trial", "risk-free"
        ])
        if not has_guarantee:
            score -= 2
            action_items.append(
                ActionItem(
                    url=self.base_url,
                    issue="Conversion points lack explicit risk-reversal microcopy ('No credit card required', '30-day money-back guarantee', or 'Cancel anytime')",
                    selector="CSS: .pricing, .cta-section, form"
                )
            )

        # Check 4: Security badges near checkout or inputs
        has_security = any(k in combined_text for k in ["ssl", "soc 2", "soc2", "hipaa", "pci", "256-bit", "gdpr", "secure checkout"])
        if not has_security:
            score -= 2
            action_items.append(
                ActionItem(
                    url=self.base_url,
                    issue="Absence of security badges, encryption verification, or compliance trust seals near conversion submission zones",
                    selector="CSS: footer, form, #checkout"
                )
            )

        # Check 5: Testimonial details (photos + full name + role)
        testimonials = []
        for soup in self.parsed_pages.values():
            testimonials.extend(soup.find_all(
                lambda t: t.name in ['div', 'section', 'blockquote'] and any(
                    k in " ".join(t.get("class", [])).lower() for k in ["testimonial", "review-card", "quote"]
                )
            ))

        for t in testimonials[:2]:
            if not t.find("img"):
                score -= 1
                action_items.append(
                    ActionItem(
                        url=self.base_url,
                        issue="Testimonial block lacks customer headshot, verifiable company name, or professional title, reducing authenticity",
                        selector=f"XPath: {generate_xpath(t)}"
                    )
                )

        score = max(0, min(10, score))
        return SectionResult(title=title, score=score, action_items=action_items)

    def evaluate_user_flow_continuity(self) -> SectionResult:
        """Point 5: User Flow Continuity & Funnel Navigation."""
        title = "User Flow Continuity & Funnel Navigation"
        action_items: List[ActionItem] = []
        score = 10

        for url, soup in self.parsed_pages.items():
            path = urllib.parse.urlparse(url).path.lower()
            is_high_intent = any(k in path for k in ["checkout", "cart", "signup", "register", "demo", "contact", "pricing"])

            # Check for navigation leak on high intent conversion pages
            if is_high_intent:
                nav = soup.find(["nav", "header"])
                if nav:
                    links = nav.find_all("a")
                    if len(links) > 10:
                        score -= 2
                        action_items.append(
                            ActionItem(
                                url=url,
                                issue=f"High-intent conversion page displays full navigation bar with {len(links)} links, leaking qualified traffic away from the funnel",
                                selector=f"CSS: {generate_css_selector(nav)}"
                            )
                        )

            # Check for distracting external social media icons in hero or main conversion area
            main_content = soup.find(["main", "section"])
            if main_content:
                social_links = main_content.find_all(
                    "a",
                    href=lambda h: h and any(s in str(h).lower() for s in ["facebook.com", "instagram.com", "twitter.com", "x.com", "tiktok.com"])
                )
                if social_links:
                    score -= 1
                    action_items.append(
                        ActionItem(
                            url=url,
                            issue="External social media links placed inside primary content/conversion area, siphoning prospective leads off-site",
                            selector=f"XPath: {generate_xpath(social_links[0])}"
                        )
                    )

        score = max(0, min(10, score))
        return SectionResult(title=title, score=score, action_items=action_items)

    def evaluate_mobile_conversion(self) -> SectionResult:
        """Point 6: Mobile Conversion & Touch Ergonomics."""
        title = "Mobile Conversion & Touch Ergonomics"
        action_items: List[ActionItem] = []
        score = 10

        for url, soup in self.parsed_pages.items():
            # Check viewport meta tag
            viewport = soup.find("meta", attrs={"name": "viewport"})
            if not viewport or "width=device-width" not in (viewport.get("content") or "").lower():
                score -= 4
                action_items.append(
                    ActionItem(
                        url=url,
                        issue="Missing or invalid '<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">' tag, breaking mobile touch layouts",
                        selector="XPath: /html/head"
                    )
                )

            # Check for sticky bottom conversion element or fixed mobile bar
            fixed_elements = soup.find_all(
                class_=lambda c: c and any(x in str(c).lower() for x in ["sticky-bottom", "fixed-bottom", "bottom-bar", "mobile-sticky"])
            )
            if not fixed_elements:
                score -= 1
                action_items.append(
                    ActionItem(
                        url=url,
                        issue="Long-scrolling layout lacks a persistent sticky bottom CTA bar on mobile viewports",
                        selector="CSS: body"
                    )
                )

        score = max(0, min(10, score))
        return SectionResult(title=title, score=score, action_items=action_items)

    def run_full_audit(self) -> List[SectionResult]:
        """Execute all evaluation modules."""
        return [
            self.evaluate_5_second_test(),
            self.evaluate_cta_friction(),
            self.evaluate_form_optimization(),
            self.evaluate_trust_and_social_proof(),
            self.evaluate_user_flow_continuity(),
            self.evaluate_mobile_conversion(),
        ]


def crawl_website(base_url: str, sub_paths: Optional[List[str]] = None) -> Dict[str, str]:
    """Crawl the base URL and requested sub-pages."""
    if not base_url.startswith("http://") and not base_url.startswith("https://"):
        base_url = "https://" + base_url

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36 CROAuditor/1.0"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    crawled_pages: Dict[str, str] = {}
    urls_to_visit = [base_url]

    if sub_paths:
        for p in sub_paths:
            full = urllib.parse.urljoin(base_url, p.strip())
            if full not in urls_to_visit:
                urls_to_visit.append(full)

    session = requests.Session()
    session.headers.update(headers)

    print(f"[*] Crawling target site: {base_url}")
    for u in urls_to_visit:
        try:
            print(f"    Fetching {u} ...")
            resp = session.get(u, timeout=12, allow_redirects=True)
            if resp.status_code == 200:
                crawled_pages[u] = resp.text
            else:
                print(f"    [!] Received HTTP status {resp.status_code} for {u}")
        except Exception as e:
            print(f"    [!] Error crawling {u}: {e}")

    # If sub_paths were not specified, attempt to auto-discover common conversion pages from the home page
    if len(crawled_pages) == 1 and not sub_paths:
        home_soup = BeautifulSoup(list(crawled_pages.values())[0], "html.parser")
        discovered_paths = []
        target_keywords = ["pricing", "contact", "demo", "signup", "register", "about", "checkout", "trial"]
        for a in home_soup.find_all("a", href=True):
            href = a["href"].strip()
            if href.startswith("#") or href.startswith("mailto:") or href.startswith("tel:"):
                continue
            for kw in target_keywords:
                if kw in href.lower():
                    full_link = urllib.parse.urljoin(base_url, href)
                    parsed_link = urllib.parse.urlparse(full_link)
                    parsed_base = urllib.parse.urlparse(base_url)
                    if parsed_link.netloc == parsed_base.netloc and full_link not in crawled_pages and full_link not in discovered_paths:
                        discovered_paths.append(full_link)
                    break

        for link in discovered_paths[:4]:
            try:
                print(f"    Auto-discovered key page: {link} ...")
                resp = session.get(link, timeout=10, allow_redirects=True)
                if resp.status_code == 200:
                    crawled_pages[link] = resp.text
            except Exception as e:
                print(f"    [!] Error fetching discovered page {link}: {e}")

    return crawled_pages


def format_report(base_url: str, section_results: List[SectionResult]) -> str:
    """Format audit findings into the standardized CRO & User Flow report."""
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
        "CONVERSION RATE OPTIMIZATION (CRO) & USER FLOW AUDIT REPORT",
        f"Target Site: {base_url}",
        "Generated By: Agency AI CRO & User Flow Auditor Agent",
        "Benchmark: Industry CRO & Funnel Conversion Best Practices",
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
            lines.append(f"{base_url} | Meets all evaluation criteria for this capability.")
        lines.append("")

    lines.append("============================================================")
    lines.append("OVERALL SUMMARY & RECOMMENDATIONS")
    lines.append(f"Overall CRO & User Flow Score: {total_score}/10")
    lines.append(f"Conversion Friction Risk Level: {risk_level}")
    lines.append("Primary Funnel Drop-off Bottlenecks:")

    # Identify top bottlenecks from lowest scoring sections
    sorted_sections = sorted(section_results, key=lambda s: s.score)
    bottleneck_idx = 1
    for s in sorted_sections[:2]:
        if s.action_items:
            lines.append(f"{bottleneck_idx}. [{s.title}] {s.action_items[0].issue}")
            bottleneck_idx += 1

    if bottleneck_idx == 1:
        lines.append("1. None identified; smooth user flow.")

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
        lines.append("1. Maintain current CRO high-conversion design patterns.")

    lines.append("============================================================")
    lines.append("END OF REPORT")
    lines.append("============================================================")

    return "\n".join(lines)


def run_audit(target_url: str, sub_paths: Optional[List[str]] = None, output_file: str = "cro-userflow-report.txt") -> str:
    """Main audit execution pipeline."""
    crawled_data = crawl_website(target_url, sub_paths)
    if not crawled_data:
        raise RuntimeError(f"Unable to crawl target URL: {target_url}")

    evaluator = CROEvaluator(base_url=target_url, pages_data=crawled_data)
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
        print("CRO & User Flow Auditor Agent")
        print("-----------------------------")
        target = input("Enter target website base URL (e.g., https://example.com): ").strip()
        if target:
            subs_input = input("Enter optional comma-separated sub-paths (or press Enter to auto-discover): ").strip()
            subs = [s.strip() for s in subs_input.split(",") if s.strip()] if subs_input else None
            report = run_audit(target, subs)
            print("\n" + report)
        else:
            print("No URL provided. Exiting.")
