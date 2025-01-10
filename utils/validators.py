import re
from typing import Tuple, Optional
import ipaddress
from core.config_manager import ConfigManager
from PySide2.QtWidgets import QMessageBox


class InputValidator:
    @staticmethod
    def check_accounts_valid(config_manager: ConfigManager, parent=None) -> bool:
        accounts = config_manager.get_all_accounts()
        if not accounts:
            QMessageBox.warning(
                parent,
                "提示",
                "请先添加至少一个账号和域名配置",
                QMessageBox.Ok
            )
            return False

        for account in accounts.values():
            if account.domains:
                return True

        QMessageBox.warning(
            parent,
            "提示",
            "请至少配置一个域名",
            QMessageBox.Ok
        )
        return False


    @staticmethod
    def validate_domain(domain: str) -> Tuple[bool, Optional[str]]:
        """验证域名格式"""
        pattern = r'^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$'
        if re.match(pattern, domain):
            return True, None
        return False, "域名格式不正确"

    @staticmethod
    def validate_subdomain(subdomain: str) -> Tuple[bool, Optional[str]]:
        """验证子域名格式"""
        pattern = r'^[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?$'
        if re.match(pattern, subdomain):
            return True, None
        return False, "子域名格式不正确"

    @staticmethod
    def validate_ip(ip: str, version: int = 4) -> Tuple[bool, Optional[str]]:
        """验证IP地址格式"""
        try:
            ip_obj = ipaddress.ip_address(ip)
            if version == 4 and isinstance(ip_obj, ipaddress.IPv4Address):
                return True, None
            elif version == 6 and isinstance(ip_obj, ipaddress.IPv6Address):
                return True, None
            return False, f"IP地址版本不匹配，需要IPv{version}"
        except ValueError:
            return False, "IP地址格式不正确"

    @staticmethod
    def validate_tencent_secret_id(secret_id: str) -> Tuple[bool, Optional[str]]:
        """验证腾讯云SecretId格式"""
        if len(secret_id) < 36:
            return False, "SecretId长度不足"
        return True, None

    @staticmethod
    def validate_tencent_secret_key(secret_key: str) -> Tuple[bool, Optional[str]]:
        """验证腾讯云SecretKey格式"""
        if len(secret_key) < 32:
            return False, "SecretKey长度不足"
        return True, None

    @staticmethod
    def validate_update_interval(interval: int) -> Tuple[bool, Optional[str]]:
        """验证更新时间间隔"""
        if not isinstance(interval, int):
            return False, "更新间隔必须是整数"
        if interval < 1 or interval > 1440:
            return False, "更新间隔必须在1-1440分钟之间"
        return True, None
