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


class DnsUpdateService(win32serviceutil.ServiceFramework):
    _svc_name_ = "DdnsUpdater"
    _svc_display_name_ = "天成锐视DNS自动更新服务"
    _svc_description_ = "自动更新动态IP到腾讯云域名解析DNS记录"

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.stop_event = win32event.CreateEvent(None, 0, 0, None)

        # 获取程序运行目录
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))

        # 初始化配置管理器时传入配置文件路径
        config_file = os.path.join(base_dir, 'config.enc')
        logging.info(f'配置文件路径: {config_file}')
        self.config_manager = ConfigManager()
        self.config_manager.load_config(config_file)

        self.dns_updater = DNSUpdater()
        self.running = True
        self.setup_logging()

    def setup_logging(self):
        # 获取程序运行目录
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))

        # 创建logs目录
        log_dir = os.path.join(base_dir, 'logs')
        os.makedirs(log_dir, exist_ok=True)

        # 使用固定基础日志文件名
        log_file = os.path.join(log_dir, 'service.log')

        # 配置日志处理器
        file_handler = TimedRotatingFileHandler(
            log_file,
            when='midnight',
            interval=1,
            backupCount=30,
            encoding='utf-8'
        )

        # 自定义日志文件命名函数
        def namer(default_name):
            date_str = default_name.split('.')[-1]
            try:
                date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                new_date_str = date_obj.strftime('%Y%m%d')
                return f"service_{new_date_str}.log"
            except:
                return default_name

        file_handler.namer = namer

        # 添加控制台输出处理器
        console_handler = logging.StreamHandler()

        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        # 获取根日志记录器并清除现有处理器
        logger = logging.getLogger()
        logger.handlers = []
        logger.setLevel(logging.INFO)
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

        logging.info('服务初始化完成')

        return logger

    async def update_all_records(self):
        try:
            logging.info('开始更新DNS记录')
            accounts = self.config_manager.get_all_accounts()
            logging.info(f'当前配置的账号数量: {len(accounts)}')

            for name, account in accounts.items():
                logging.info(f'处理账号: {name}')
                domain_count = sum(len(domains) for domains in account.domains.values())
                logging.info(f'账号 {name} 配置的域名数量: {domain_count}')

                for domain, configs in account.domains.items():
                    logging.info(f'处理域名: {domain}, 子域名数量: {len(configs)}')
                    for config in configs:
                        logging.info(f'更新记录: {config.subdomain}.{domain} ({config.record_type})')

                results = await self.dns_updater.update_records(account)
                for result in results:
                    if result.success:
                        logging.info(f"更新成功: {result.domain} - {result.subdomain} -> {result.ip}")
                    else:
                        logging.error(f"更新失败: {result.domain} - {result.subdomain}: {result.message}")

        except Exception as e:
            logging.error(f"更新过程发生错误: {str(e)}", exc_info=True)

    async def run_service(self):
        logging.info('服务开始运行')
        while self.running:
            try:
                await self.update_all_records()
                interval = self.config_manager.global_settings['update_interval']
                logging.info(f'等待 {interval} 分钟后进行下一次更新')

                # 分段检查停止信号
                for _ in range(interval * 60):
                    if not self.running:
                        break
                    await asyncio.sleep(1)

            except Exception as e:
                logging.error(f"服务运行错误: {str(e)}", exc_info=True)
                await asyncio.sleep(60)

    def SvcStop(self):
        logging.info('收到停止服务信号')
        self.running = False
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.stop_event)
        logging.info('服务停止完成')

    def SvcDoRun(self):
        try:
            logging.info('服务启动')
            asyncio.run(self.run_service())
        except Exception as e:
            logging.error(f'服务运行失败: {str(e)}', exc_info=True)
            raise


if __name__ == '__main__':
    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(DnsUpdateService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(DnsUpdateService)
