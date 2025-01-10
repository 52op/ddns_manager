import os
import sys

from PySide2.QtCore import QEvent
from PySide2.QtGui import QIcon, Qt
from PySide2.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QCheckBox,
                               QSpinBox, QListWidget, QPushButton, QHBoxLayout,
                               QInputDialog, QMessageBox, QLabel, QLineEdit)
from core.service_controller import ServiceController
from utils.validators import InputValidator
from .base_dialog import ProtectedDialog


class SettingsDialog(ProtectedDialog):
    def __init__(self, config_manager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.service_controller = ServiceController()
        self.setup_ui()
        self.apply_theme()
        self.load_settings()

    def setup_ui(self):
        self.setWindowTitle("全局设置")

        layout = QVBoxLayout(self)

        # General settings
        form = QFormLayout()
        self.startup_check = QCheckBox("开机启动本程序")
        self.update_interval = QSpinBox()
        self.update_interval.setRange(1, 1440)
        self.update_interval.setSuffix(" 分钟")

        form.addRow("开机启动:", self.startup_check)
        form.addRow("更新间隔:", self.update_interval)

        # 密码保护设置
        self.password_protect_check = QCheckBox("启用密码保护:[设置,账号编辑],默认密码:letvar")
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setEnabled(False)

        form.addRow("密码保护:", self.password_protect_check)
        form.addRow("设置密码:", self.password_input)

        layout.addLayout(form)

        # IP Sources
        layout.addWidget(QLabel("IPv4地址获取接口:"))
        self.ip_sources_list = QListWidget()
        layout.addWidget(self.ip_sources_list)

        # IP source controls
        ip_controls = QHBoxLayout()
        self.add_source_btn = QPushButton("增加接口")
        self.remove_source_btn = QPushButton("移除接口")
        ip_controls.addWidget(self.add_source_btn)
        ip_controls.addWidget(self.remove_source_btn)
        layout.addLayout(ip_controls)

        # Service controls
        service_controls = QHBoxLayout()
        self.install_service_btn = QPushButton("安装服务")
        self.uninstall_service_btn = QPushButton("卸载服务")
        self.start_service_btn = QPushButton("启动服务")
        self.stop_service_btn = QPushButton("停止服务")

        service_controls.addWidget(self.install_service_btn)
        service_controls.addWidget(self.uninstall_service_btn)
        service_controls.addWidget(self.start_service_btn)
        service_controls.addWidget(self.stop_service_btn)
        layout.addLayout(service_controls)

        # Dialog buttons
        buttons = QHBoxLayout()
        self.save_btn = QPushButton("保存")
        self.cancel_btn = QPushButton("取消")
        buttons.addWidget(self.save_btn)
        buttons.addWidget(self.cancel_btn)
        layout.addLayout(buttons)

        self.connect_signals()

    def apply_theme(self):
        if self.parent().is_dark_theme:
            self.parent().set_dark_theme(self)
        else:
            self.parent().set_light_theme(self)

    def connect_signals(self):
        self.add_source_btn.clicked.connect(self.add_ip_source)
        self.remove_source_btn.clicked.connect(self.remove_ip_source)
        self.save_btn.clicked.connect(self.save_settings)
        self.cancel_btn.clicked.connect(self.reject)

        self.install_service_btn.clicked.connect(self.install_service)
        self.uninstall_service_btn.clicked.connect(self.uninstall_service)
        self.start_service_btn.clicked.connect(self.start_service)
        self.stop_service_btn.clicked.connect(self.stop_service)
        self.startup_check.stateChanged.connect(self.startup_changed)
        self.password_protect_check.stateChanged.connect(self.toggle_password_input)

    def toggle_password_input(self, state):
        """切换密码输入框的启用状态"""
        self.password_input.setEnabled(state == Qt.Checked)

    def startup_changed(self, state):
        if state:
            success, message = self.service_controller.enable_startup()
            QMessageBox.information(self, "操作结果", message)
        else:
            success, message = self.service_controller.disable_startup()
            QMessageBox.warning(self, "操作结果", message)

        if not success:
            QMessageBox.warning(self, "错误", message)

    def load_settings(self):
        settings = self.config_manager.global_settings
        # self.startup_check.setChecked(settings['startup_enabled'])
        # 从注册表获取实际的开机启动状态
        self.startup_check.setChecked(self.service_controller.is_startup_enabled())
        self.update_interval.setValue(settings.get('update_interval', 5))

        self.ip_sources_list.clear()
        self.ip_sources_list.addItems(settings['ip_sources'])

        self.update_service_buttons()

        # 加载密码保护设置
        self.password_protect_check.setChecked(
            self.config_manager.global_settings.get('password_protected', False)
        )
        self.password_input.setText(
            self.config_manager.global_settings.get('settings_password', 'letvar')
        )
        self.password_input.setEnabled(self.password_protect_check.isChecked())

    def update_service_buttons(self):
        is_installed = self.service_controller.is_service_installed()
        is_running = self.service_controller.is_service_running()

        self.install_service_btn.setEnabled(not is_installed)
        self.uninstall_service_btn.setEnabled(is_installed)
        self.start_service_btn.setEnabled(is_installed and not is_running)
        self.stop_service_btn.setEnabled(is_installed and is_running)

    def add_ip_source(self):
        """添加IP获取源"""
        source, ok = QInputDialog.getText(
            self,
            "添加IP源",
            "请输入IP获取源URL:",
            text="https://"
        )

        if ok and source:
            # 验证URL格式
            if source.startswith(('http://', 'https://')):
                # 检查是否已存在
                items = [self.ip_sources_list.item(i).text()
                         for i in range(self.ip_sources_list.count())]
                if source not in items:
                    self.ip_sources_list.addItem(source)
                    # 更新配置
                    self.config_manager.global_settings['ip_sources'].append(source)
            else:
                QMessageBox.warning(
                    self,
                    "格式错误",
                    "IP源必须以http://或https://开头"
                )

    def remove_ip_source(self):
        """移除选中的IP源"""
        current_item = self.ip_sources_list.currentItem()
        if current_item:
            source = current_item.text()
            row = self.ip_sources_list.row(current_item)
            self.ip_sources_list.takeItem(row)

            # 从配置中移除
            if source in self.config_manager.global_settings['ip_sources']:
                self.config_manager.global_settings['ip_sources'].remove(source)
        else:
            QMessageBox.information(
                self,
                "提示",
                "请先选择要删除的IP源"
            )

    def save_settings(self):
        """保存所有设置"""
        # 保存开机启动设置
        self.config_manager.global_settings['startup_enabled'] = self.startup_check.isChecked()

        # 保存更新间隔
        self.config_manager.global_settings['update_interval'] = self.update_interval.value()

        # 保存IP源列表
        ip_sources = [self.ip_sources_list.item(i).text()
                      for i in range(self.ip_sources_list.count())]
        self.config_manager.global_settings['ip_sources'] = ip_sources

        # 处理开机启动
        if self.startup_check.isChecked():
            self.service_controller.enable_startup()
        else:
            self.service_controller.disable_startup()

        # 保存密码保护设置
        self.config_manager.global_settings['password_protected'] = self.password_protect_check.isChecked()
        if self.password_protect_check.isChecked():
            new_password = self.password_input.text().strip()
            if not new_password:
                new_password = 'letvar'
            self.config_manager.global_settings['settings_password'] = new_password

        # 关闭对话框
        self.accept()

    def install_service(self):
        """安装Windows服务"""
        success, message = self.service_controller.install_service()
        if success:
            QMessageBox.information(self, "成功", "服务安装成功")
            self.update_service_buttons()
        else:
            QMessageBox.warning(self, "错误", f"服务安装失败: {message}")

    def uninstall_service(self):
        """卸载Windows服务"""
        success, message = self.service_controller.uninstall_service()
        if success:
            QMessageBox.information(self, "成功", "服务卸载成功")
            self.update_service_buttons()
        else:
            QMessageBox.warning(self, "错误", f"服务卸载失败: {message}")

    def start_service(self):
        """启动服务"""
        if not InputValidator.check_accounts_valid(self.config_manager, self):
            return
        success, message = self.service_controller.start_service()
        if success:
            QMessageBox.information(self, "成功", "服务启动成功")
            self.update_service_buttons()
        else:
            QMessageBox.warning(self, "错误", f"服务启动失败: {message}")

    def stop_service(self):
        """停止服务"""
        success, message = self.service_controller.stop_service()
        if success:
            QMessageBox.information(self, "成功", "服务停止成功")
            self.update_service_buttons()
        else:
            QMessageBox.warning(self, "错误", f"服务停止失败: {message}")
