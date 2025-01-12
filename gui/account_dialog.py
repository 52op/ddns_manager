import asyncio
import os
import sys
import webbrowser

from PySide2.QtGui import QIcon
from PySide2.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QLineEdit,
                               QPushButton, QTableWidget, QTableWidgetItem,
                               QHBoxLayout, QComboBox, QCheckBox, QMessageBox)
from PySide2.QtCore import Qt

from core.config_manager import AccountConfig
from core.dns_updater import DNSUpdater
from .base_dialog import ProtectedDialog


class AccountDialog(ProtectedDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.apply_theme()
        self.logger = self.parent().logger
        # 添加表格项变化信号连接
        self.domains_table.itemChanged.connect(self.on_domain_item_changed)

    def setup_ui(self):
        self.setWindowTitle("账号设置")
        # 设置窗口帮助按钮
        self.setWindowFlags(self.windowFlags() | Qt.WindowContextHelpButtonHint)

        # 设置窗口固定宽度
        # self.setFixedWidth(800)  # 设置固定宽度为800像素

        # 或者设置窗口最小和最大宽度
        self.setMinimumWidth(500)  # 最小宽度
        self.setMaximumWidth(600)  # 最大宽度
        layout = QVBoxLayout(self)

        # Account details form
        form = QFormLayout()
        self.name_edit = QLineEdit()
        self.secret_id_edit = QLineEdit()
        self.secret_key_edit = QLineEdit()
        self.secret_key_edit.setEchoMode(QLineEdit.Password)

        form.addRow("账号:", self.name_edit)
        # 添加账号输入框的提示
        self.name_edit.setPlaceholderText("请输入账号名称(用于区分不同组id和key)")
        # 设置账号输入框的帮助文本
        name_edit_help_text = "账号自定义，用于记忆与区分不同的id及key，因为一组id及key能操作的域名肯定是在同一个账号下的。"
        self.name_edit.setWhatsThis(name_edit_help_text)
        form.addRow("Secret ID:", self.secret_id_edit)
        secret_id_edit_help_text = "id及key，腾讯云平台申请，如不知道网址，可点击窗口上的申请secret。"
        form.addRow("Secret Key:", self.secret_key_edit)
        self.secret_id_edit.setWhatsThis(secret_id_edit_help_text)
        self.secret_key_edit.setWhatsThis(secret_id_edit_help_text)
        layout.addLayout(form)
        # 添加帮助按钮
        reg_secret_btn = QPushButton("申请Secret", self)
        reg_secret_btn.setFixedSize(80, 20)
        reg_secret_btn.clicked.connect(self.open_reg_secret)
        form.addWidget(reg_secret_btn)

        # Domains table
        self.domains_table = QTableWidget()
        self.domains_table.setColumnCount(5)  # 增加一列用于启用/禁用
        self.domains_table.setHorizontalHeaderLabels([
            "主域名", "子域名", "记录类型", "线路", "状态"
        ])
        # 设置表头提示信息
        header = self.domains_table.horizontalHeader()
        header.setToolTip("A记录=IPV4地址，AAAA记录=IPV6地址")
        # 或者使用QTableWidgetItem来设置每列的表头提示
        self.domains_table.horizontalHeaderItem(0).setToolTip("输入主域名，如: example.com")
        self.domains_table.horizontalHeaderItem(1).setToolTip("输入子域名，如: www")
        self.domains_table.horizontalHeaderItem(2).setToolTip("A记录=IPV4地址，AAAA记录=IPV6地址")
        self.domains_table.horizontalHeaderItem(3).setToolTip("如无特殊要求，默认就好")
        self.domains_table.horizontalHeaderItem(4).setToolTip("如果暂时不想更新这条域名，去掉勾就好")

        layout.addWidget(self.domains_table)

        # Domain controls
        domain_controls = QHBoxLayout()
        self.add_domain_btn = QPushButton("增加域名")
        self.remove_domain_btn = QPushButton("删除域名")
        domain_controls.addWidget(self.add_domain_btn)
        domain_controls.addWidget(self.remove_domain_btn)
        layout.addLayout(domain_controls)

        # Dialog buttons
        buttons = QHBoxLayout()
        self.save_btn = QPushButton("保存")
        self.cancel_btn = QPushButton("取消")
        buttons.addWidget(self.save_btn)
        buttons.addWidget(self.cancel_btn)
        layout.addLayout(buttons)

        # Connect signals
        self.save_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)
        self.add_domain_btn.clicked.connect(self.add_domain_row)
        self.remove_domain_btn.clicked.connect(self.remove_domain)

    def apply_theme(self):
        if self.parent().is_dark_theme:
            self.parent().set_dark_theme(self)
        else:
            self.parent().set_light_theme(self)

    def open_reg_secret(self):
        """打开申请secret链接"""
        webbrowser.open('https://console.cloud.tencent.com/cam/capi')
        return

    def add_domain_row(self):
        """添加域名"""
        row = self.domains_table.rowCount()
        self.domains_table.insertRow(row)
        # 为第三列设置提示文本
        record_item = QTableWidgetItem("")
        record_item.setToolTip("如需更新ipv6请选AAAA")
        self.domains_table.setItem(row, 2, record_item)

        # 添加各列的控件
        self.domains_table.setItem(row, 0, QTableWidgetItem(""))
        self.domains_table.setItem(row, 1, QTableWidgetItem(""))

        type_combo = QComboBox()
        type_combo.addItems(["A", "AAAA"])
        self.domains_table.setCellWidget(row, 2, type_combo)

        line_combo = QComboBox()
        line_combo.addItems(["默认", "电信", "联通", "移动"])
        self.domains_table.setCellWidget(row, 3, line_combo)

        enabled_check = QCheckBox()
        enabled_check.setChecked(True)
        self.domains_table.setCellWidget(row, 4, enabled_check)

    def on_domain_item_changed(self, item):
        """处理域名表格项变化"""
        row = item.row()
        column = item.column()

        # 只检查域名和子域名列
        if column in [0, 1]:
            domain_item = self.domains_table.item(row, 0)
            subdomain_item = self.domains_table.item(row, 1)

            if domain_item and subdomain_item:
                domain = domain_item.text()
                subdomain = subdomain_item.text()

                if domain and subdomain:
                    self.check_domain_duplicate(row, domain, subdomain)

    def check_domain_duplicate(self, current_row, domain, subdomain):
        """检查域名是否重复"""
        for row in range(self.domains_table.rowCount()):
            if row == current_row:
                continue

            existing_domain_item = self.domains_table.item(row, 0)
            existing_subdomain_item = self.domains_table.item(row, 1)

            if existing_domain_item and existing_subdomain_item:
                existing_domain = existing_domain_item.text()
                existing_subdomain = existing_subdomain_item.text()

                if domain == existing_domain and subdomain == existing_subdomain:
                    QMessageBox.warning(
                        self,
                        "错误",
                        f"域名 {domain} 下已存在子域名 {subdomain}"
                    )
                    # 清空当前输入
                    # self.domains_table.item(current_row, 0).setText("")   # 只清下面的子域名
                    self.domains_table.item(current_row, 1).setText("")
                    break

    def get_account_data(self):
        """获取账号数据"""
        domains = []
        for row in range(self.domains_table.rowCount()):
            domain = self.domains_table.item(row, 0).text()
            subdomain = self.domains_table.item(row, 1).text()
            type_combo = self.domains_table.cellWidget(row, 2)
            line_combo = self.domains_table.cellWidget(row, 3)
            enabled_check = self.domains_table.cellWidget(row, 4)

            domains.append({
                'domain': domain,
                'subdomain': subdomain,
                'type': type_combo.currentText(),
                'line': line_combo.currentText(),
                'enabled': enabled_check.isChecked()
            })

        return {
            'name': self.name_edit.text(),
            'secret_id': self.secret_id_edit.text(),
            'secret_key': self.secret_key_edit.text(),
            'domains': domains
        }

    def load_account_data(self, name: str, account_config: AccountConfig):
        """加载现有账号数据"""
        self.name_edit.setText(name)
        self.name_edit.setEnabled(False)
        self.secret_id_edit.setText(account_config.secret_id)
        self.secret_key_edit.setText(account_config.secret_key)

        # 清空并重新加载域名表格
        self.domains_table.setRowCount(0)
        for domain, configs in account_config.domains.items():
            for config in configs:
                row = self.domains_table.rowCount()
                self.domains_table.insertRow(row)
                self.domains_table.setItem(row, 0, QTableWidgetItem(domain))
                self.domains_table.setItem(row, 1, QTableWidgetItem(config.subdomain))

                type_combo = QComboBox()
                type_combo.addItems(["A", "AAAA"])
                type_combo.setCurrentText(config.record_type)

                line_combo = QComboBox()
                line_combo.addItems(["默认", "电信", "联通", "移动"])
                line_combo.setCurrentText(config.line)

                enabled_check = QCheckBox()
                enabled_check.setChecked(config.enabled)

                self.domains_table.setCellWidget(row, 2, type_combo)
                self.domains_table.setCellWidget(row, 3, line_combo)
                self.domains_table.setCellWidget(row, 4, enabled_check)

    async def delete_dns_record_async(self, client, domain, subdomain, record_type):
        """异步删除DNS记录"""
        dns_updater = DNSUpdater(logger=self.logger)
        await dns_updater.delete_dns_records(client, domain, subdomain, record_type)

    def remove_domain(self):
        """删除选中的域名及其DNS记录"""
        current_row = self.domains_table.currentRow()
        if current_row >= 0:
            domain = self.domains_table.item(current_row, 0).text()
            subdomain = self.domains_table.item(current_row, 1).text()
            record_type = self.domains_table.cellWidget(current_row, 2).currentText()

            reply = QMessageBox.question(
                self,
                "确认删除",
                f"确定要删除域名记录 {subdomain}.{domain} ({record_type}) 吗？\n"
                f"这将同时删除腾讯云上的解析记录",
                QMessageBox.Yes | QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                try:
                    # 获取账号信息
                    secret_id = self.secret_id_edit.text()
                    secret_key = self.secret_key_edit.text()

                    # 创建DNS客户端
                    from tencentcloud.dnspod.v20210323 import dnspod_client
                    from tencentcloud.common import credential

                    cred = credential.Credential(secret_id, secret_key)
                    client = dnspod_client.DnspodClient(cred, "")

                    # 使用事件循环删除记录
                    loop = asyncio.get_event_loop()
                    loop.run_until_complete(
                        self.delete_dns_record_async(client, domain, subdomain, record_type)
                    )

                except Exception as e:
                    self.logger.error(f"删除腾讯云域名记录时出错: {str(e)}")

                finally:
                    # 从表格中删除
                    self.domains_table.removeRow(current_row)
                    QMessageBox.information(
                        self,
                        "删除成功",
                        f"本地域名记录 {subdomain}.{domain} 已删除,保存生效"
                    )
