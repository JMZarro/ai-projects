# 🌐 Hosting Platform Detector Agent

An agent that analyzes any website URL or domain name to identify its web hosting platform, cloud infrastructure, or site builder.

---

## ⚡ Quick Start

### 1. Interactive Mode
Run the agent without arguments to start an interactive prompt:

```bash
python hosting_detector_agent.py
```
*(or using the shortcut `python hosting_agent.py`)*

```text
============================================================
🌐 Hosting Platform Detector Agent
Identifies the web hosting platform behind any website URL.
Type 'q' or 'exit' to quit.
============================================================

Enter website URL: www.example1.com
"www.example1.com" hosted by 'Hostinger' (https://www.hostinger.com/)
```

### 2. Single Command-Line Lookup
Pass any URL or domain directly as an argument:

```bash
python hosting_detector_agent.py "www.example1.com"
```
**Output:**
```text
"www.example1.com" hosted by 'Hostinger' (https://www.hostinger.com/)
```

### 3. Verbose Diagnostic Mode (`-v` / `--verbose`)
Inspect full DNS records, IPs, ASN, HTTP headers, and matching evidence:

```bash
python hosting_detector_agent.py "nextjs.org" -v
```
**Output:**
```text
[+] Inspecting target: nextjs.org (Host: nextjs.org)
"nextjs.org" hosted by 'Vercel' (https://vercel.com/)

Detection Breakdown:
  Confidence: 100%
  IPs: 64.239.109.193
  ASN/Org: AS16509 Amazon.com, Inc. Vercel, Inc
  Nameservers: ns1.vercel-dns.com., ns2.vercel-dns.com.
  Evidence:
    - HTTP header 'server: Vercel' matches Vercel
    - HTTP header 'x-vercel-id: ...' matches Vercel
    - Nameserver matches pattern 'vercel-dns\.com'
    - IP ASN/ISP matches 'vercel'
```

### 4. JSON Mode (`--json`)
Output structured JSON data for integration into other pipelines:

```bash
python hosting_detector_agent.py "shopify.com" --json
```

### 5. Batch Processing (`--file`)
Process multiple URLs from a text file:

```bash
python hosting_detector_agent.py --file urls.txt
```

---

## 🐍 Python API Usage

You can import and use the agent directly in your Python code:

```python
from hosting_detector_agent import HostingDetectorAgent

agent = HostingDetectorAgent()
result = agent.detect("www.example1.com")

# Exact formatted output:
print(result.format_summary())
# "www.example1.com" hosted by 'Hostinger' (https://www.hostinger.com/)

# Detailed properties:
print(result.platform_name)     # "Hostinger"
print(result.platform_url)      # "https://www.hostinger.com/"
print(result.confidence)        # 0.95
print(result.evidence)          # ['Nameserver matches...', 'HTTP Server...']
print(result.resolved_ips)      # ['172.67....']
print(result.nameservers)       # ['ns1.dns-parking.com', ...]
```

---

## 🔍 How Detection Works

The agent uses a multi-layered detection strategy:

1. **DNS & Infrastructure Discovery (DoH)**:
   - Queries Google and Cloudflare DNS-over-HTTPS (DoH) for `NS`, `CNAME`, `A`, `AAAA`, `SOA`, and `TXT` records without needing external binary dependencies.
2. **HTTP/HTTPS Fingerprinting & Anti-Bot Fallback**:
   - Sends HTTP requests with a browser User-Agent to extract `Server`, `X-Powered-By`, and provider-specific tokens (`X-Hostinger-Cache`, `X-Shopify-Stage`, `X-Vercel-Id`, `X-Wix-Request-Id`, etc.).
   - **Rule 3 Compliance**: Automatically falls back to `curl.exe` via `subprocess` if anti-bot protections or Cloudflare TLS fingerprinting return 403/429.
3. **HTML Inspection**:
   - Inspects `<meta name="generator">` tags and static asset CDN domains (`cdn.shopify.com`, `static.wixstatic.com`, `assets.squarespace.com`).
4. **IP Geolocation, Reverse DNS (PTR) & ASN**:
   - Resolves IP PTR records (e.g. `*.main-hosting.com`, `*.secureserver.net`).
   - Queries IP ASN and Organization (e.g. `Hostinger International Ltd`, `Wix.com Ltd.`).
5. **CDN & Origin Disambiguation**:
   - Intelligently disambiguates between proxy CDNs (e.g., Cloudflare, CloudFront, Fastly) and origin hosting providers (e.g., Hostinger, Shopify, Squarespace, Wix, WP Engine). If a site sits behind Cloudflare, the origin hosting provider is reported as primary, with the CDN noted in the evidence.

---

## 🧪 Testing

Run the test suite:

```bash
python test_hosting_detector_agent.py
```
