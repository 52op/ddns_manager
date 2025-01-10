import sys

from PySide2.QtWidgets import QApplication
from PySide2.QtCore import QCoreApplication
from gui.main_window import MainWindow
import logging


def setup_application():
    # 设置应用程序基本信息
    QCoreApplication.setOrganizationName("LetVar")
    QCoreApplication.setApplicationName("DNS更新管理器")

    # 配置日志系统
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('dns_manager.log'),
            logging.StreamHandler()  # 添加控制台输出
        ]
    )


def main():
    setup_application()

    app = QApplication(sys.argv)

    # 设置应用程序样式
    app.setStyle('Fusion')

    # 创建并显示主窗口
    window = MainWindow()

    # 处理命令行参数
    start_update = "-start" in sys.argv
    minimize = "-min" in sys.argv

    if minimize:
        window.hide()
    else:
        window.show()

    if start_update:
        window.update_records()

    # sys.exit(app.exec())    # PySide6写法
    sys.exit(app.exec_())   # PySide2写法


if __name__ == '__main__':
    main()
