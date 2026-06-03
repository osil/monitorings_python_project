import socket
from typing import Dict, Optional

import requests


_IP_CACHE: Optional[Dict[str, str]] = None


def get_private_ip() -> str:
    """Return the current machine private IP in LAN."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("8.8.8.8", 80))
        private_ip = sock.getsockname()[0]
        sock.close()
        return private_ip
    except Exception:
        try:
            return socket.gethostbyname(socket.gethostname())
        except Exception:
            return "0.0.0.0"


def get_public_ip(timeout: float = 5.0) -> str:
    """Return public IP using reliable external endpoints with fallback."""
    endpoints = [
        ("https://api.ipify.org?format=json", "json"),
        ("https://ifconfig.me/ip", "text"),
        ("https://icanhazip.com", "text"),
    ]

    for url, response_type in endpoints:
        try:
            response = requests.get(url, timeout=timeout)
            if response.status_code != 200:
                continue

            if response_type == "json":
                ip = response.json().get("ip", "").strip()
            else:
                ip = response.text.strip()

            if ip:
                return ip
        except Exception:
            continue

    return "0.0.0.0"


def get_ip_info(force_refresh: bool = False) -> Dict[str, str]:
    """Return both private and public IP addresses with process-level cache."""
    global _IP_CACHE

    if force_refresh or _IP_CACHE is None:
        _IP_CACHE = {
            "private_ip": get_private_ip(),
            "public_ip": get_public_ip(),
        }

    return dict(_IP_CACHE)
