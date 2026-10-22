"""
AI Crawlability & Readiness Auditor
===================================
Automated crawling and evaluation engine for AI readiness, LLM indexing,
and conversational agent crawlability.

Evaluates websites across:
1. Technical Crawlability (robots.txt for GPTBot, ClaudeBot, PerplexityBot, Google-Extended)
2. Semantic HTML (HTML5 document structure & semantic markers)
3. Accessibility Tree (DOM visibility, element labels, image descriptions for headless agents)
4. Content Structure for RAG Systems (heading relevance, chunking hierarchy, direct summaries)
5. Structured Data & Schema Markup (JSON-LD Organization, FAQPage, Article, Product schema)
6. Machine-Friendly Formats (/llms.txt, /llms-full.txt, markdown documentation maps)

Generates a standardized 'ai-crawlability-report.txt' audit report.
"""

import sys
import os
import re
import urllib.parse
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Tuple
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


class AICrawlabilityEvaluator:
    """Evaluates website assets for AI crawlability, indexing, and RAG comprehension."""

    AI_USER_AGENTS = ["GPTBot", "ClaudeBot", "PerplexityBot", "Google-Extended", "CCBot", "cohere-ai"]
    VAGUE_HEADINGS = [
        "things", "stuff we do", "services", "our work", "solutions",
        "more", "features", "what we do", "overview", "details"
    ]

    def __init__(self, base_url: str, pages: List[CrawledPage], robots_txt: Optional[str], llms_txt_status: int, llms_txt_content: str):
        self.base_url = base_url
        self.pages = pages
        self.robots_txt = robots_txt or ""
        self.llms_txt_status = llms_txt_status
        self.llms_txt_content = llms_txt_content

    def evaluate_technical_crawlability(self) -> SectionResult:
        """Section 1: Technical Crawlability (robots.txt & AI bot access)."""
        title = "Technical Crawlability"
        action_items: List[ActionItem] = []
        score = 10
        robots_url = urllib.parse.urljoin(self.base_url, "/robots.txt")

        if not self.robots_txt:
            score -= 3
            action_items.append(
                ActionItem(
                    url=robots_url,
                    issue="No 'robots.txt' file detected (404 or empty response); crawlers lack clear machine indexing rules",
                    selector=""
                )
            )
        else:
            lines = self.robots_txt.splitlines()
            current_agents: List[str] = []
            blocked_agents: Set[str] = set()
            wildcard_blocked = False

            for line in lines:
                line_str = line.strip()
                if not line_str or line_str.startswith("#"):
                    continue

                if ":" in line_str:
                    key, val = line_str.split(":", 1)
                    key = key.strip().lower()
                    val = val.strip()

                    if key == "user-agent":
                        current_agents = [val]
                    elif key == "disallow":
                        if val in ["/", "/*"]:
                            for agent in current_agents:
                                if agent == "*":
                                    wildcard_blocked = True
                                else:
                                    for ai_bot in self.AI_USER_AGENTS:
                                        if ai_bot.lower() in agent.lower():
                                            blocked_agents.add(ai_bot)

            if wildcard_blocked:
                score -= 5
                action_items.append(
                    ActionItem(
                        url=robots_url,
                        issue="Wildcard 'User-agent: * Disallow: /' directive explicitly blocks all automated crawlers and AI search agents",
                        selector=""
                    )
                )

            for bot in blocked_agents:
                score -= 2
                action_items.append(
                    ActionItem(
                        url=robots_url,
                        issue=f"Explicitly blocks '{bot}' which prevents conversational search discovery and RAG indexing",
                        selector=""
                    )
                )

            # Check for Sitemap directive
            if not any(re.match(r'^sitemap\s*:', l, re.IGNORECASE) for l in lines):
                score -= 1
                action_items.append(
                    ActionItem(
                        url=robots_url,
                        issue="Missing 'Sitemap:' directive in robots.txt to assist LLM crawler path discovery",
                        selector=""
                    )
                )

        score = max(0, min(10, score))
        return SectionResult(title=title, score=score, action_items=action_items)

    def evaluate_semantic_html(self) -> SectionResult:
        """Section 2: Semantic HTML (Document architecture & layout tags)."""
        title = "Semantic HTML"
        action_items: List[ActionItem] = []
        score = 10

        for page in self.pages:
            soup = page.soup

            # Check for major landmarks
            has_main = bool(soup.find("main"))
            has_header = bool(soup.find("header"))
            has_footer = bool(soup.find("footer"))
            has_nav = bool(soup.find("nav"))
            has_article = bool(soup.find("article"))

            if not has_main:
                score -= 2
                action_items.append(
                    ActionItem(
                        url=page.url,
                        issue="Page lacks semantic <main> container; AI crawlers cannot cleanly isolate core content from boilerplates",
                        selector="XPath: /html/body"
                    )
                )

            if not has_header or not has_footer:
                score -= 1
                action_items.append(
                    ActionItem(
                        url=page.url,
                        issue="Missing semantic <header> or <footer> layout landmark tags; layout relies on generic unlabelled <div> tags",
                        selector="XPath: /html/body"
                    )
                )

            # Check for article or section wrapping content
            body = soup.find("body")
            if body:
                direct_divs = [c for c in body.children if getattr(c, 'name', None) == 'div']
                if len(direct_divs) > 5 and not has_article and not soup.find("section"):
                    score -= 2
                    action_items.append(
                        ActionItem(
                            url=page.url,
                            issue="Excessive unlabelled <div> nesting without <article> or <section> structural boundaries",
                            selector=f"CSS: {generate_css_selector(direct_divs[0])}"
                        )
                    )

        score = max(0, min(10, score))
        return SectionResult(title=title, score=score, action_items=action_items)

    def evaluate_accessibility_tree(self) -> SectionResult:
        """Section 3: Accessibility Tree (Interactive roles, labels, image descriptions)."""
        title = "Accessibility Tree"
        action_items: List[ActionItem] = []
        score = 10

        for page in self.pages:
            soup = page.soup

            # Missing image alt attributes
            images = soup.find_all("img")
            missing_alts = [img for img in images if img.get("alt") is None or img.get("alt").strip() == ""]
            if missing_alts:
                score -= min(4, len(missing_alts))
                for img in missing_alts[:3]:
                    src = img.get("src") or "image"
                    clean_name = src.split("/")[-1].split("?")[0]
                    action_items.append(
                        ActionItem(
                            url=page.url,
                            issue=f"Image ('{clean_name}') missing descriptive 'alt' attribute, leaving headless AI visual agents blind to visual content",
                            selector=f"XPath: {generate_xpath(img)}"
                        )
                    )

            # Interactive buttons without labels or accessible names
            buttons = soup.find_all("button")
            for btn in buttons:
                text = btn.get_text(strip=True)
                aria = btn.get("aria-label") or btn.get("aria-labelledby")
                if not text and not aria:
                    score -= 1
                    action_items.append(
                        ActionItem(
                            url=page.url,
                            issue="Interactive button lacks text content or accessible 'aria-label', invisible to autonomous browser agents",
                            selector=f"CSS: {generate_css_selector(btn)}"
                        )
                    )
                    break

        score = max(0, min(10, score))
        return SectionResult(title=title, score=score, action_items=action_items)

    def evaluate_content_structure_rag(self) -> SectionResult:
        """Section 4: Content Structure for RAG Systems (Headings & chunk summaries)."""
        title = "Content Structure for RAG Systems"
        action_items: List[ActionItem] = []
        score = 10

        for page in self.pages:
            soup = page.soup

            # Check headings for vague labels
            headings = soup.find_all(["h1", "h2", "h3"])
            if not headings:
                score -= 4
                action_items.append(
                    ActionItem(
                        url=page.url,
                        issue="Page has no structural <h1>, <h2>, or <h3> headings, making vector embedding and RAG chunking ineffective",
                        selector="XPath: /html/body"
                    )
                )
            else:
                for h in headings:
                    htext = h.get_text(strip=True).lower()
                    if htext in self.VAGUE_HEADINGS or len(htext) < 4:
                        score -= 1
                        action_items.append(
                            ActionItem(
                                url=page.url,
                                issue=f"Heading '{h.get_text(strip=True)}' is too vague for semantic vector chunking. Add explicit entity context (e.g., 'Our Enterprise Cloud Services') and a 50-word direct summary block below it",
                                selector=f"XPath: {generate_xpath(h)}"
                            )
                        )
                        break

            # Check for direct summary blocks under major H2s
            h2s = soup.find_all("h2")
            for h2 in h2s[:3]:
                next_p = h2.find_next_sibling("p")
                if not next_p or len(next_p.get_text(strip=True).split()) < 20:
                    score -= 1
                    action_items.append(
                        ActionItem(
                            url=page.url,
                            issue=f"Section heading '{h2.get_text(strip=True)}' lacks an introductory summary paragraph (40-60 words) immediately below it, degrading retrieval chunk fidelity",
                            selector=f"CSS: {generate_css_selector(h2)}"
                        )
                    )
                    break

        score = max(0, min(10, score))
        return SectionResult(title=title, score=score, action_items=action_items)

    def evaluate_structured_data_schema(self) -> SectionResult:
        """Section 5: Structured Data & Schema Markup (JSON-LD context)."""
        title = "Structured Data & Schema Markup"
        action_items: List[ActionItem] = []
        score = 10

        schema_found = False
        for page in self.pages:
            soup = page.soup
            json_ld_scripts = soup.find_all("script", attrs={"type": "application/ld+json"})

            if json_ld_scripts:
                schema_found = True
            else:
                score -= 3
                action_items.append(
                    ActionItem(
                        url=page.url,
                        issue="Page lacks JSON-LD structured schema markup (missing 'application/ld+json' scripts); machines must rely on fragile text heuristics",
                        selector="CSS: head"
                    )
                )

            # Check for visual FAQs lacking FAQPage schema
            faq_headings = [
                h for h in soup.find_all(["h2", "h3", "h4"])
                if any(k in h.get_text().lower() for k in ["faq", "frequently asked", "q&a"])
            ]
            if faq_headings:
                has_faq_schema = False
                for s in json_ld_scripts:
                    if "faqpage" in s.get_text().lower():
                        has_faq_schema = True
                        break
                if not has_faq_schema:
                    score -= 2
                    action_items.append(
                        ActionItem(
                            url=page.url,
                            issue="Page features visual FAQs but lacks corresponding JSON-LD 'FAQPage' schema injection for rich AI answer synthesis",
                            selector=f"CSS: {generate_css_selector(faq_headings[0])}"
                        )
                    )

        if not schema_found:
            score = min(score, 3)

        score = max(0, min(10, score))
        return SectionResult(title=title, score=score, action_items=action_items)

    def evaluate_machine_friendly_formats(self) -> SectionResult:
        """Section 6: Machine-Friendly Formats (/llms.txt & alternate representations)."""
        title = "Machine-Friendly Formats"
        action_items: List[ActionItem] = []
        score = 10
        llms_url = urllib.parse.urljoin(self.base_url, "/llms.txt")

        if self.llms_txt_status != 200:
            score = 0
            action_items.append(
                ActionItem(
                    url=llms_url,
                    issue=f"File not found ({self.llms_txt_status} error). Add an llms.txt map to the root directory for LLM discoverability and context routing",
                    selector=""
                )
            )
        else:
            if len(self.llms_txt_content.strip()) < 30:
                score = 4
                action_items.append(
                    ActionItem(
                        url=llms_url,
                        issue="File '/llms.txt' is present but virtually empty (<30 characters); populate with clean markdown site overview and key URLs",
                        selector=""
                    )
                )

        score = max(0, min(10, score))
        return SectionResult(title=title, score=score, action_items=action_items)

    def run_full_audit(self) -> List[SectionResult]:
        """Run all AI crawlability audit modules."""
        return [
            self.evaluate_technical_crawlability(),
            self.evaluate_semantic_html(),
            self.evaluate_accessibility_tree(),
            self.evaluate_content_structure_rag(),
            self.evaluate_structured_data_schema(),
            self.evaluate_machine_friendly_formats(),
        ]


