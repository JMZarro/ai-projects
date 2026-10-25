"""
Core Web Vitals & Speed Performance Auditor
===========================================
Automated crawling and evaluation engine for Google Core Web Vitals (LCP, INP, CLS)
and Speed Performance (Asset Bloat, Modern Image Formats, Script Contention).

Evaluates websites across:
1. Core Web Vitals: Largest Contentful Paint (LCP) Optimization
2. Core Web Vitals: Interaction to Next Paint (INP) & Main-Thread Responsiveness
3. Core Web Vitals: Cumulative Layout Shift (CLS) & Visual Stability
4. Asset Bloat: Modern Image Formats & Media Optimization
5. Asset Bloat: JavaScript Execution, Bundling & Render-Blocking Scripts
6. Third-Party Script Contention & Tag Management

Generates a standardized 'performance-audit-report.txt' audit report.
"""

import sys
import os
import re
import time
import urllib.parse
from dataclasses import dataclass, field
from typing import List, Dict, Optional
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
    ttfb_ms: float
    headers: Dict[str, str]
    soup: BeautifulSoup = field(init=False)

    def __post_init__(self):
        self.soup = BeautifulSoup(self.html, "html.parser")


class PerformanceEvaluator:
    """Evaluates crawled pages for Core Web Vitals & Speed Performance."""

    KNOWN_TRACKERS = {
        "google-analytics.com": "Google Analytics",
        "googletagmanager.com": "Google Tag Manager",
        "facebook.net": "Meta / Facebook Pixel",
        "connect.facebook.net": "Meta / Facebook SDK",
        "hotjar.com": "Hotjar Session Recording",
        "clarity.ms": "Microsoft Clarity",
        "tiktok.com": "TikTok Pixel",
        "linkedin.com": "LinkedIn Insight Tag",
        "segment.com": "Segment Analytics",
        "segment.io": "Segment Analytics",
        "criteo.com": "Criteo Advertising",
        "pinterest.com": "Pinterest Tag",
        "mouseflow.com": "Mouseflow Replay",
        "fullstory.com": "FullStory Session Replay",
        "crazyegg.com": "CrazyEgg Heatmaps",
        "klaviyo.com": "Klaviyo Marketing",
    }

    KNOWN_CHAT_WIDGETS = {
        "intercom.io": "Intercom Chat",
        "intercomcdn.com": "Intercom Chat",
        "drift.com": "Drift Chat",
        "zendesk.com": "Zendesk Widget",
        "zopim.com": "Zendesk/Zopim",
        "hubspot.com": "HubSpot Conversations Widget",
        "tidio.co": "Tidio Live Chat",
        "crisp.chat": "Crisp Chat",
    }

    def __init__(self, base_url: str, pages: List[CrawledPage]):
        self.base_url = base_url
        self.pages = pages

    def evaluate_lcp(self) -> SectionResult:
        """Section 1: Core Web Vitals - Largest Contentful Paint (LCP) Optimization."""
        title = "Core Web Vitals: Largest Contentful Paint (LCP) Optimization"
        action_items: List[ActionItem] = []
        score = 10

        for page in self.pages:
            soup = page.soup

            # 1. Server TTFB latency check
            if page.ttfb_ms > 800:
                score -= 2
                action_items.append(
                    ActionItem(
                        url=page.url,
                        issue=f"Server Time to First Byte (TTFB) is slow ({page.ttfb_ms:.0f}ms, exceeds 800ms recommended threshold), directly inflating LCP wait time",
                        selector="Network: TTFB"
                    )
                )

            # 2. Compression header check
            enc = page.headers.get("content-encoding", "").lower()
            if "gzip" not in enc and "br" not in enc:
                score -= 1
                action_items.append(
                    ActionItem(
                        url=page.url,
                        issue="HTML response lacks modern compression headers (Brotli 'br' or Gzip 'gzip'), increasing initial payload transfer time",
                        selector="HTTP Header: Content-Encoding"
                    )
                )

            # 3. Detect Hero / LCP candidate image
            hero_container = soup.find(lambda t: t.name in ['section', 'header', 'div'] and any(
                k in " ".join(t.get('class', [])).lower() or k in (t.get('id') or '').lower()
                for k in ['hero', 'banner', 'masthead', 'intro']
            ))

            hero_imgs = []
            if hero_container:
                hero_imgs = hero_container.find_all("img")
            if not hero_imgs:
                # Fall back to first visible image in body
                all_body_imgs = soup.find_all("img")
                if all_body_imgs:
                    hero_imgs = [all_body_imgs[0]]

            preloaded_images = [
                link.get("href") for link in soup.find_all("link", attrs={"rel": "preload", "as": "image"})
            ]

            for img in hero_imgs[:2]:
                src = img.get("src") or img.get("data-src") or ""
                loading = (img.get("loading") or "").lower()
                fetchpriority = (img.get("fetchpriority") or "").lower()

                # Critical Anti-pattern: lazy-loading LCP candidate
                if loading == "lazy":
                    score -= 3
                    action_items.append(
                        ActionItem(
                            url=page.url,
                            issue="Above-the-fold hero image uses 'loading=\"lazy\"', delaying browser LCP asset discovery and rendering",
                            selector=f"CSS: {generate_css_selector(img)}"
                        )
                    )

                # Missing preload / fetchpriority
                if fetchpriority != "high":
                    score -= 1
                    action_items.append(
                        ActionItem(
                            url=page.url,
                            issue="Hero LCP candidate image lacks 'fetchpriority=\"high\"' attribute for prioritized browser request scheduling",
                            selector=f"XPath: {generate_xpath(img)}"
                        )
                    )

                if src and src not in preloaded_images:
                    score -= 1
                    action_items.append(
                        ActionItem(
                            url=page.url,
                            issue=f"Hero LCP image ('{src.split('/')[-1].split('?')[0]}') lacks '<link rel=\"preload\" as=\"image\">' in <head>",
                            selector="CSS: head"
                        )
                    )

            # 4. Render-blocking stylesheets in <head>
            stylesheets = soup.find_all("link", attrs={"rel": "stylesheet"})
            blocking_css = [s for s in stylesheets if not s.get("media") or s.get("media") == "all"]
            if len(blocking_css) > 3:
                score -= 2
                action_items.append(
                    ActionItem(
                        url=page.url,
                        issue=f"Found {len(blocking_css)} synchronous stylesheets in <head> blocking critical rendering path; inline critical CSS and defer non-critical styles",
                        selector=f"CSS: {generate_css_selector(blocking_css[0])}"
                    )
                )

            # 5. External fonts missing preconnect
            font_links = [
                l.get("href", "") for l in soup.find_all("link")
                if "fonts.googleapis.com" in l.get("href", "") or "use.typekit.net" in l.get("href", "")
            ]
            preconnects = [
                l.get("href", "") for l in soup.find_all("link", attrs={"rel": "preconnect"})
            ]
            if font_links and not any("fonts.gstatic.com" in p for p in preconnects):
                score -= 1
                action_items.append(
                    ActionItem(
                        url=page.url,
                        issue="External Google Fonts link used without '<link rel=\"preconnect\" href=\"https://fonts.gstatic.com\" crossorigin>', adding an extra connection roundtrip to LCP",
                        selector="CSS: head"
                    )
                )

        score = max(0, min(10, score))
        return SectionResult(title=title, score=score, action_items=action_items)

    def evaluate_inp(self) -> SectionResult:
        """Section 2: Core Web Vitals - Interaction to Next Paint (INP) & Main-Thread Responsiveness."""
        title = "Core Web Vitals: Interaction to Next Paint (INP) & Main-Thread Responsiveness"
        action_items: List[ActionItem] = []
        score = 10

        for page in self.pages:
            soup = page.soup

            scripts = soup.find_all("script")
            external_scripts = [s for s in scripts if s.get("src")]

            # 1. Check for synchronous render-blocking scripts in <head>
            head_tag = soup.find("head")
            head_scripts = head_tag.find_all("script") if head_tag else []
            sync_head_scripts = [
                s for s in head_scripts
                if s.get("src") and not s.get("defer") and not s.get("async") and s.get("type") != "application/ld+json"
            ]

            if sync_head_scripts:
                score -= 3
                for s in sync_head_scripts[:2]:
                    src_name = s.get("src", "").split("/")[-1].split("?")[0]
                    action_items.append(
                        ActionItem(
                            url=page.url,
                            issue=f"Synchronous script '{src_name}' in <head> lacks 'defer' or 'async', locking main thread parser and degrading INP responsiveness",
                            selector=f"CSS: {generate_css_selector(s)}"
                        )
                    )

            # 2. Check total external script count
            if len(external_scripts) > 15:
                score -= 2
                action_items.append(
                    ActionItem(
                        url=page.url,
                        issue=f"Page loads {len(external_scripts)} external JavaScript bundles; heavy script volume creates main thread contention and long tasks (>50ms)",
                        selector="XPath: /html/body"
                    )
                )

            # 3. Detect duplicate / competing frameworks (e.g. jQuery + React/Vue simultaneously)
            script_srcs = " ".join([s.get("src", "").lower() for s in external_scripts])
            frameworks_detected = []
            if "jquery" in script_srcs:
                frameworks_detected.append("jQuery")
            if "react" in script_srcs or "react-dom" in script_srcs:
                frameworks_detected.append("React")
            if "vue" in script_srcs:
                frameworks_detected.append("Vue")
            if "angular" in script_srcs:
                frameworks_detected.append("Angular")

            if len(frameworks_detected) > 1:
                score -= 2
                action_items.append(
                    ActionItem(
                        url=page.url,
                        issue=f"Multiple heavy JS libraries/frameworks loaded concurrently ({', '.join(frameworks_detected)}), inflating runtime memory and main thread execution time",
                        selector="CSS: script[src]"
                    )
                )

        score = max(0, min(10, score))
        return SectionResult(title=title, score=score, action_items=action_items)

    def evaluate_cls(self) -> SectionResult:
        """Section 3: Core Web Vitals - Cumulative Layout Shift (CLS) & Visual Stability."""
        title = "Core Web Vitals: Cumulative Layout Shift (CLS) & Visual Stability"
        action_items: List[ActionItem] = []
        score = 10

        for page in self.pages:
            soup = page.soup

            # 1. Images missing explicit width and height attributes
            images = soup.find_all("img")
            imgs_missing_dims = []
            for img in images:
                has_w = img.get("width")
                has_h = img.get("height")
                style = (img.get("style") or "").lower()
                has_aspect = "aspect-ratio" in style

                if (not has_w or not has_h) and not has_aspect:
                    imgs_missing_dims.append(img)

            if imgs_missing_dims:
                penalty = min(4, len(imgs_missing_dims))
                score -= penalty
                for img in imgs_missing_dims[:3]:
                    src = img.get("src") or img.get("data-src") or "image"
                    src_clean = src.split("/")[-1].split("?")[0]
                    action_items.append(
                        ActionItem(
                            url=page.url,
                            issue=f"Image '{src_clean}' lacks explicit 'width' and 'height' (or CSS 'aspect-ratio'), triggering visual layout reflow during loading",
                            selector=f"CSS: {generate_css_selector(img)}"
                        )
                    )

            # 2. Videos and IFrames missing dimensions
            embeds = soup.find_all(["video", "iframe"])
            for emb in embeds[:2]:
                if not emb.get("width") and not emb.get("height") and "aspect-ratio" not in (emb.get("style") or "").lower():
                    score -= 1
                    action_items.append(
                        ActionItem(
                            url=page.url,
                            issue=f"Embedded <{emb.name}> lacks defined dimensions or aspect-ratio placeholder, causing severe layout shifts when media renders",
                            selector=f"XPath: {generate_xpath(emb)}"
                        )
                    )

            # 3. Dynamic announcement / top notification bar without min-height
            top_bars = soup.find_all(
                lambda t: t.name in ['div', 'aside', 'section'] and any(
                    k in " ".join(t.get('class', [])).lower() or k in (t.get('id') or '').lower()
                    for k in ['announcement', 'promo-bar', 'top-banner', 'notice-bar', 'alert-bar']
                )
            )
            for bar in top_bars[:1]:
                style = (bar.get("style") or "").lower()
                if "min-height" not in style and "height" not in style:
                    score -= 1
                    action_items.append(
                        ActionItem(
                            url=page.url,
                            issue="Top promotional or announcement bar injected above content without reserved 'min-height', causing jarring layout shift on display",
                            selector=f"CSS: {generate_css_selector(bar)}"
                        )
                    )

            # 4. Check for font-display swap in inline styles or font links
            font_links = [l.get("href", "") for l in soup.find_all("link") if "fonts.googleapis.com" in l.get("href", "")]
            for flink in font_links:
                if "display=swap" not in flink:
                    score -= 1
                    action_items.append(
                        ActionItem(
                            url=page.url,
                            issue="Google Fonts link is missing 'display=swap' query parameter, causing Flash of Invisible Text (FOIT) and layout reflow",
                            selector="CSS: link[href*='fonts.googleapis.com']"
                        )
                    )

        score = max(0, min(10, score))
        return SectionResult(title=title, score=score, action_items=action_items)

    def evaluate_image_asset_bloat(self) -> SectionResult:
        """Section 4: Asset Bloat - Modern Image Formats & Media Optimization."""
        title = "Asset Bloat: Modern Image Formats & Media Optimization"
        action_items: List[ActionItem] = []
        score = 10

        for page in self.pages:
            soup = page.soup
            images = soup.find_all("img")

            legacy_images = []
            missing_srcset = []
            animated_gifs = []

            for img in images:
                src = (img.get("src") or img.get("data-src") or "").lower()
                clean_src = src.split("?")[0]

                # Check for legacy formats
                if clean_src.endswith((".png", ".jpg", ".jpeg")):
                    # Check if inside a <picture> with <source type="image/webp"> or <source type="image/avif">
                    is_in_picture = False
                    if img.parent and img.parent.name == "picture":
                        sources = img.parent.find_all("source")
                        types = [s.get("type", "").lower() for s in sources]
                        if any("webp" in t or "avif" in t for t in types):
                            is_in_picture = True

                    if not is_in_picture:
                        legacy_images.append((img, src))

                # Check for heavy GIFs
                if clean_src.endswith(".gif") and "spacer" not in clean_src and "pixel" not in clean_src:
                    animated_gifs.append((img, src))

                # Check for responsive srcset on larger content images
                if not img.get("srcset") and not img.get("sizes"):
                    cls = " ".join(img.get("class", [])).lower()
                    if any(k in cls for k in ["hero", "banner", "product", "featured", "cover", "gallery"]):
                        missing_srcset.append((img, src))

            # Score deductions and action items
            if legacy_images:
                score -= min(4, len(legacy_images))
                for img, src in legacy_images[:3]:
                    file_name = src.split("/")[-1].split("?")[0]
                    action_items.append(
                        ActionItem(
                            url=page.url,
                            issue=f"Image '{file_name}' delivered in legacy format. Convert to modern next-gen formats (.webp or .avif) for 30-70% bandwidth savings",
                            selector=f"CSS: {generate_css_selector(img)}"
                        )
                    )

            if animated_gifs:
                score -= 2
                for img, src in animated_gifs[:2]:
                    file_name = src.split("/")[-1].split("?")[0]
                    action_items.append(
                        ActionItem(
                            url=page.url,
                            issue=f"Heavy animated GIF ('{file_name}') used. Replace with lightweight HTML5 loopable video (<video autoplay loop muted playsinline>) or animated WebP",
                            selector=f"XPath: {generate_xpath(img)}"
                        )
                    )

            if missing_srcset:
                score -= 2
                for img, src in missing_srcset[:2]:
                    file_name = src.split("/")[-1].split("?")[0]
                    action_items.append(
                        ActionItem(
                            url=page.url,
                            issue=f"High-resolution banner/product image '{file_name}' lacks responsive 'srcset' and 'sizes' attributes, over-serving desktop bytes to mobile viewports",
                            selector=f"CSS: {generate_css_selector(img)}"
                        )
                    )

        score = max(0, min(10, score))
        return SectionResult(title=title, score=score, action_items=action_items)

    def evaluate_javascript_and_css_bloat(self) -> SectionResult:
        """Section 5: Asset Bloat - JavaScript Execution, Bundling & Render-Blocking Scripts."""
        title = "Asset Bloat: JavaScript Execution, Bundling & Render-Blocking Scripts"
        action_items: List[ActionItem] = []
        score = 10

        for page in self.pages:
            soup = page.soup

            scripts = soup.find_all("script", src=True)
            stylesheets = soup.find_all("link", attrs={"rel": "stylesheet"})

            # Check unminified scripts
            unminified_scripts = []
            for s in scripts:
                src = s["src"].lower().split("?")[0]
                if src.endswith(".js") and not src.endswith(".min.js") and not re.search(r'[-.][0-9a-f]{8,}\.js', src):
                    unminified_scripts.append(s)

            if unminified_scripts:
                score -= 2
                for s in unminified_scripts[:2]:
                    name = s["src"].split("/")[-1].split("?")[0]
                    action_items.append(
                        ActionItem(
                            url=page.url,
                            issue=f"Unminified script detected in production ('{name}'). Enable build minification and dead-code elimination",
                            selector=f"CSS: {generate_css_selector(s)}"
                        )
                    )

            # Check excessive stylesheet count
            if len(stylesheets) > 5:
                score -= 2
                action_items.append(
                    ActionItem(
                        url=page.url,
                        issue=f"Page links to {len(stylesheets)} separate external CSS files; consolidate stylesheets and bundle via CSS build step",
                        selector="CSS: head > link[rel='stylesheet']"
                    )
                )

            # Check inline style / script bloat
            inline_scripts = soup.find_all("script", src=False)
            total_inline_js_chars = sum(len(s.get_text()) for s in inline_scripts)
            if total_inline_js_chars > 30000:
                score -= 2
                action_items.append(
                    ActionItem(
                        url=page.url,
                        issue=f"Excessive inline JavaScript detected ({total_inline_js_chars // 1000}KB in HTML payload); move heavy client code to external deferred bundles to allow browser caching",
                        selector="XPath: //script[not(@src)]"
                    )
                )

        score = max(0, min(10, score))
        return SectionResult(title=title, score=score, action_items=action_items)

    def evaluate_third_party_scripts(self) -> SectionResult:
        """Section 6: Third-Party Script Contention & Tag Management."""
        title = "Third-Party Script Contention & Tag Management"
        action_items: List[ActionItem] = []
        score = 10

        for page in self.pages:
            soup = page.soup
            scripts = soup.find_all("script", src=True)

            detected_trackers = set()
            detected_chats = []

            for s in scripts:
                src = s["src"].lower()
                for domain, label in self.KNOWN_TRACKERS.items():
                    if domain in src:
                        detected_trackers.add((label, s))

                for domain, label in self.KNOWN_CHAT_WIDGETS.items():
                    if domain in src:
                        detected_chats.append((label, s))

            # Excessive tracker density
            if len(detected_trackers) > 4:
                score -= 3
                tracker_names = [name for name, _ in detected_trackers]
                action_items.append(
                    ActionItem(
                        url=page.url,
                        issue=f"Excessive third-party tracking scripts ({len(detected_trackers)} active: {', '.join(tracker_names[:5])}); multiple concurrent pixels congest CPU and network queues",
                        selector="XPath: //head"
                    )
                )
            elif len(detected_trackers) > 2:
                score -= 1
                tracker_names = [name for name, _ in detected_trackers]
                action_items.append(
                    ActionItem(
                        url=page.url,
                        issue=f"Multiple analytics and marketing trackers loaded on page load ({', '.join(tracker_names)}); throttle tags via GTM triggers",
                        selector="XPath: //head"
                    )
                )

            # Heavy synchronous chat widgets loaded immediately
            if detected_chats:
                for label, s in detected_chats[:1]:
                    if not s.get("defer") and not s.get("async"):
                        score -= 2
                        action_items.append(
                            ActionItem(
                                url=page.url,
                                issue=f"Live customer chat widget ({label}) is loaded synchronously on initial page load. Defer widget initialization until user interaction or page idle",
                                selector=f"CSS: {generate_css_selector(s)}"
                            )
                        )

            # Missing preconnect for third-party scripts
            preconnects = [l.get("href", "") for l in soup.find_all("link", attrs={"rel": "preconnect"})]
            needed_preconnects = set()
            for s in scripts:
                src = s["src"]
                if src.startswith("http://") or src.startswith("https://"):
                    domain = urllib.parse.urlparse(src).netloc
                    base_domain = urllib.parse.urlparse(page.url).netloc
                    if domain and domain != base_domain:
                        if not any(domain in p for p in preconnects):
                            needed_preconnects.add(domain)

            if len(needed_preconnects) > 2:
                score -= 1
                sample_domains = list(needed_preconnects)[:2]
                action_items.append(
                    ActionItem(
                        url=page.url,
                        issue=f"Missing '<link rel=\"preconnect\">' hints for critical third-party resource domains ({', '.join(sample_domains)})",
                        selector="CSS: head"
                    )
                )

        score = max(0, min(10, score))
        return SectionResult(title=title, score=score, action_items=action_items)

    def run_full_audit(self) -> List[SectionResult]:
        """Execute all Core Web Vitals and performance evaluation modules."""
        return [
            self.evaluate_lcp(),
            self.evaluate_inp(),
            self.evaluate_cls(),
            self.evaluate_image_asset_bloat(),
            self.evaluate_javascript_and_css_bloat(),
            self.evaluate_third_party_scripts(),
        ]


