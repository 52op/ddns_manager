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
        keyword = self.search_input.text()
        start_date = self.start_date.date().toPython()
        end_date = self.end_date.date().toPython()
        log_type = self.log_type.currentText()
        today = datetime.now().date()

        # 获取日志目录
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        log_dir = os.path.join(base_dir, 'logs')

        # 初始化 list 以存储所有匹配的日志文件
        log_files_to_check = []

        # 处理服务日志
        if log_type in ["所有日志", "服务日志"]:
            # 如果在日期范围内，则添加当天的日志文件
            if start_date <= today <= end_date:
                current_log = os.path.join(log_dir, "service.log")
                if os.path.exists(current_log):
                    log_files_to_check.append(current_log)
            # 添加历史日志文件
            log_files_to_check.extend(glob.glob(os.path.join(log_dir, "service_*.log")))

        # 处理窗口日志
        if log_type in ["所有日志", "窗口日志"]:
            # 如果在日期范围内，则添加当天的日志文件
            if start_date <= today <= end_date:
                current_log = os.path.join(log_dir, "window.log")
                if os.path.exists(current_log):
                    log_files_to_check.append(current_log)
            # 添加历史日志文件
            log_files_to_check.extend(glob.glob(os.path.join(log_dir, "window_*.log")))

        results = []
        for log_file in log_files_to_check:
            file_name = os.path.basename(log_file)

            # 确定文件日期
            if file_name in ["service.log", "window.log"]:
                file_date = today
            else:
                # 从历史日志文件中提取日期
                file_date_str = file_name.split('_')[1].split('.')[0]
                file_date = datetime.strptime(file_date_str, "%Y%m%d").date()

            # 检查文件日期是否在范围内
            if start_date <= file_date <= end_date:
                try:
                    with open(log_file, 'r', encoding='utf-8') as f:
                        for line in f:
                            if keyword.lower() in line.lower():
                                results.append(line.strip())
                except Exception as e:
                    results.append(f"Error reading {file_name}: {str(e)}")

        # 显示结果
        self.log_display.setText('\n'.join(results))