def crawl_website(base_url: str, sub_paths: Optional[List[str]] = None) -> Tuple[List[CrawledPage], str, int, str]:
    """Crawl website, robots.txt, and llms.txt."""
    if not base_url.startswith("http://") and not base_url.startswith("https://"):
        base_url = "https://" + base_url

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36 AICrawler/1.0"
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

    print(f"[*] Crawling target site for AI Crawlability: {base_url}")
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

    # Fetch robots.txt
    robots_txt = ""
    robots_url = urllib.parse.urljoin(base_url, "/robots.txt")
    try:
        print(f"    Checking {robots_url} ...")
        r_resp = session.get(robots_url, timeout=8)
        if r_resp.status_code == 200:
            robots_txt = r_resp.text
    except Exception as e:
        print(f"    [!] Error checking robots.txt: {e}")

    # Fetch llms.txt
    llms_txt_status = 404
    llms_txt_content = ""
    llms_url = urllib.parse.urljoin(base_url, "/llms.txt")
    try:
        print(f"    Checking {llms_url} ...")
        l_resp = session.get(llms_url, timeout=8)
        llms_txt_status = l_resp.status_code
        if l_resp.status_code == 200:
            llms_txt_content = l_resp.text
    except Exception as e:
        print(f"    [!] Error checking llms.txt: {e}")

    return crawled_pages, robots_txt, llms_txt_status, llms_txt_content


