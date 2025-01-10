from typing import Optional, List, Dict
from tencentcloud.common import credential
from tencentcloud.dnspod.v20210323 import dnspod_client, models
import logging
from dataclasses import dataclass
from core.config_manager import AccountConfig, DomainConfig
from core.ip_resolver import IPResolver
import ujson as json


@dataclass
class UpdateResult:
    success: bool
    message: str
    ip: str
    domain: str
    subdomain: str


class DNSUpdater:
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.ip_resolver = IPResolver()
        self._clients: Dict[str, dnspod_client.DnspodClient] = {}
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/91.0.864.59'
        ]
        self.logger = logger or logging.getLogger(__name__)
        self.ip_resolver = IPResolver(logger=self.logger)   # 向ip_resolver传入logger

    def _get_client(self, secret_id: str, secret_key: str) -> dnspod_client.DnspodClient:
        key = f"{secret_id}:{secret_key}"
        if key not in self._clients:
            cred = credential.Credential(secret_id, secret_key)
            self._clients[key] = dnspod_client.DnspodClient(cred, "")
        return self._clients[key]

    async def update_records(self, account: AccountConfig) -> List[UpdateResult]:
        results = []
        self.logger.info(f"开始更新DNS记录")
        client = self._get_client(account.secret_id, account.secret_key)

        ipv4 = await self.ip_resolver.get_ipv4()
        # self.logger.info(f"获取到IPv4地址: {ipv4}")
        ipv6 = await self.ip_resolver.get_ipv6()
        # self.logger.info(f"获取到IPv6地址: {ipv6}")

        for domain, configs in account.domains.items():
            self.logger.info(f"处理域名: {domain}")
            for config in configs:
                self.logger.info(f"处理记录: {config.subdomain}.{domain} ({config.record_type})")

                if not config.enabled:
                    self.logger.info(f"记录 {config.subdomain}.{domain} 已禁用，跳过更新")
                    results.append(UpdateResult(
                        success=False,
                        message="记录已禁用",
                        ip="127.0.0.1",
                        domain=domain,
                        subdomain=config.subdomain,
                    ))
                    continue

                ip = ipv4 if config.record_type == 'A' else ipv6
                if not ip:
                    self.logger.error(f"无法获取 {config.record_type} 地址")
                    results.append(UpdateResult(
                        False,
                        f"无法获取 {config.record_type} 地址",
                        "",
                        domain,
                        config.subdomain
                    ))
                    continue

                try:
                    result = await self._update_single_record(
                        client, domain, config, ip
                    )
                    results.append(result)
                    self.logger.info(f"更新结果: {result.domain} - {result.subdomain} -> {result.ip} ({result.message})")
                except Exception as e:
                    self.logger.error(f"更新失败: {domain} - {config.subdomain}: {str(e)}")
                    results.append(UpdateResult(
                        False,
                        str(e),
                        ip,
                        domain,
                        config.subdomain
                    ))

        return results

    async def _update_single_record(
            self,
            client: dnspod_client.DnspodClient,
            domain: str,
            config: DomainConfig,
            ip: str
    ) -> UpdateResult:
        try:
            # self.logger.info(f"查询记录: {config.subdomain}.{domain}")
            req = models.DescribeRecordListRequest()
            params = {
                "Domain": domain,
                "Subdomain": config.subdomain,
                "RecordType": config.record_type
            }
            req.from_json_string(json.dumps(params))
            resp = client.DescribeRecordList(req)

            if not resp.RecordList:
                self.logger.info(f"创建新记录: {config.subdomain}.{domain} -> {ip}")
                create_req = models.CreateRecordRequest()
                create_params = {
                    "Domain": domain,
                    "SubDomain": config.subdomain,
                    "RecordType": config.record_type,
                    "RecordLine": config.line,
                    "Value": ip
                }
                create_req.from_json_string(json.dumps(create_params))
                client.CreateRecord(create_req)
                return UpdateResult(
                    True,
                    "创建记录成功",
                    ip,
                    domain,
                    config.subdomain
                )

            record = resp.RecordList[0]
            if record.Value == ip:
                self.logger.info(f"记录无需更新: {config.subdomain}.{domain} = {ip}")
                return UpdateResult(
                    True,
                    "记录是最新的",
                    ip,
                    domain,
                    config.subdomain
                )

            self.logger.info(f"更新记录: {config.subdomain}.{domain} -> {ip}")
            modify_req = models.ModifyRecordRequest()
            modify_params = {
                "Domain": domain,
                "RecordId": record.RecordId,
                "SubDomain": config.subdomain,
                "RecordType": config.record_type,
                "RecordLine": config.line,
                "Value": ip
            }
            modify_req.from_json_string(json.dumps(modify_params))
            client.ModifyRecord(modify_req)

            return UpdateResult(
                True,
                "记录更新成功",
                ip,
                domain,
                config.subdomain
            )

        except Exception as e:
            self.logger.error(f"DNS更新出错: {str(e)}")
            raise
