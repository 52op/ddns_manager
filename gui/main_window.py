import logging
import os
import sys
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler
import asyncio
import win32service
from PySide2.QtGui import QIcon, QPixmap, QPalette, QColor

from PySide2.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                               QPushButton, QTableWidget, QTableWidgetItem, QMenuBar,
                               QStatusBar, QLabel, QMessageBox, QMenu, QSystemTrayIcon, QApplication, QDialog)
from PySide2.QtCore import Qt, Signal, Slot, QThread, QEvent, QTimer

from core.service_controller import ServiceController
from .account_dialog import AccountDialog
from .log_viewer import LogViewerDialog
from .settings_dialog import SettingsDialog
from core.config_manager import ConfigManager
from core.dns_updater import DNSUpdater
from utils.validators import InputValidator
from ctypes import windll, c_int, byref, sizeof, c_uint
import platform
from loguru import logger


class UpdateThread(QThread):
    update_finished = Signal(list)  # 更新完成信号
    status_changed = Signal(str)  # 状态变化信号
    stopped = Signal()  # 添加停止信号

    def __init__(self, dns_updater, accounts, interval):
        super().__init__()
        self.dns_updater = dns_updater
        self.accounts = accounts
        self.interval = interval
        self.is_running = True
        self._loop = None

    def run(self):
        async def update():
            while self.is_running:
                try:
                    for account in self.accounts.values():
                        if not self.is_running:
                            return
                        results = await self.dns_updater.update_records(account)
                        self.update_finished.emit(results)

                    if self.is_running:
                        self.status_changed.emit(f"等待下次更新 ({self.interval}分钟)")
                        await asyncio.sleep(self.interval * 60)
                except asyncio.CancelledError:
                    return

        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._task = self._loop.create_task(update())
            self._loop.run_until_complete(self._task)
        except RuntimeError:
            # 忽略事件循环停止的错误
            pass
        finally:
            self._loop.close()
            self.stopped.emit()

    def stop(self):
        self.is_running = False
        if self._loop and self._loop.is_running():
            self._task.cancel()
            self._loop.stop()


class LoguruHandler(logging.Handler):
    def emit(self, record):
        # 将 logging 的日志记录转发到 loguru
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        logger.opt(depth=6, exception=record.exc_info).log(level, record.getMessage())


