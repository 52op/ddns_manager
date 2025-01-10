import aiohttp
import asyncio
import random
import re
import logging
from typing import Optional, List
import psutil
import socket

from core import config_manager


class IPResolver:
    def __init__(self, logger: Optional[logging.Logger] = None):
        self._logger = logger or logging.getLogger(__name__)    # 定义传入的logger
        self.config_manager = config_manager.ConfigManager()
        self._ip_pattern = re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b')
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/91.0.864.59'
        ]

    async def get_ipv4(self) -> Optional[str]:
        sources = self.config_manager.global_settings['ip_sources'].copy()
        random.shuffle(sources)
        # self._logger.info(f"开始获取IPv4地址")

        headers = {
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
        }

        # 配置TCP连接器强制使用IPv4
        connector = aiohttp.TCPConnector(family=socket.AF_INET)

        async with aiohttp.ClientSession(connector=connector) as session:
            for source in sources:
                try:
                    # self._logger.info(f"尝试从 {source} 获取IPv4")
                    async with session.get(source, headers=headers, timeout=10) as response:
                        if response.status == 200:
                            text = await response.text()
                            matches = self._ip_pattern.findall(text)
                            if matches:
                                self._logger.info(f"从 {source} 成功获取IPv4: {matches[0]}")
                                return matches[0]
                except Exception as e:
                    self._logger.warning(f"无法从 {source} 获取IPv4: {e}")
                    continue
        self._logger.error("所有IPv4源均获取失败")
        return None

    async def get_ipv6(self) -> Optional[str]:
        # self._logger.info("开始获取IPv6地址")
        try:
            interfaces = psutil.net_if_addrs()
            for interface_name, addresses in interfaces.items():
                # self._logger.debug(f"检查网络接口: {interface_name}")
                for address in addresses:
                    if address.family == socket.AF_INET6:
                        ipv6 = address.address
                        if (not ipv6.startswith('fe80:') and
                                not ipv6.startswith('::') and
                                not ipv6.endswith('::1') and
                                '%' not in ipv6):
                            self._logger.info(f"找到有效IPv6: {ipv6}")
                            return ipv6
        except Exception as e:
            self._logger.error(f"无法获取IPv6: {e}")
        # self._logger.warning("未找到有效的IPv6地址")
        return None
