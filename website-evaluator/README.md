# Website Evaluator Suite

A specialized suite of automated auditing agents and analysis engines for client websites, built using standardized evaluation blueprints, 0–10 scoring scales, exact CSS/XPath technical remediation items, and structured text audit reports.

---

## 🛠️ Available Website Auditors

| Auditor Agent | Blueprint Skill | Python Engine | Output Report | Focus Area |
| :--- | :--- | :--- | :--- | :--- |
| 👑 **Master Audit Orchestrator** | [`website_audit_orchestrator.md`](file:///g:/My%20Drive/AI/website-evaluator/website_audit_orchestrator.md) | [`audit_orchestrator.py`](file:///g:/My%20Drive/AI/website-evaluator/audit_orchestrator.py) | `*-website-audit-review.docx` | Multi-agent concurrency, 30s status chat polling, executive scorecard, revenue risk modeling, client Word doc (.docx) |
| **ADA Accessibility Compliance** | [`ada_compliance_auditor.md`](file:///g:/My%20Drive/AI/website-evaluator/ada_compliance_auditor.md) | [`ada_compliance_auditor.py`](file:///g:/My%20Drive/AI/website-evaluator/ada_compliance_auditor.py) | `ada-compliance-report.txt` | WCAG 2.1/2.2 AA (Contrast, Keyboard, Alt Text, Form Labels, Overlays) |
| **AI Readiness & Crawlability** | [`ai_crawlability_auditor.md`](file:///g:/My%20Drive/AI/website-evaluator/ai_crawlability_auditor.md) | [`ai_crawlability_auditor.py`](file:///g:/My%20Drive/AI/website-evaluator/ai_crawlability_auditor.py) | `ai-crawlability-report.txt` | `robots.txt` (GPTBot/ClaudeBot), Schema JSON-LD, RAG structure, `llms.txt` |
| **Core Web Vitals & Performance** | [`performance_web_vitals_auditor.md`](file:///g:/My%20Drive/AI/website-evaluator/performance_web_vitals_auditor.md) | [`performance_auditor.py`](file:///g:/My%20Drive/AI/website-evaluator/performance_auditor.py) | `performance-audit-report.txt` | LCP, INP, CLS, Asset Bloat (Images, JS/CSS), Third-Party Scripts |
| **CRO & User Flow** | [`cro_userflow_auditor.md`](file:///g:/My%20Drive/AI/website-evaluator/cro_userflow_auditor.md) | [`cro_auditor.py`](file:///g:/My%20Drive/AI/website-evaluator/cro_auditor.py) | `cro-userflow-report.txt` | 5-Second Test, CTA Friction, Form Optimization, Social Proof, Mobile Flow |
| **Mobile Responsiveness & Touch UX** | [`mobile_responsiveness_auditor.md`](file:///g:/My%20Drive/AI/website-evaluator/mobile_responsiveness_auditor.md) | [`mobile_responsiveness_auditor.py`](file:///g:/My%20Drive/AI/website-evaluator/mobile_responsiveness_auditor.py) | `mobile-ux-report.txt` | Touch Targets (44px), Reflow & Overflow, Hamburger Depth, Sticky Headers, Click-to-Call, Maps |
| **Technical & Local SEO Health** | [`seo_technical_local_auditor.md`](file:///g:/My%20Drive/AI/website-evaluator/seo_technical_local_auditor.md) | [`seo_technical_local_auditor.py`](file:///g:/My%20Drive/AI/website-evaluator/seo_technical_local_auditor.py) | `seo-health-report.txt` | Title/Meta tags, H1-H6 Hierarchy, Schema.org LocalBusiness, 404s, 302 vs 301, NAP |
| **Brand Modernity & Freshness** | [`brand_modernity_auditor.md`](file:///g:/My%20Drive/AI/website-evaluator/brand_modernity_auditor.md) | [`brand_modernity_auditor.py`](file:///g:/My%20Drive/AI/website-evaluator/brand_modernity_auditor.py) | `brand-modernity-report.txt` | Stale Copyright (© 2021), Dead Social Links, Skeuomorphic Shadows, Retina SVG Clarity, Content Freshness |
| **Security, Privacy & Web Hygiene** | [`security_privacy_hygiene_auditor.md`](file:///g:/My%20Drive/AI/website-evaluator/security_privacy_hygiene_auditor.md) | [`security_privacy_auditor.py`](file:///g:/My%20Drive/AI/website-evaluator/security_privacy_auditor.py) | `security-privacy-report.txt` | SSL/TLS, Mixed Content, GDPR/CCPA Privacy & Cookie Consent, CMS Version Leakage, HSTS/CSP Headers |
| **Tracking & Measurement** | [`tracking_measurement_auditor.md`](file:///g:/My%20Drive/AI/website-evaluator/tracking_measurement_auditor.md) | [`tracking_measurement_auditor.py`](file:///g:/My%20Drive/AI/website-evaluator/tracking_measurement_auditor.py) | `tracking-measurement-report.txt` | GTM, GA4 & Meta Pixel Hygiene, Tag Duplication, Custom Conversion Events, DataLayer, Consent Mode v2 |

---

## 👑 Master Website Audit Orchestrator

The Master Orchestrator executes all **nine** specialized website auditor subagents concurrently, monitors real-time agent execution via a central chat status log polled every 30 seconds, parses and synthesizes findings across all evaluation domains, and generates an executive-ready client presentation document (`.docx`).

### Orchestration Architecture & Workflow:
1. **Dynamic Target & Client Branding Discovery:**
   - Crawls the target website to extract client brand identity: Organization Name (`og:site_name` or `<title>`), Tagline/Description (`og:description` or meta description), and high-resolution logo (favicons, touch-icons, header logo).
2. **Concurrent Multi-Agent Dispatch:**
   - Dispatches all 9 auditor subagents concurrently using a high-throughput worker pool.
3. **Central Status Chat Log & 30-Second Polling:**
   - Subagents post real-time updates (`[STARTING]`, `[IN_PROGRESS]`, `[COMPLETED]`, `[ERROR]`) to `audit_status_chat.txt` and `audit_status_chat.jsonl`.
   - The orchestrator checks the status log every 30 seconds to evaluate doneness, printing a consolidated multi-agent status table until all 9 domains finish.
4. **Synthesis & Document Generation (`.docx`):**
   - Synthesizes all 9 text audit reports into an executive-ready client presentation document formatted with agency branding (**[Brilliant Web Design](https://brilliantweb.design/)**) and the client's discovered branding.

### Client Presentation Document Structure (`.docx`):
- **Cover / Title Page:**
  - Agency branding with official Brilliant Web Design logo (`assets/brilliant_logo.jpg`), mission statement (*"We speak machine so you don't have to"*), and client branding.
- **Table of Contents:**
  - Complete navigation map across all chapters and appendices.
- **Executive Summary One-Pager:**
  - **Executive Scorecard (Red / Yellow / Green):** Visual composite scorecard formatted after the [Venngage template](https://s3.amazonaws.com/thumbnails.venngage.com/template/846ec8d6-e209-4d0f-8f8e-675ba402d6b5.png) with color-coded status badges: Green ($\ge 8.0$), Yellow ($6.0 - 7.9$), Red ($< 6.0$).
  - **"Cost of Inaction" Revenue Risk Highlight:** Translates technical debt into revenue risk (*"Based on your traffic and speed scores, you are likely losing ~15-20% of potential leads before they ever reach your contact form"*).
  - **Quick Wins vs. Strategic Modernization Proposal:** 1–2 immediate low-hanging fruit fixes (48–72h turnaround) followed by Brilliant Web Design's 30–60 day strategic overhaul.
- **Detailed Domain Audit Chapters (1 through 9):**
  - In-depth chapters for all 9 auditing domains styled after the [WhiteLabelIQ audit format](https://www.whitelabeliq.com/wp-content/uploads/2025/09/Sample-SEO-Audit-Analysis-Report.pdf), featuring score banners, benchmark standards, primary bottlenecks, top priorities, and structured defect remediation tables with CSS selectors.
- **Strategic Next Steps & Engagement Roadmap:**
  - Brilliant Web Design 3-phase execution model: Immediate Triage, Comprehensive Modernization, and Continuous Monitoring.

### Running the Master Orchestrator:
```powershell
# Run full 9-agent audit and generate executive client presentation document (.docx)
python audit_orchestrator.py https://example.com

# Audit with specific key conversion and sub-paths
python audit_orchestrator.py https://example.com /about /services /pricing /contact /shop

# Custom 15-second status polling
python audit_orchestrator.py https://example.com --poll 15
```

---

## ⚡ Core Web Vitals & Speed Performance Auditor

Audits websites for rendering speed, user interaction responsiveness, layout stability, and asset bloat against Google Core Web Vitals benchmarks.

### Evaluation Dimensions:
1. **Core Web Vitals: Largest Contentful Paint (LCP) Optimization:**
   - How fast the main content renders (target: $\le$ 2.5s).
   - Audits hero LCP image lazy-loading anti-pattern (`loading="lazy"`), missing `<link rel="preload" as="image">` and `fetchpriority="high"`, server response latency (TTFB > 800ms), and render-blocking CSS/fonts.
2. **Core Web Vitals: Interaction to Next Paint (INP) & Main-Thread Responsiveness:**
   - How responsive the UI feels when clicked or tapped (target: $\le$ 200ms).
   - Audits synchronous parser-blocking scripts in `<head>` lacking `defer` or `async`, excessive external script volume, duplicate heavy frameworks (e.g. jQuery + React), and CPU-heavy hydration.
3. **Core Web Vitals: Cumulative Layout Shift (CLS) & Visual Stability:**
   - Visual instability and jumping elements while loading (target: $\le$ 0.1).
   - Audits `<img>`, `<video>`, and `<iframe>` elements missing explicit `width`/`height` or CSS `aspect-ratio`, dynamically injected announcement banners lacking reserved `min-height`, and web font reflow (FOUT).
4. **Asset Bloat: Modern Image Formats & Media Optimization:**
   - Detects huge uncompressed images in legacy formats (`.png`, `.jpg`, `.jpeg`) that should use WebP/AVIF.
   - Audits lack of responsive `srcset` and `sizes` attributes (over-serving desktop images to mobile), and replaces animated GIFs with HTML5 video or animated WebP.
5. **Asset Bloat: JavaScript Execution, Bundling & Render-Blocking Scripts:**
   - Detects unminified scripts in production, monolithic CSS stylesheets, and excessive inline script payloads.
6. **Third-Party Script Contention & Tag Management:**
   - Audits tracker proliferation (multiple concurrent analytics, pixels, and session recorders), synchronous live chat widgets blocking initial paint, and missing `rel="preconnect"` resource hints.

### Running the Performance Audit:
```powershell
# Basic audit (crawls base URL and auto-discovers sub-pages)
python performance_auditor.py https://example.com

# Audit with specific sub-pages
python performance_auditor.py https://example.com /shop /blog /pricing /checkout
```

---

## 🎯 Conversion Rate Optimization (CRO) & User Flow Auditor

Audits websites to reduce conversion friction and guide visitors toward primary actions.

### Evaluation Dimensions:
1. **The 5-Second Test & Value Proposition Clarity:**
   - Can a first-time visitor immediately identify what the company does, who it serves, and why they should choose them without scrolling?
2. **Call-to-Action (CTA) Friction & Visual Hierarchy:**
   - Identifies buried buttons, inconsistent styling, Hick's law choice paralysis (multiple competing primary buttons), and passive microcopy (`Submit`, `Click Here`).
3. **Form Optimization & Funnel Drop-off:**
   - Audits excessive form fields, missing HTML5 `autocomplete` attributes, incorrect input types for mobile keyboards (`type="tel"`, `type="email"`), disappearing placeholder labels, and lack of inline validation.
4. **Trust Elements, Social Proof & Risk Reversal:**
   - Audits proximity of trust markers: verified reviews/star ratings, client logo bars, case studies, risk reducers (money-back guarantees, no credit card required), and security badges.
5. **User Flow Continuity & Funnel Navigation:**
   - Eliminates navigation leaks on high-intent conversion pages (checkout, demo booking) and dead ends.
6. **Mobile Conversion & Touch Ergonomics:**
   - Audits mobile viewport configuration, thumb-zone reachability, and persistent sticky bottom conversion anchors.

### Running the CRO Audit:
```powershell
# Basic audit
python cro_auditor.py https://example.com

# Audit with key funnel paths
python cro_auditor.py https://example.com /pricing /contact /demo /signup
```

---

## ♿ ADA Website Compliance Auditor

Audits websites for digital accessibility compliance under the **Americans with Disabilities Act (ADA)** and **WCAG 2.1 & 2.2 Level AA** standards.

### Evaluation Dimensions:
1. **Perceivable: Text Alternatives & Media:** Meaningful image `alt` attributes, closed captions for video/audio.
2. **Perceivable: Color Contrast & Visual Reflow:** 4.5:1 text contrast ratio, zoom reflow up to 400%, no color-only information.
3. **Operable: Keyboard Navigation & Focus Control:** Operability without mouse, "Skip to Main Content" bypass link, visible focus rings.
4. **Operable: Touch Targets & Motion:** 24x24px / 44x44px touch target tolerances, pause/stop controls for moving banners/videos.
5. **Understandable: Forms & Error Validation:** Form labels (`for="id"`), persistent labels, `<html lang="...">` declaration.
6. **Robust: Semantic Structure & ARIA Hierarchy:** HTML5 landmarks, strict heading hierarchy, ARIA state attributes.
7. **Native Accessibility & Overlay Assessment:** Checks native source code compliance vs. reliance on third-party JS overlays (accessiBe, UserWay), Accessibility Statement link.

### Running the ADA Audit:
```powershell
# Basic audit
python ada_compliance_auditor.py https://example.com

# Audit with specific sub-pages
python ada_compliance_auditor.py https://example.com /about /contact /team /services
```

---

## 🤖 AI Readiness & Crawlability Auditor

Audits websites for conversational search indexing, AI readiness, and LLM crawlability.

### Evaluation Dimensions:
1. **Technical Crawlability:** `robots.txt` rules for `GPTBot`, `ClaudeBot`, `PerplexityBot`, `Google-Extended`, and `Sitemap` directives.
2. **Semantic HTML:** Semantic HTML5 landmarks (`<main>`, `<header>`, `<nav>`, `<article>`, `<footer>`) vs. generic nested `<div>` soup.
3. **Accessibility Tree:** Image alt descriptions and explicit button labels for headless browser agents.
4. **Content Structure for RAG Systems:** Clear, entity-grounded headings and 40–60 word introductory summary blocks under major sections for vector chunking.
5. **Structured Data & Schema Markup:** JSON-LD schema arrays (`Organization`, `WebSite`, `FAQPage`, `Article`, `Product`).
6. **Machine-Friendly Formats:** Verifies `/llms.txt` and `/llms-full.txt` presence and content.

### Running the AI Crawlability Audit:
```powershell
# Basic audit
python ai_crawlability_auditor.py https://example.com

# Audit with specific sub-pages
python ai_crawlability_auditor.py https://example.com /about /faq /products /blog
```

---

## 📱 Mobile Responsiveness & Touch UX Auditor

Audits websites strictly from the perspective of smartphone and touch device users against Google Mobile-First Indexing and touch interface standards.

### Evaluation Dimensions:
1. **Touch Targets & Thumb Ergonomics:**
   - Audits interactive targets measuring $<44$x$44$px (Apple HIG) or $<48$x$48$px (Android Material Design) and tightly packed pagination or link clusters with $<8$px spacing.
2. **Viewport Configuration & Responsive Layout Reflow:**
   - Detects missing/invalid viewport meta tags, zoom prevention (`user-scalable=no`), fixed-width containers ($>500$px) causing horizontal scroll, and unconstrained tables or media.
3. **Mobile Navigation & Sticky Header Real Estate:**
   - Flags sticky/fixed mobile headers consuming more than $15\text{--}20\%$ of vertical screen height ($>80\text{--}100$px) and cumbersome hamburger menus with $>2$ levels of nested sub-menus.
4. **Mobile Click-to-Call & Local Directions Integration:**
   - Detects static plain-text phone numbers missing `<a href="tel:...">` links and physical street addresses missing tap-to-navigate links (`maps.google.com` or `geo:` URIs).
5. **Mobile Form Ergonomics & Font Auto-Zoom Prevention:**
   - Flags input field font-sizes $<16$px triggering disruptive iOS Safari automatic zooming upon focus, inputs lacking `type="tel"` or numeric keypads, and input heights $<44$px.
6. **Mobile Interstitials & Overlay Friction:**
   - Audits aggressive full-screen popups, mobile modals with tiny close buttons ($<30$px), and oversized mobile cookie banners.

### Running the Mobile UX Audit:
```powershell
# Basic audit (crawls base URL using Mobile Safari / iPhone user-agent)
python mobile_responsiveness_auditor.py https://example.com

# Audit with key mobile pages
python mobile_responsiveness_auditor.py https://example.com /contact /locations /services /menu
```

---

## 🔍 Technical & Local SEO Health Auditor

Audits websites for organic search visibility, Google Search Essentials compliance, rich snippet Schema markup, and Google Local Pack ranking signals.

### Evaluation Dimensions:
1. **Metadata & SERP Snippet Optimization:**
   - Evaluates title tag length (50–60 characters), meta description quality and length (120–160 characters), duplicate titles across pages, and Open Graph social tags (`og:title`, `og:description`, `og:image`).
2. **Document Heading Hierarchy (H1-H6):**
   - Validates single authoritative `<h1>` presence, flags multiple conflicting `<h1>` tags, and detects skipped heading levels (e.g. `<h1>` to `<h4>`).
3. **Structured Data (Schema.org) & Rich Snippets:**
   - Audits JSON-LD markup for `LocalBusiness` (validating essential NAP, geo-coordinates, and opening hours), `Organization`, `Service`, `Product`, and `FAQPage` schema.
4. **Broken Links, HTTP Status & Redirect Hygiene:**
   - Detects internal and outbound 404/500 errors, temporary HTTP 302 redirects instead of permanent 301s (preventing PageRank loss), and insecure `http://` internal links.
5. **Indexing Directives & Canonicalization:**
   - Detects accidental `<meta name="robots" content="noindex">` on critical pages and validates self-referential `<link rel="canonical">` consistency.
6. **Local SEO Citations & NAP Consistency:**
   - Checks footer and contact area for phone numbers, physical street addresses, embedded Google Maps, and targeted geographic service keywords.

### Running the SEO Audit:
```powershell
# Basic audit (crawls base URL and auto-discovers key pages)
python seo_technical_local_auditor.py https://example.com

# Audit with specific sub-pages
python seo_technical_local_auditor.py https://example.com /services /about /contact /locations /faq
```

---

## 🎨 Brand Modernity & Content Freshness Auditor

Audits websites for contemporary aesthetic polish, visual trust cues, ongoing maintenance recency, and Retina/high-DPI display fidelity.

### Evaluation Dimensions:
1. **Visual Trust Clues: Copyright Year & Maintenance Recency:**
   - Detects outdated hardcoded footer copyright years (e.g. `"© 2021"`) signaling brand abandonment or neglected site maintenance, and audits dynamic year automation.
2. **Social Channel Integrity & Active Community Links:**
   - Detects dummy social link placeholders (`href="#"`, `href="https://facebook.com/yourhandle"`), dead/broken profiles (HTTP 404), and legacy Twitter URLs/icons without modern X branding.
3. **Visual Trend Modernity & Skeuomorphic Anti-Patterns:**
   - Audits harsh, un-diffused black drop shadows (`box-shadow`), obsolete HTML tags (`<marquee>`, `<font>`, `<center>`), and dated 2010s generic business stock photo tropes (e.g. disembodied handshakes, call center headsets).
4. **Cross-Browser & Retina Clarity (High-DPI Assets):**
   - Identifies blurry non-SVG brand logos and UI icons delivered as low-resolution raster images (`.png`, `.jpg`, `.gif`) lacking modern `@2x` `srcset` or scalable SVG vectors, and checks for high-res touch icons/favicons.
5. **Content Freshness & Publication Recency:**
   - Audits publication dates across blogs, press releases, and case studies, flagging abandoned editorial channels ($>12\text{--}24$ months without updates).
6. **Modern Typography & Color Contrast Standards:**
   - Audits excessive font family proliferation ($>3$ distinct font families) and low-contrast "whisper" gray text styles.

### Running the Brand Modernity Audit:
```powershell
# Basic audit (crawls base URL and auto-discovers blog/about pages)
python brand_modernity_auditor.py https://example.com

# Audit with specific sub-pages
python brand_modernity_auditor.py https://example.com /blog /about /company /press
```

---

## 🛡️ Security, Privacy & Web Hygiene Auditor

Audits client websites for public-facing defensive weaknesses, unencrypted asset leakage, data privacy compliance, CMS version disclosure, and defensive header hygiene.

### Evaluation Dimensions:
1. **SSL/TLS Configuration & Mixed Content Integrity:**
   - Automatic HTTP-to-HTTPS redirect enforcement (permanent 301/308 redirects).
   - Active mixed content (`<script>`, `<link rel="stylesheet">`, `<iframe>`) loading over unencrypted HTTP on HTTPS origins.
   - Passive mixed content (`<img>`, `<video>`, `<audio>`) loaded insecurely.
2. **Privacy Compliance & Legal Consent Frameworks (GDPR/CCPA):**
   - Mandatory Privacy Policy and Terms of Service presence in global footer navigation (GDPR Art. 13, CalOPPA).
   - Cookie consent banner & CMP enforcement prior to firing third-party marketing/analytics trackers (GDPR prior-consent).
   - CCPA/CPRA "Do Not Sell or Share My Personal Information" / "Your Privacy Choices" opt-out mechanisms.
3. **Software Version Disclosure & CMS Hygiene:**
   - Exposed CMS generator meta tags (`<meta name="generator" content="WordPress X.X">`) broadcasting versions to automated exploit bots.
   - Asset version queries (`?ver=X.X.X`) leaking specific installed plugin and theme builds.
   - Server software and runtime headers (`Server`, `X-Powered-By`) revealing detailed stack versions.
4. **HTTP Defensive Security Headers Hygiene:**
   - `Strict-Transport-Security` (HSTS) with recommended duration ($\ge 6\text{ months}$), `includeSubDomains`, and `preload`.
   - `Content-Security-Policy` (CSP) restricting script sources and eliminating unsafe execution.
   - Clickjacking defense (`X-Frame-Options: DENY` or `SAMEORIGIN`), MIME-sniffing prevention (`X-Content-Type-Options: nosniff`), privacy-preserving `Referrer-Policy`, and hardware `Permissions-Policy`.
5. **Form Transmission & Input Security:**
   - Forms on HTTPS pages submitting data to insecure HTTP destinations (`action="http://..."`).
   - Sensitive forms using GET instead of POST methods, password fields lacking `autocomplete="current-password"` or `new-password`, and state-changing POST forms lacking CSRF anti-forgery tokens.
6. **Cookie Security & Attribute Hygiene:**
   - `Secure` flag on HTTPS cookies preventing plaintext network transmission.
   - `HttpOnly` flag on session and authentication tokens preventing theft via XSS.
   - `SameSite` attribute (`Lax` or `Strict`) preventing Cross-Site Request Forgery (CSRF).

### Running the Security & Privacy Audit:
```powershell
# Basic audit (crawls base URL and auto-discovers privacy, terms, login, and contact pages)
python security_privacy_auditor.py https://example.com

# Audit with specific sub-pages
python security_privacy_auditor.py https://example.com /privacy /terms /login /contact
```

---

## 📊 Tracking & Measurement Architecture Auditor

Audits client websites for measurement accuracy, tag container hygiene, conversion event instrumentation, dataLayer reliability, and privacy-preserving Consent Mode v2 standards.

### Evaluation Dimensions:
1. **Core Tag Deployment & Container Hygiene (GTM, GA4, Meta Pixel):**
   - Verification of GTM snippet in `<head>` and companion `<noscript>` fallback iframe in `<body>`.
   - Detection of duplicated Google Analytics 4 (GA4) Measurement IDs (`G-XXXXX`) firing multiple times on the same page load.
   - Detection of duplicated Meta (Facebook) Pixel IDs (`fbq('init')`) artificially inflating PageView volumes.
   - Elimination of obsolete Universal Analytics scripts (`UA-XXXXX-Y` / `analytics.js`).
2. **Conversion Event Architecture & Micro-Action Tracking:**
   - Lead generation forms submitting without `dataLayer.push({'event': 'generate_lead', ...})` or conversion telemetry.
   - Click-to-call (`href="tel:..."`) anchor links lacking click listeners or custom dataLayer events (`click_to_call`).
   - Click-to-email (`href="mailto:..."`) anchor links lacking click dispatchers.
   - High-value file download links (`.pdf`, `.docx`, `.xlsx`, `.zip`) lacking `file_download` tracking.
3. **DataLayer Architecture & State Management:**
   - Initialization order: Ensuring `window.dataLayer = window.dataLayer || [];` executes *before* Google Tag Manager loads.
   - Prevention of direct array assignment (`dataLayer = [...]`) that destroys pre-existing push queues.
   - Contextual page metadata (page type, template, user state) pushed into the dataLayer on initial render.
4. **E-Commerce & Funnel Step Measurement:**
   - Standard GA4 and Meta e-commerce event instrumentation: product detail view (`view_item` / `ViewContent`), add to cart (`add_to_cart` / `AddToCart`), checkout initiation (`begin_checkout` / `InitiateCheckout`), and order confirmation (`purchase` / `Purchase`).
   - Verification of transaction ID, item SKU arrays, and revenue values for ROAS attribution.
5. **Google Consent Mode v2 & Privacy-Preserving Measurement:**
   - Default state initialization: `gtag('consent', 'default', { ... })` executed prior to tag library loading.
   - Verification of modern Consent Mode v2 parameters (`ad_user_data`, `ad_personalization`, `ad_storage`, `analytics_storage`) required for Google Ads remarketing and conversion modeling in the EU/EEA.
6. **Ad Platform Pixels & Attribution Hygiene:**
   - Multi-channel ad pixel health (LinkedIn Insight Tag, TikTok Pixel, Twitter/X Ads, Microsoft UET, Pinterest).
   - Server-Side Conversions API (CAPI) event deduplication markers (`event_id` / `eventId`).
   - Detection of placeholder or unconfigured tracking IDs (`YOUR_PIXEL_ID`, `GTM-XXXXXX`).

### Running the Tracking & Measurement Audit:
```powershell
# Basic audit (crawls base URL and auto-discovers conversion/e-commerce sub-pages)
python tracking_measurement_auditor.py https://example.com

# Audit with specific sub-pages
python tracking_measurement_auditor.py https://example.com /contact /pricing /shop /cart /checkout
```

---

## 📝 Standardized Report Output Format

All auditors produce clean, highly actionable `.txt` reports (`performance-audit-report.txt`, `cro-userflow-report.txt`, `ada-compliance-report.txt`, `ai-crawlability-report.txt`, `mobile-ux-report.txt`, `seo-health-report.txt`, `brand-modernity-report.txt`, `security-privacy-report.txt`, `tracking-measurement-report.txt`) following this exact format:

```text
============================================================
<AUDIT SUITE NAME> AUDIT REPORT
Target Site: [Target URL]
Generated By: Agency AI Auditor Agent
Benchmark: [Industry Standards Benchmark]
============================================================

<Section Title>: <Score>/10
<URL> | <Identified issue / technical recommendation> at <CSS / XPath / Network selector>

============================================================
OVERALL SUMMARY & RECOMMENDATIONS
Overall Score: [X/10]
Risk Level: [Low / Moderate / High / Critical]
Primary Bottlenecks:
1. [Primary blocker]
2. [Secondary blocker]
Top Remediation Priorities:
1. [Highest impact, lowest effort change]
2. [Second priority remediation]
3. [Third priority remediation]
============================================================
END OF REPORT
============================================================
```
