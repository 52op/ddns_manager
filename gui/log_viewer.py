import sys

from PySide2.QtGui import QIcon
from PySide2.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                               QLineEdit, QDateEdit, QTextEdit, QComboBox, QLabel)
from PySide2.QtCore import Qt, QDate
import os
import glob
from datetime import datetime


class LogViewerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("日志查看器")
        self.resize(800, 600)
        self.setup_ui()
        self.apply_theme()
        self.search_logs()

    def setup_ui(self):
        if getattr(sys, 'frozen', False):
            # 打包后的路径
            base_dir = sys._MEIPASS
        else:
            # 开发环境路径
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        icon_path = os.path.join(base_dir, 'resources', 'icon.ico')
        self.setWindowIcon(QIcon(icon_path))

        layout = QVBoxLayout()

        # 搜索条件区域
        search_layout = QHBoxLayout()

        # 日志类型选择
        self.log_type = QComboBox()
        self.log_type.addItems(["所有日志", "服务日志", "窗口日志"])
        search_layout.addWidget(QLabel("日志类型:"))
        search_layout.addWidget(self.log_type)

        # 日期范围选择
        self.start_date = QDateEdit()
        self.start_date.setDate(QDate.currentDate())
        self.end_date = QDateEdit()
        self.end_date.setDate(QDate.currentDate())

        search_layout.addWidget(QLabel("开始日期:"))
        search_layout.addWidget(self.start_date)
        search_layout.addWidget(QLabel("结束日期:"))
        search_layout.addWidget(self.end_date)

        # 关键字搜索
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("输入搜索关键字")
        search_layout.addWidget(self.search_input)

        # 搜索按钮
        search_btn = QPushButton("搜索")
        search_btn.clicked.connect(self.search_logs)
        search_layout.addWidget(search_btn)

        layout.addLayout(search_layout)

        # 日志显示区域
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        layout.addWidget(self.log_display)

        self.setLayout(layout)

    def apply_theme(self):
        if self.parent().is_dark_theme:
            self.parent().set_dark_theme(self)
        else:
            self.parent().set_light_theme(self)

    def search_logs(self):
        """按日期搜索日志函数，适配新的日志命名格式 window_YYYYMMDD.log 和 service_YYYYMMDD.log"""
        try:
            keyword = self.search_input.text()
            start_date = self.start_date.date().toPython()
            end_date = self.end_date.date().toPython()
            log_type = self.log_type.currentText()

            # 获取日志目录
            if getattr(sys, 'frozen', False):
                base_dir = os.path.dirname(sys.executable)
            else:
                base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

            log_dir = os.path.join(base_dir, 'logs')
            results = []

            # 逐日遍历日期范围
            current_date = start_date
            while current_date <= end_date:
                date_str = current_date.strftime("%Y%m%d")

                # 根据选择的日志类型确定要搜索的文件
                log_files_to_check = []

                if log_type in ["所有日志", "窗口日志"]:
                    window_log = os.path.join(log_dir, f"window_{date_str}.log")
                    print(f"{window_log}")
                    if os.path.exists(window_log):
                        log_files_to_check.append(window_log)

                if log_type in ["所有日志", "服务日志"]:
                    service_log = os.path.join(log_dir, f"service_{date_str}.log")
                    if os.path.exists(service_log):
                        log_files_to_check.append(service_log)

                # 搜索当天的日志文件
                for log_file in log_files_to_check:
                    try:
                        with open(log_file, 'r', encoding='utf-8') as f:
                            file_name = os.path.basename(log_file)
                            # 确定日志来源标识
                            log_source = "服务" if file_name.startswith("service_") else "窗口"
                            for line in f:
                                if keyword.lower() in line.lower():
                                    # 添加文件名标识到每行日志前
                                    results.append(f"[{log_source}] {line.strip()}")
                    except Exception as e:
                        results.append(f"Error reading {os.path.basename(log_file)}: {str(e)}")

                # 移到下一天
                current_date = current_date.replace(day=current_date.day + 1)

            # 显示结果
            if results:
                self.log_display.setText('\n'.join(results))
            else:
                self.log_display.setText("未找到匹配的日志记录")

        except Exception as e:
            self.log_display.setText(f"搜索日志时出错: {str(e)}")
