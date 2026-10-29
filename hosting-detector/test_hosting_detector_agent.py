"""
Unit and Integration Tests for Hosting Platform Detector Agent
==============================================================
Validates:
- Normalization logic
- Fingerprint detection and weighted scoring
- GEMINI.md Rule 1: Thread-safe status logging with flush
- GEMINI.md Rule 2: json.JSONDecodeError per-line resilience
- GEMINI.md Rule 3: curl fallback mechanism
- GEMINI.md Rule 4: Dynamic loading via importlib
"""

import json
import os
import tempfile
import threading
import unittest
from pathlib import Path

from hosting_detector_agent import (
    HOSTING_PROVIDERS,
    HostingDetectionResult,
    HostingDetectorAgent,
    ThreadSafeStatusLogger,
    load_agent_module,
)


class TestHostingDetectorAgent(unittest.TestCase):

    def setUp(self):
        self.agent = HostingDetectorAgent(timeout=3.0)

    def test_normalization(self):
        """Tests input URL and domain normalization."""
        cases = [
            ("www.example1.com", "www.example1.com", "www.example1.com"),
            ("https://www.example1.com/sub/page?q=1", "https://www.example1.com/sub/page?q=1", "www.example1.com"),
            ("http://sub.domain.co.uk/", "http://sub.domain.co.uk/", "sub.domain.co.uk"),
            ("  'myshop.shopify.com'  ", "myshop.shopify.com", "myshop.shopify.com"),
            ("example.org", "example.org", "example.org"),
        ]
        for raw, expected_target, expected_host in cases:
            target, host = self.agent.normalize_input(raw)
            self.assertEqual(host, expected_host, f"Failed for {raw}")

    def test_hostinger_signature_matching(self):
        """Tests that Hostinger signatures are recognized correctly."""
        provider, confidence, evidence, cdn = self.agent.evaluate_signals(
            domain="www.example1.com",
            dns_records={
                "NS": ["ns1.dns-parking.com", "ns2.dns-parking.com"],
                "CNAME": [],
                "SOA": ["dns1.hostinger.com"],
                "TXT": ["v=spf1 include:spf.hostinger.com ~all"],
            },
            headers={"server": "LiteSpeed"},
            html_snippet="<html><head></head><body>Hello</body></html>",
            ptrs=["srv1.main-hosting.com"],
            asn_info={"isp": "Hostinger International Ltd", "as": "AS47583"},
        )
        self.assertEqual(provider.name, "Hostinger")
        self.assertEqual(provider.url, "https://www.hostinger.com/")
        self.assertGreater(confidence, 0.7)
        self.assertTrue(any("hostinger" in ev.lower() or "dns-parking" in ev.lower() for ev in evidence))

    def test_shopify_signature_matching(self):
        """Tests that Shopify signatures are recognized correctly even behind Cloudflare."""
        provider, confidence, evidence, cdn = self.agent.evaluate_signals(
            domain="store.example.com",
            dns_records={
                "NS": ["ns1.cloudflare.com"],
                "CNAME": ["shops.myshopify.com"],
                "SOA": [],
                "TXT": [],
            },
            headers={
                "server": "cloudflare",
                "x-shopify-stage": "production",
                "x-sorting-hat-podid": "123",
            },
            html_snippet='<html><head><meta name="generator" content="Shopify"></head></html>',
            ptrs=[],
            asn_info={"isp": "Cloudflare, Inc."},
        )
        # Should disambiguate and select Shopify as the true hosting platform, not Cloudflare!
        self.assertEqual(provider.name, "Shopify")
        self.assertEqual(provider.url, "https://www.shopify.com/")
        self.assertEqual(cdn, "Cloudflare")

    def test_vercel_signature_matching(self):
        """Tests that Vercel is recognized correctly."""
        provider, confidence, evidence, cdn = self.agent.evaluate_signals(
            domain="nextapp.com",
            dns_records={
                "NS": ["ns1.vercel-dns.com"],
                "CNAME": ["cname.vercel-dns.com"],
                "SOA": [],
                "TXT": [],
            },
            headers={
                "server": "Vercel",
                "x-vercel-id": "iad1::xyz",
                "x-vercel-cache": "HIT",
            },
            html_snippet="",
            ptrs=[],
            asn_info={"isp": "Vercel, Inc."},
        )
        self.assertEqual(provider.name, "Vercel")
        self.assertEqual(provider.url, "https://vercel.com/")

    def test_format_summary(self):
        """Tests that format_summary produces the exact string format requested by user."""
        res = HostingDetectionResult(
            target_input="www.example1.com",
            normalized_domain="www.example1.com",
            platform_name="Hostinger",
            platform_url="https://www.hostinger.com/",
            confidence=0.95,
        )
        expected = '"www.example1.com" hosted by \'Hostinger\' (https://www.hostinger.com/)'
        self.assertEqual(res.format_summary(), expected)

    def test_gemini_rule_1_and_2_thread_safe_logging(self):
        """
        Tests GEMINI.md Rule 1 (threading.Lock + flush) and
        Rule 2 (safe per-line json.JSONDecodeError recovery).
        """
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jsonl") as tf:
            log_path = tf.name

        try:
            logger = ThreadSafeStatusLogger(log_path)

            def worker(worker_id: int):
                for i in range(10):
                    logger.log_event({
                        "worker": worker_id,
                        "iteration": i,
                        "target": f"site_{worker_id}_{i}.com",
                    })

            threads = [threading.Thread(target=worker, args=(t,)) for t in range(5)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            # Now artificially inject corrupt/malformed lines into the JSONL file
            with open(log_path, "a", encoding="utf-8") as f:
                f.write("\nTHIS IS CORRUPT NOT JSON\n")
                f.write('{"valid": true, "after_corrupt": 1}\n')
                f.write("{unclosed_json: true\n")

            # Verify Rule 2: read_jsonl_safely must read all valid lines without crashing
            records = ThreadSafeStatusLogger.read_jsonl_safely(log_path)
            self.assertEqual(len(records), 51)  # 50 worker events + 1 valid post-corrupt event
            self.assertEqual(records[-1]["valid"], True)

        finally:
            if os.path.exists(log_path):
                os.remove(log_path)

    def test_gemini_rule_3_curl_fallback(self):
        """
        Tests GEMINI.md Rule 3:
        Subprocess fallback to curl.exe when requests hits 403/429 or TLS block.
        """
        from unittest.mock import patch, MagicMock

        mock_resp = MagicMock()
        mock_resp.status_code = 403

        with patch("hosting_detector_agent.requests.Session.get", return_value=mock_resp), \
             patch.object(self.agent, "_run_curl_probe", return_value=({"server": "cloudflare"}, "<html></html>", "https://blocked.com")) as mock_curl:

            headers, body, url = self.agent.fetch_http_fingerprint("blocked.com")
            self.assertTrue(mock_curl.called, "curl fallback was not invoked on 403!")
            self.assertEqual(headers.get("server"), "cloudflare")

    def test_gemini_rule_4_dynamic_loading(self):
        """Tests GEMINI.md Rule 4: Dynamic loading via importlib."""
        curr_dir = Path(__file__).parent
        agent_file = curr_dir / "hosting_detector_agent.py"
        loaded = load_agent_module(str(agent_file), "dynamic_agent_test")
        self.assertTrue(hasattr(loaded, "HostingDetectorAgent"))


if __name__ == "__main__":
    unittest.main()
