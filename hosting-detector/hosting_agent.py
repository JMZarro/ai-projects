"""
Hosting Platform Detector Agent - Entrypoint
============================================
Convenience alias and launcher for hosting_detector_agent.py.
"""

from hosting_detector_agent import (
    HostingDetectorAgent,
    HostingDetectionResult,
    HostingProviderSignature,
    ThreadSafeStatusLogger,
    load_agent_module,
    main,
)

if __name__ == "__main__":
    main()