class MainWindow(QMainWindow):
    update_requested = Signal()

    def setup_logging(self):
        # 获取程序运行目录
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))

        # 创建 logs 目录
        log_dir = os.path.join(base_dir, 'logs')
        os.makedirs(log_dir, exist_ok=True)

        # 配置 loguru 日志处理器
        logger.add(
            os.path.join(log_dir, 'window_{time:YYYYMMDD}.log'),  # 日志文件名带当天日期
            rotation="00:00",  # 每天午夜轮换
            retention="30 days",  # 保留最近30天的日志
            format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
            level="INFO"
        )

        # 配置 logging
        logging.basicConfig(level=logging.INFO)
        # 手动添加 LoguruHandler 将 loguru 适配到 logging 模块
        logging.getLogger().addHandler(LoguruHandler())

        # 返回标准的 logging.Logger 对象
        return logging.getLogger()

    def __init__(self):
        super().__init__()
        self.base_dir = ''
        if getattr(sys, 'frozen', False):
            # 打包后的路径
            self.base_dir = sys._MEIPASS
        else:
            # 开发环境路径
            self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.icon_path = os.path.join(self.base_dir, 'resources', 'icon.ico')
        self.is_dark_theme = False
        self.config_manager = ConfigManager()
        self.dns_updater = DNSUpdater()
        self.service_controller = ServiceController()
        self.update_thread = None
        self.logger = self.setup_logging()
        self.dns_updater = DNSUpdater(logger=self.logger)   # 向dns_update传入logger
        self.setup_ui()
        self.refresh_table()
        self.setup_tray_icon()

    def setup_ui(self):
        self.setWindowTitle("DM动态IP自动解析工具-腾讯云DnsPod专用")

        self.setWindowIcon(QIcon(self.icon_path))
        self.setMinimumSize(800, 600)

        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # Toolbar
        toolbar = QHBoxLayout()
        self.add_account_btn = QPushButton("增加账号")
        self.edit_account_btn = QPushButton("编辑账号")
        self.settings_btn = QPushButton("设置")
        self.update_btn = QPushButton("开始更新")
        self.stop_update_btn = QPushButton("停止更新")
        self.stop_update_btn.setEnabled(False)  # 初始状态禁用

        toolbar.addWidget(self.add_account_btn)
        toolbar.addWidget(self.edit_account_btn)
        toolbar.addWidget(self.settings_btn)
        toolbar.addStretch()
        toolbar.addWidget(self.update_btn)
        toolbar.addWidget(self.stop_update_btn)

        layout.addLayout(toolbar)

        # Records table
        self.records_table = QTableWidget()
        self.records_table.setColumnCount(6)
        self.records_table.setHorizontalHeaderLabels([
            "账号", "主域名", "子域名", "记录类型(AAAA=IPV6)", "当前IP", "状态"
        ])
        # 设置固定宽度
        self.records_table.setColumnWidth(0, 80)  # 账号列宽100像素
        self.records_table.setColumnWidth(1, 100)  # 主域名列宽150像素
        self.records_table.setColumnWidth(2, 80)  # 子域名列宽100像素
        self.records_table.setColumnWidth(3, 150)  # 记录类型列宽150像素
        self.records_table.setColumnWidth(4, 120)  # 当前IP列宽120像素
        self.records_table.setColumnWidth(5, 150)  # 状态列宽150像素

        # 设置自动调整模式
        from PySide2.QtWidgets import QHeaderView
        header = self.records_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)  # 固定宽度
        header.setSectionResizeMode(5, QHeaderView.Stretch)  # 自动伸展
        header.setSectionResizeMode(5, QHeaderView.Interactive)  # 手动调整

        # 添加右键菜单
        self.records_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.records_table.customContextMenuRequested.connect(self.show_context_menu)

        layout.addWidget(self.records_table)

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        # 使用已存在的状态栏self.status_bar 添加服务状态标签到状态栏右侧
        self.service_status_label = QLabel()
        self.status_bar.addPermanentWidget(self.service_status_label)

        # 开始定时检查服务状态
        self.service_controller = ServiceController()
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_service_status)
        self.status_timer.start(5000)  # 每5秒更新一次状态
        self.update_service_status()  # 立即更新一次

        # Connect signals
        self.add_account_btn.clicked.connect(self.show_add_account_dialog)
        self.edit_account_btn.clicked.connect(self.show_edit_account_dialog)
        self.settings_btn.clicked.connect(self.show_settings_dialog)
        self.update_btn.clicked.connect(self.update_records)
        self.stop_update_btn.clicked.connect(self.stop_update)

        # 添加查看日志按钮
        self.view_log_btn = QPushButton("查看日志")
        self.view_log_btn.clicked.connect(self.show_log_viewer)
        toolbar.addWidget(self.view_log_btn)

        # 添加主题切换按钮到工具栏
        self.theme_button = QPushButton()
        self.update_theme_button()
        self.theme_button.setFixedSize(20, 20)
        toolbar.addWidget(self.theme_button)
        self.theme_button.clicked.connect(self.toggle_theme)

    def show_log_viewer(self):
        dialog = LogViewerDialog(self)
        dialog.exec_()

    def update_theme_button(self):
        if not self.is_dark_theme:
            self.theme_button.setText("☾")
            self.theme_button.setStyleSheet("QPushButton { color: black; }")
            self.theme_button.setToolTip("切换到深色模式")
        else:
            self.theme_button.setText("☀️")
            self.theme_button.setStyleSheet("QPushButton { color: white; }")
            self.theme_button.setToolTip("切换到浅色模式")

    def toggle_theme(self):
        self.is_dark_theme = not self.is_dark_theme
        if self.is_dark_theme:
            self.set_dark_theme(self)
        else:
            self.set_light_theme(self)
        self.update_theme_button()
        # 使用 QTimer 延迟更新
        QTimer.singleShot(0, self.force_update_windows)

    def force_update_windows(self):
        self.hide()
        self.show()

    def set_dark_theme(self, window):
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(53, 53, 53))
        palette.setColor(QPalette.WindowText, Qt.white)
        palette.setColor(QPalette.Base, QColor(25, 25, 25))
        palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
        palette.setColor(QPalette.ToolTipBase, Qt.white)
        palette.setColor(QPalette.ToolTipText, Qt.white)
        palette.setColor(QPalette.Text, Qt.white)
        palette.setColor(QPalette.Button, QColor(53, 53, 53))
        palette.setColor(QPalette.ButtonText, Qt.white)
        palette.setColor(QPalette.BrightText, Qt.red)
        palette.setColor(QPalette.Link, QColor(42, 130, 218))
        palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
        palette.setColor(QPalette.HighlightedText, Qt.black)
        QApplication.setPalette(palette)
        # 检测Windows版本
        win_version = platform.version().split('.')
        is_win11 = int(win_version[0]) >= 10 and int(win_version[2]) >= 22000

        hwnd = int(window.winId())
        # 基础深色模式设置
        DWMWA_USE_IMMERSIVE_DARK_MODE = 20
        windll.dwmapi.DwmSetWindowAttribute(
            hwnd,
            DWMWA_USE_IMMERSIVE_DARK_MODE,
            byref(c_int(1)),
            sizeof(c_int)
        )

        # Windows 11 特定设置
        if is_win11:
            DWMWA_CAPTION_COLOR = 35
            caption_color = 0x00000000  # ARGB 黑色
            windll.dwmapi.DwmSetWindowAttribute(
                hwnd,
                DWMWA_CAPTION_COLOR,
                byref(c_uint(caption_color)),
                sizeof(c_uint)
            )

    def set_light_theme(self, window):
        # 恢复默认调色板
        QApplication.setPalette(QApplication.style().standardPalette())

        # 检测Windows版本
        win_version = platform.version().split('.')
        is_win11 = int(win_version[0]) >= 10 and int(win_version[2]) >= 22000

        hwnd = int(window.winId())
        # 关闭深色模式
        DWMWA_USE_IMMERSIVE_DARK_MODE = 20
        windll.dwmapi.DwmSetWindowAttribute(
            hwnd,
            DWMWA_USE_IMMERSIVE_DARK_MODE,
            byref(c_int(0)),
            sizeof(c_int)
        )

        # Windows 11 特定设置
        if is_win11:
            DWMWA_CAPTION_COLOR = 35
            caption_color = 0xFFFFFFFF  # ARGB 白色
            windll.dwmapi.DwmSetWindowAttribute(
                hwnd,
                DWMWA_CAPTION_COLOR,
                byref(c_uint(caption_color)),
                sizeof(c_uint)
            )

    @Slot()
    def show_add_account_dialog(self):
        """显示添加账号对话框"""
        dialog = AccountDialog(self)
        if dialog.exec_():  # 注意这里是exec_
            account_data = dialog.get_account_data()
            # 检查账号是否已存在
            if account_data['name'] in self.config_manager.accounts:
                QMessageBox.warning(
                    self,
                    "账号已存在",
                    "已存在相同账号，如果有相同的id及key对应的账号想要添加不同域名，可到该账号下进行添加"
                )
                return
            # 添加账号到配置
            self.config_manager.add_account(
                account_data['name'],
                account_data['secret_id'],
                account_data['secret_key'],
                account_data['domains']  # 添加domains参数
            )
            # 保存配置
            self.config_manager.save_config()
            # 刷新表格显示
            self.refresh_table()

    @Slot()
    def update_records(self):
        """开始更新DNS记录"""
        if not InputValidator.check_accounts_valid(self.config_manager, self):
            return
        if self.check_service_running():
            QMessageBox.warning(
                self,
                "警告",
                "后台服务正在运行中，请先停止服务再进行手动更新。",
                QMessageBox.Ok
            )
            return

        self.update_btn.setEnabled(False)
        self.stop_update_btn.setEnabled(True)
        self.status_bar.showMessage("正在更新DNS记录...")

        interval = self.config_manager.global_settings.get('update_interval', 5)
        self.update_thread = UpdateThread(
            self.dns_updater,
            self.config_manager.accounts,
            interval
        )
        self.update_thread.update_finished.connect(self.update_table_with_results)
        self.update_thread.status_changed.connect(self.status_bar.showMessage)
        self.update_thread.stopped.connect(self.on_update_stopped)
        self.update_thread.start()

    def stop_update(self):
        """停止更新DNS记录"""
        if self.update_thread and self.update_thread.isRunning():
            self.update_thread.stop()
            self.status_bar.showMessage("正在停止更新...")
            self.update_btn.setEnabled(False)
            self.stop_update_btn.setEnabled(False)
            # 强制触发stopped信号
            self.on_update_stopped()

    def on_update_stopped(self):
        """更新停止后的处理"""
        self.update_btn.setEnabled(True)
        self.stop_update_btn.setEnabled(False)
        self.status_bar.showMessage("已停止更新", 5000)

    def update_table_with_results(self, results):
        """更新表格显示DNS更新结果"""
        for row in range(self.records_table.rowCount()):
            account = self.records_table.item(row, 0).text()
            domain = self.records_table.item(row, 1).text()
            subdomain = self.records_table.item(row, 2).text()

            # 查找对应的结果
            for result in results:
                if (result.domain == domain and
                        result.subdomain == subdomain):
                    # 更新IP和状态
                    self.records_table.setItem(
                        row, 4,
                        QTableWidgetItem(result.ip if result.success else "-")
                    )
                    status = "更新成功" if result.success else f"失败: {result.message}"
                    self.records_table.setItem(row, 5, QTableWidgetItem(status))
                    break

    def refresh_table(self):
        """刷新表格显示"""
        self.records_table.setRowCount(0)
        row = 0

        for account_name, account in self.config_manager.accounts.items():
            for domain, configs in account.domains.items():
                for config in configs:
                    self.records_table.insertRow(row)
                    # 账号列设置为不可编辑
                    account_item = QTableWidgetItem(account_name)
                    account_item.setFlags(account_item.flags() & ~Qt.ItemIsEditable)
                    self.records_table.setItem(row, 0, account_item)

                    self.records_table.setItem(row, 1, QTableWidgetItem(domain))
                    self.records_table.setItem(row, 2, QTableWidgetItem(config.subdomain))
                    self.records_table.setItem(row, 3, QTableWidgetItem(config.record_type))
                    self.records_table.setItem(row, 4, QTableWidgetItem("-"))
                    status = "启用" if config.enabled else "禁用"
                    self.records_table.setItem(row, 5, QTableWidgetItem(status))
                    row += 1

    @Slot()
    def show_edit_account_dialog(self):
        # 获取当前选中的账号
        selected_items = self.records_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "提示", "请先选择要编辑的账号")
            return

        # 获取所选行的行号
        row = selected_items[0].row()
        # 获取该行第一列的账号名
        account_name = self.records_table.item(row, 0).text()
        if account_name not in self.config_manager.accounts:
            QMessageBox.warning(self, "错误", "未找到选中的账号")
            return

        # 打开编辑对话框
        dialog = AccountDialog(self)
        dialog.load_account_data(account_name, self.config_manager.accounts[account_name])

        if dialog.exec():
            # 更新账号信息
            account_data = dialog.get_account_data()
            self.config_manager.update_account(
                account_name,
                account_data['secret_id'],
                account_data['secret_key'],
                account_data['domains']
            )
            self.refresh_table()

    @Slot()
    def show_settings_dialog(self):
        """显示设置对话框"""
        dialog = SettingsDialog(self.config_manager, self)
        if dialog.exec():
            # 保存设置
            self.config_manager.save_config('config.enc')
            # 如果服务正在运行，可能需要重启服务以应用新设置
            if self.service_controller.is_service_running():
                reply = QMessageBox.question(
                    self,
                    "重启服务",
                    "设置已更改，是否要重启服务以应用新设置？",
                    QMessageBox.Yes | QMessageBox.No
                )
                if reply == QMessageBox.Yes:
                    self.service_controller.stop_service()
                    self.service_controller.start_service()

    def show_context_menu(self, pos):
        """显示右键菜单"""
        menu = QMenu(self)
        edit_action = menu.addAction("编辑账号")
        delete_action = menu.addAction("删除账号")

        # 获取点击的行
        item = self.records_table.itemAt(pos)
        if item:
            action = menu.exec_(self.records_table.mapToGlobal(pos))
            row = item.row()
            account_name = self.records_table.item(row, 0).text()

            if action == edit_action:
                self.edit_account(account_name)
            elif action == delete_action:
                self.delete_account(account_name)

    def edit_account(self, account_name):
        """编辑账号"""
        if account_name in self.config_manager.accounts:
            dialog = AccountDialog(self)
            dialog.load_account_data(account_name, self.config_manager.accounts[account_name])
            if dialog.exec_():
                account_data = dialog.get_account_data()
                self.config_manager.update_account(
                    account_name,
                    account_data['secret_id'],
                    account_data['secret_key'],
                    account_data['domains']
                )
                self.refresh_table()

    def delete_account(self, account_name):
        """删除账号"""
        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除账号 {account_name} 吗？\n点击确定，删除{account_name}对应的所有域名",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.config_manager.remove_account(account_name)
            self.refresh_table()

    def check_service_running(self) -> bool:
        import win32serviceutil
        try:
            status = win32serviceutil.QueryServiceStatus('DdnsUpdater')
            return status[1] == win32service.SERVICE_RUNNING
        except:
            return False

    def update_service_status(self):
        try:
            if not self.service_controller.is_service_installed():
                self.service_status_label.setText("后台服务未安装")
                self.service_status_label.setStyleSheet("color: red")
            elif self.service_controller.is_service_running():
                self.service_status_label.setText("后台服务运行中")
                self.service_status_label.setStyleSheet("color: green")
            else:
                self.service_status_label.setText("后台服务未启动")
                self.service_status_label.setStyleSheet("color: black")
        except Exception as e:
            self.logger.error(f"更新服务状态出错: {str(e)}")

    def setup_tray_icon(self):
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon(self.icon_path))
        self.tray_icon.setToolTip("DM动态IP自动解析工具")  # 添加提示文本

        # 绑定托盘图标点击事件
        self.tray_icon.activated.connect(self.tray_icon_activated)

        # 创建托盘菜单
        tray_menu = QMenu()

        # 显示主窗口
        show_action = tray_menu.addAction("显示主窗口")
        show_action.triggered.connect(self.show)

        # 关于程序
        about_action = tray_menu.addAction("关于程序")
        about_action.triggered.connect(self.show_about_dialog)

        tray_menu.addSeparator()

        # 退出程序
        quit_action = tray_menu.addAction("退出程序")
        quit_action.triggered.connect(self.quit_application)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()

    def tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick or reason == QSystemTrayIcon.Trigger:
            self.show()
            self.setWindowState(Qt.WindowActive)

    def show_about_dialog(self):
        # 显示主窗口，确保有父窗口
        # self.show()
        # self.setWindowState(Qt.WindowActive)

        dialog = AboutDialog(self)
        dialog.exec_()

    def closeEvent(self, event):
        event.ignore()
        self.hide()
        self.tray_icon.showMessage(
            "提示",
            "程序已最小化到系统托盘",
            QSystemTrayIcon.Information,
            2000
        )

    def changeEvent(self, event):
        if event.type() == QEvent.WindowStateChange:
            if self.windowState() & Qt.WindowMinimized:
                event.ignore()
                self.hide()
                self.tray_icon.showMessage(
                    "提示",
                    "程序已最小化到系统托盘",
                    QSystemTrayIcon.Information,
                    2000
                )

    def quit_application(self):
        self.tray_icon.hide()
        QApplication.quit()


