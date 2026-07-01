# Copyright (c) 2026 Handsome Agent Contributors
#
# 本项目采用 MIT 许可证开源
# 详细信息请参见 LICENSE 文件

"""
URL安全检查模块
防止SSRF攻击，特别关注云元数据端点
"""

import ipaddress
import socket
from urllib.parse import urlparse

from common.logging_manager import get_logger

logger = get_logger(__name__)

# 始终阻止的云元数据IP地址
_ALWAYS_BLOCKED_IPS = frozenset({
    ipaddress.ip_address("169.254.169.254"),  # AWS/GCP/Azure/DO/Oracle metadata
    ipaddress.ip_address("169.254.170.2"),  # AWS ECS task metadata
    ipaddress.ip_address("169.254.169.253"),  # Azure IMDS wire server
    ipaddress.ip_address("fd00:ec2::254"),  # AWS metadata (IPv6)
    ipaddress.ip_address("100.100.100.200"),  # Alibaba Cloud metadata
    # IPv4-mapped IPv6 variants
    ipaddress.ip_address("::ffff:169.254.169.254"),
    ipaddress.ip_address("::ffff:169.254.170.2"),
    ipaddress.ip_address("::ffff:169.254.169.253"),
    ipaddress.ip_address("::ffff:100.100.100.200"),
})

# 始终阻止的网络段
_ALWAYS_BLOCKED_NETWORKS = (
    ipaddress.ip_network("169.254.0.0/16"),  # 整个链路本地地址段
    ipaddress.ip_network("::ffff:169.254.0.0/112"),  # IPv4映射的链路本地地址
)

# 始终阻止的主机名
_BLOCKED_HOSTNAMES = frozenset({
    "metadata.google.internal",
    "metadata.goog",
    "169.254.169.254",
    "169.254.170.2",
    "169.254.169.253",
    "100.100.100.200",
})


def _is_blocked_ip(ip) -> bool:
    """
    检查IP是否为私有/内部地址

    Args:
        ip: IP地址对象

    Returns:
        是否为阻止的地址
    """
    # 私有地址
    if ip.is_private:
        return True
    # 回环地址
    if ip.is_loopback:
        return True
    # 未指定地址
    if ip.is_unspecified:
        return True
    # 多播地址
    if ip.is_multicast:
        return True
    # 链路本地地址
    if ip.is_link_local:
        return True

    return False


def is_safe_url(url: str) -> bool:
    """
    检查URL是否安全（不指向内部/私有地址）

    Args:
        url: 要检查的URL

    Returns:
        URL是否安全
    """
    try:
        parsed = urlparse(url)
        hostname = (parsed.hostname or "").strip().lower().rstrip(".")
        scheme = (parsed.scheme or "").strip().lower()

        # 检查协议
        if scheme not in {"http", "https"}:
            logger.warning("Blocked request — unsupported URL scheme: %s", scheme or "<empty>")
            return False

        if not hostname:
            return False

        # 阻止已知的内部主机名
        if hostname in _BLOCKED_HOSTNAMES:
            logger.warning("Blocked request to internal hostname: %s", hostname)
            return False

        # 尝试解析主机名
        try:
            addr_info = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
        except socket.gaierror:
            logger.warning("Blocked request — DNS resolution failed for: %s", hostname)
            return False

        # 检查所有解析的IP地址
        for family, _, _, _, sockaddr in addr_info:
            ip_str = sockaddr[0]
            try:
                ip = ipaddress.ip_address(ip_str)
            except ValueError:
                continue

            # 始终阻止云元数据IP和链路本地地址
            if ip in _ALWAYS_BLOCKED_IPS:
                logger.warning(
                    "Blocked request to cloud metadata address: %s -> %s",
                    hostname,
                    ip_str,
                )
                return False

            for net in _ALWAYS_BLOCKED_NETWORKS:
                if ip in net:
                    logger.warning(
                        "Blocked request to link-local address: %s -> %s",
                        hostname,
                        ip_str,
                    )
                    return False

            # 阻止私有/内部地址
            if _is_blocked_ip(ip):
                logger.warning(
                    "Blocked request to private/internal address: %s -> %s",
                    hostname,
                    ip_str,
                )
                return False

        return True

    except Exception as exc:
        logger.warning("Blocked request — URL safety check error for %s: %s", url, exc)
        return False


def check_urls_in_content(content: str) -> list:
    """
    检查内容中的所有URL是否安全

    Args:
        content: 要检查的内容

    Returns:
        不安全URL的列表
    """
    import re

    # 简单的URL提取正则
    url_pattern = re.compile(
        r'https?://[^\s<>"{}|\\^`\[\]]+',
        re.IGNORECASE,
    )

    unsafe_urls = []
    for match in url_pattern.finditer(content):
        url = match.group()
        if not is_safe_url(url):
            unsafe_urls.append(url)

    return unsafe_urls