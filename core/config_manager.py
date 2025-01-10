import logging
import os
from dataclasses import dataclass
from typing import List, Dict, Optional
import json
from utils.encryption import EncryptionHandler


@dataclass
class DomainConfig:
    subdomain: str
    record_type: str  # 'A' or 'AAAA'
    line: str
    enabled: bool = True


@dataclass
class AccountConfig:
    secret_id: str
    secret_key: str
    domains: Dict[str, List[DomainConfig]]
    update_interval: int = 300


class ConfigManager:
    def __init__(self):
        self.accounts = {}
        self.global_settings = {
            'startup_enabled': False,
            'update_interval': 5,
            'ip_sources': [
                'http://www.3322.org/dyndns/getip',
                'https://ifconfig.me/ip',
                'https://api.ip.sb/ip'
            ]
        }
        self.encryption = EncryptionHandler()
        # 初始化时立即加载配置
        self.load_config()

    def load_config(self, filename='config.enc'):
        """加载配置文件"""
        try:
            if os.path.exists(filename):
                with open(filename, 'r') as f:
                    encrypted_data = f.read()
                    data = json.loads(self.encryption.decrypt(encrypted_data))

                    # 加载全局设置
                    self.global_settings.update(data.get('settings', {}))

                    # 加载账号信息
                    accounts_data = data.get('accounts', {})
                    for name, acc_data in accounts_data.items():
                        account = AccountConfig(
                            secret_id=acc_data['secret_id'],
                            secret_key=acc_data['secret_key'],
                            domains={}
                        )

                        # 加载域名配置
                        for domain, configs in acc_data.get('domains', {}).items():
                            account.domains[domain] = []
                            for config in configs:
                                domain_config = DomainConfig(
                                    subdomain=config['subdomain'],
                                    record_type=config['record_type'],
                                    line=config['line'],
                                    enabled=config.get('enabled', True)
                                )
                                account.domains[domain].append(domain_config)

                        self.accounts[name] = account

        except Exception as e:
            logging.error(f"加载配置失败: {str(e)}")

    def save_config(self, filename='config.enc'):
        """保存配置到文件"""
        try:
            data = {
                'settings': self.global_settings,
                'accounts': {}
            }

            # 保存账号信息
            for name, account in self.accounts.items():
                acc_data = {
                    'secret_id': account.secret_id,
                    'secret_key': account.secret_key,
                    'domains': {}
                }

                # 保存域名配置
                for domain, configs in account.domains.items():
                    acc_data['domains'][domain] = [
                        {
                            'subdomain': config.subdomain,
                            'record_type': config.record_type,
                            'line': config.line,
                            'enabled': config.enabled
                        } for config in configs
                    ]

                data['accounts'][name] = acc_data

            # 加密并保存
            encrypted_data = self.encryption.encrypt(json.dumps(data))
            with open(filename, 'w') as f:
                f.write(encrypted_data)

            return True
        except Exception as e:
            logging.error(f"保存配置失败: {str(e)}")
            return False

    def add_account(self, name: str, secret_id: str, secret_key: str, domains: list) -> bool:
        """添加新账号"""
        if name in self.accounts:
            return False

        account = AccountConfig(
            secret_id=secret_id,
            secret_key=secret_key,
            domains={}
        )

        # 处理域名配置
        for domain_config in domains:
            domain = domain_config['domain']
            if domain not in account.domains:
                account.domains[domain] = []

            account.domains[domain].append(
                DomainConfig(
                    subdomain=domain_config['subdomain'],
                    record_type=domain_config['type'],
                    line=domain_config['line'],
                    enabled=True
                )
            )

        self.accounts[name] = account
        return True

    def update_account(self, name: str, secret_id: str, secret_key: str, domains: list) -> bool:
        """更新账号配置"""
        if name not in self.accounts:
            return False

        account = AccountConfig(
            secret_id=secret_id,
            secret_key=secret_key,
            domains={}
        )

        # 处理域名配置
        for domain_config in domains:
            domain = domain_config['domain']
            if domain not in account.domains:
                account.domains[domain] = []

            account.domains[domain].append(
                DomainConfig(
                    subdomain=domain_config['subdomain'],
                    record_type=domain_config['type'],
                    line=domain_config['line'],
                    enabled=domain_config['enabled']
                )
            )

        # 更新账号并保存配置
        self.accounts[name] = account
        self.save_config()
        return True

    def remove_account(self, name: str) -> bool:
        """删除账号"""
        if name in self.accounts:
            del self.accounts[name]
            self.save_config()
            return True
        return False

    def get_account(self, name: str) -> Optional[AccountConfig]:
        """获取账号配置"""
        return self.accounts.get(name)

    def get_all_accounts(self) -> Dict[str, AccountConfig]:
        """获取所有账号配置"""
        return self.accounts.copy()