class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("关于程序")
        # 设置对话框关闭时不影响父窗口 不加这个主窗口隐藏状态时，关掉关于窗口，主程序也退出了
        self.setAttribute(Qt.WA_QuitOnClose, False)
        # 从父窗口获取 base_dir
        self.base_dir = self.parent().base_dir
        self.setup_ui()
        self.apply_theme()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # 添加图片
        label = QLabel()
        zs_img_path = os.path.join(self.base_dir, 'resources', 'zs.png')
        pixmap = QPixmap(zs_img_path)
        label.setPixmap(pixmap)
        layout.addWidget(label)

        # 添加说明文字
        text1 = QLabel(
            "如果喜欢，欢迎打赏支持，万分感谢！\n\n"
            "DM动态IP自动解析工具\n"
        )
        text2 = QLabel(
            "功能: \n自动更新动态IP到腾讯云域名解析DNS记录，\n支持IPv4和IPv6，支持多账号多域名，支持服务方式运行\n"
            "反馈： letvar@qq.com(秒回)"
        )
        text1.setAlignment(Qt.AlignCenter)
        layout.addWidget(text1)
        text2.setAlignment(Qt.AlignLeft)
        layout.addWidget(text2)

        self.setLayout(layout)

    def apply_theme(self):
        if self.parent().is_dark_theme:
            self.parent().set_dark_theme(self)
        else:
            self.parent().set_light_theme(self)