def format_report(base_url: str, section_results: List[SectionResult]) -> str:
    """Format audit findings into standardized AI Crawlability Report."""
    lines = [
        "============================================================",
        "AI CRAWLABILITY AUDIT REPORT",
        f"Target Site: {base_url}",
        "Generated By: Agency AI Auditor Agent",
        "============================================================",
        "",
    ]

    for section in section_results:
        lines.append(f"{section.title}: {section.score}/10")
        if section.action_items:
            for item in section.action_items:
                lines.append(item.to_line())
        else:
            lines.append(f"{base_url} | Meets all evaluation criteria for this capability.")
        lines.append("")

    lines.append("============================================================")
    lines.append("END OF REPORT")
    lines.append("============================================================")

    return "\n".join(lines)


def run_audit(target_url: str, sub_paths: Optional[List[str]] = None, output_file: str = "ai-crawlability-report.txt") -> str:
    """Main execution pipeline."""
    crawled_pages, robots_txt, llms_status, llms_content = crawl_website(target_url, sub_paths)
    if not crawled_pages:
        raise RuntimeError(f"Unable to crawl target URL: {target_url}")

    evaluator = AICrawlabilityEvaluator(
        base_url=target_url,
        pages=crawled_pages,
        robots_txt=robots_txt,
        llms_txt_status=llms_status,
        llms_txt_content=llms_content
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
        print("AI Crawlability & Readiness Auditor Agent")
        print("-----------------------------------------")
        target = input("Enter target website base URL (e.g., https://example.com): ").strip()
        if target:
            subs_input = input("Enter optional comma-separated sub-paths: ").strip()
            subs = [s.strip() for s in subs_input.split(",") if s.strip()] if subs_input else None
            report = run_audit(target, subs)
            print("\n" + report)
        else:
            print("No URL provided. Exiting.")
