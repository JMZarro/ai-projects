How to Use the Agent
1. Interactive Mode

Run the agent without arguments:

powershell
python "hosting_detector_agent.py"
text
============================================================
🌐 Hosting Platform Detector Agent
Identifies the web hosting platform behind any website URL.
Type 'q' or 'exit' to quit.
============================================================
Enter website URL: www.example1.com
"www.example1.com" hosted by 'Hostinger' (https://www.hostinger.com/)
2. Single Command-Line Lookup
powershell
python "hosting_detector_agent.py" "www.example1.com"

Output:

text
"www.example1.com" hosted by 'Hostinger' (https://www.hostinger.com/)
3. Verbose Diagnostic Mode (-v)
powershell
python "hosting_detector_agent.py" "nextjs.org" -v

Output:

text
[+] Inspecting target: nextjs.org (Host: nextjs.org)
"nextjs.org" hosted by 'Vercel' (https://vercel.com/)
Detection Breakdown:
  Confidence: 100%
  IPs: 64.239.109.193
  ASN/Org: AS16509 Amazon.com, Inc. Vercel, Inc
  Nameservers: ns1.vercel-dns.com., ns2.vercel-dns.com.
  Evidence:
    - HTTP header 'server: Vercel' matches Vercel
    - HTTP header 'x-vercel-id: iad1::...' matches Vercel
    - Nameserver matches pattern 'vercel-dns\.com'
    - IP ASN/ISP matches 'vercel'
4. Python API
python
from hosting_detector_agent import HostingDetectorAgent
agent = HostingDetectorAgent()
result = agent.detect("www.example1.com")
# Exact formatted output requested:
print(result.format_summary())
# "www.example1.com" hosted by 'Hostinger' (https://www.hostinger.com/)