def crawl_website(base_url: str, sub_paths: Optional[List[str]] = None) -> List[CrawledPage]:
    """Crawl the target URL and requested sub-pages, collecting network and HTML metrics."""
    if not base_url.startswith("http://") and not base_url.startswith("https://"):
        base_url = "https://" + base_url

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36 PerformanceAuditor/1.0"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/avif,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
    }

    crawled_pages: List[CrawledPage] = []
    urls_to_visit = [base_url]

    if sub_paths:
        for p in sub_paths:
            full = urllib.parse.urljoin(base_url, p.strip())
            if full not in urls_to_visit:
                urls_to_visit.append(full)

    session = requests.Session()
    session.headers.update(headers)

    print(f"[*] Crawling target site for Speed & Core Web Vitals: {base_url}")
    for u in urls_to_visit:
        try:
            print(f"    Fetching {u} ...")
            t0 = time.time()
            resp = session.get(u, timeout=12, allow_redirects=True)
            ttfb_ms = (time.time() - t0) * 1000
            if resp.status_code == 200:
                crawled_pages.append(
                    CrawledPage(
                        url=u,
                        html=resp.text,
                        status_code=resp.status_code,
                        ttfb_ms=ttfb_ms,
                        headers=dict(resp.headers),
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
        target_keywords = ["product", "shop", "blog", "pricing", "features", "about", "contact"]
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
                t0 = time.time()
                resp = session.get(link, timeout=10, allow_redirects=True)
                ttfb_ms = (time.time() - t0) * 1000
                if resp.status_code == 200:
                    crawled_pages.append(
                        CrawledPage(
                            url=link,
                            html=resp.text,
                            status_code=resp.status_code,
                            ttfb_ms=ttfb_ms,
                            headers=dict(resp.headers),
                        )
                    )
            except Exception as e:
                print(f"    [!] Error fetching discovered page {link}: {e}")

    return crawled_pages


def format_report(base_url: str, section_results: List[SectionResult]) -> str:
    """Format audit findings into the standardized Core Web Vitals & Speed Performance report."""
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
        "CORE WEB VITALS & SPEED PERFORMANCE AUDIT REPORT",
        f"Target Site: {base_url}",
        "Generated By: Agency AI Web Vitals & Performance Auditor Agent",
        "Benchmark: Google Core Web Vitals & Chrome UX Report (CrUX) Standards",
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
    lines.append(f"Overall Performance & Web Vitals Score: {total_score}/10")
    lines.append(f"Performance Degradation Risk Level: {risk_level}")
    lines.append("Primary Speed Bottlenecks:")

    # Identify top bottlenecks from lowest scoring sections
    sorted_sections = sorted(section_results, key=lambda s: s.score)
    bottleneck_idx = 1
    for s in sorted_sections[:2]:
        if s.action_items:
            lines.append(f"{bottleneck_idx}. [{s.title}] {s.action_items[0].issue}")
            bottleneck_idx += 1

    if bottleneck_idx == 1:
        lines.append("1. None identified; performance meets Core Web Vitals standards.")

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
        lines.append("1. Maintain current performance budgets and asset optimization practices.")

    lines.append("============================================================")
    lines.append("END OF REPORT")
    lines.append("============================================================")

    return "\n".join(lines)


def run_audit(target_url: str, sub_paths: Optional[List[str]] = None, output_file: str = "performance-audit-report.txt") -> str:
    """Main performance audit execution pipeline."""
    crawled_pages = crawl_website(target_url, sub_paths)
    if not crawled_pages:
        raise RuntimeError(f"Unable to crawl target URL: {target_url}")

    evaluator = PerformanceEvaluator(base_url=target_url, pages=crawled_pages)
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
        print("Core Web Vitals & Speed Performance Auditor Agent")
        print("-------------------------------------------------")
        target = input("Enter target website base URL (e.g., https://example.com): ").strip()
        if target:
            subs_input = input("Enter optional comma-separated sub-paths (or press Enter to auto-discover): ").strip()
            subs = [s.strip() for s in subs_input.split(",") if s.strip()] if subs_input else None
            report = run_audit(target, subs)
            print("\n" + report)
        else:
            print("No URL provided. Exiting.")
