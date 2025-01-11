import sys
import os
from datetime import datetime
import win32serviceutil
import win32service
import win32event
import servicemanager
import asyncio
import logging
from logging.handlers import TimedRotatingFileHandler
from core.config_manager import ConfigManager
from core.dns_updater import DNSUpdater
from loguru import logger


class LoguruHandler(logging.Handler):
    def emit(self, record):
        # 将 logging 的日志记录转发到 loguru
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        logger.opt(depth=6, exception=record.exc_info).log(level, record.getMessage())


class DnsUpdateService(win32serviceutil.ServiceFramework):
    _svc_name_ = "DdnsUpdater"
    _svc_display_name_ = "Ddns_Manager自动更新域名解析服务"
    _svc_description_ = "自动更新动态IP到腾讯云域名解析DNS记录"

    def get_app_path(self):
        # 获取程序运行目录
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
        return base_dir

    def setup_logging(self):
        try:
            # 创建 logs 目录
            log_dir = os.path.join(self.get_app_path(), 'logs')
            os.makedirs(log_dir, exist_ok=True)

            # 移除所有已存在的处理器
            logger.remove()

            # 添加文件处理器
            logger.add(
                os.path.join(log_dir, 'service_{time:YYYYMMDD}.log'),
                rotation="00:00",
                retention="30 days",
                format="{time:YYYY-MM-DD HH:mm:ss}| PID:{process} | {level} | {message}",
                level="INFO",
                enqueue=True,  # 确保线程安全
                serialize=False,  # 关闭序列化 开启会以 JSON 格式记录所有详细信息
                backtrace=True,  # 添加异常追踪
                diagnose=True  # 添加诊断信息
            )

            # 配置 logging 基础设置
            logging.basicConfig(level=logging.INFO)
            # 添加 LoguruHandler
            logging_logger = logging.getLogger()
            if not any(isinstance(handler, LoguruHandler) for handler in logging_logger.handlers):
                logging_logger.addHandler(LoguruHandler())

            return logger

        except Exception as e:
            servicemanager.LogErrorMsg(f"日志系统初始化失败: {str(e)}")
            raise

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.stop_event = win32event.CreateEvent(None, 0, 0, None)

        # 初始化配置管理器时传入配置文件路径
        config_file = os.path.join(self.get_app_path(), 'config.enc')
        logging.info(f'配置文件路径: {config_file}')
        self.config_manager = ConfigManager()
        self.config_manager.load_config(config_file)

        self.dns_updater = DNSUpdater()
        self.running = True

        # 在服务实际运行前初始化日志系统
        self.logger = self.setup_logging()

    async def update_all_records(self):
        try:
            accounts = self.config_manager.get_all_accounts()
            self.logger.info(f'开始更新DNS记录，当前配置的账号数量: {len(accounts)}')

            if len(accounts) < 1:
                self.logger.info(f'当前配置的账号数量为: {len(accounts)}，跳出更新')
                return

            for name, account in accounts.items():
                self.logger.info(f'处理账号: {name}')
                domain_count = sum(len(domains) for domains in account.domains.values())
                self.logger.info(f'账号 {name} 配置的域名数量: {domain_count}')

                for domain, configs in account.domains.items():
                    self.logger.info(f'处理域名: {domain}, 子域名数量: {len(configs)}')
                    for config in configs:
                        self.logger.info(f'更新记录: {config.subdomain}.{domain} ({config.record_type})')

                results = await self.dns_updater.update_records(account)
                for result in results:
                    if result.success:
                        self.logger.info(f"更新成功: {result.domain} - {result.subdomain} -> {result.ip}")
                    else:
                        self.logger.error(f"更新失败: {result.domain} - {result.subdomain}: {result.message}")

        except Exception as e:
            self.logger.error(f"更新过程发生错误: {str(e)}", exc_info=True)

    async def run_service(self):
        self.logger.info('服务开始运行')
        while self.running:
            try:
                await self.update_all_records()
                interval = self.config_manager.global_settings['update_interval']
                self.logger.info(f'等待 {interval} 分钟后进行下一次更新')

                # 分段检查停止信号
                for _ in range(interval * 60):
                    if not self.running:
                        break
                    await asyncio.sleep(1)

            except Exception as e:
                self.logger.error(f"服务运行错误: {str(e)}", exc_info=True)
                await asyncio.sleep(60)

    def SvcStop(self):
        self.logger.info('收到停止服务信号')
        self.running = False
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.stop_event)
        self.logger.info('服务停止完成')

    def SvcDoRun(self):
        try:
            self.logger.info('服务启动，日志系统初始化完成')
            asyncio.run(self.run_service())
        except Exception as e:
            self.logger.error(f'服务运行失败: {str(e)}', exc_info=True)
            raise


if __name__ == '__main__':
    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(DnsUpdateService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(DnsUpdateService)
