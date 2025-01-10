import win32serviceutil
import win32service
import os
import sys
import subprocess
import logging
import winreg

from PySide2.QtWidgets import QMessageBox


class ServiceController:
    SERVICE_NAME = "DdnsUpdater"

    def __init__(self):
        self.executable_path = os.path.abspath(sys.argv[0])
        self.service_path = os.path.join(os.path.dirname(self.executable_path), 'ddns_service.exe')

    def install_service(self):
        try:
            # 检查开机启动状态
            if self.is_startup_enabled():
                reply = QMessageBox.question(
                    None,
                    "确认",
                    "检测到您已将本程序设置成开机运行，建议不要再安装后台服务，是否继续安装？",
                    QMessageBox.Yes | QMessageBox.No
                )
                if reply == QMessageBox.No:
                    return False, "用户取消安装"
            if not os.path.exists(self.service_path):
                raise FileNotFoundError("未找到服务可执行文件")

            cmd = f'"{self.service_path}" install'
            subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)

            # Set to auto-start
            auto_cmd = f'sc config {self.SERVICE_NAME} start= auto'
            subprocess.run(auto_cmd, shell=True, check=True, capture_output=True, text=True)

            return True, "服务安装成功"
        except Exception as e:
            logging.error(f"服务安装失败: {e}")
            return False, str(e)

    def uninstall_service(self):
        try:
            subprocess.run([self.service_path, "remove"], check=True, capture_output=True, text=True)
            return True, "服务卸载成功"
        except Exception as e:
            logging.error(f"服务卸载失败: {e}")
            return False, str(e)

    def start_service(self):
        try:
            win32serviceutil.StartService(self.SERVICE_NAME)
            return True, "服务已成功启动"
        except Exception as e:
            logging.error(f"服务启动失败: {e}")
            return False, str(e)

    def stop_service(self):
        try:
            win32serviceutil.StopService(self.SERVICE_NAME)
            return True, "服务已成功停止"
        except Exception as e:
            logging.error(f"服务停止失败: {e}")
            return False, str(e)

    def is_service_installed(self):
        try:
            win32serviceutil.QueryServiceStatus(self.SERVICE_NAME)
            return True
        except:
            return False

    def is_service_running(self):
        try:
            status = win32serviceutil.QueryServiceStatus(self.SERVICE_NAME)[1]
            return status == win32service.SERVICE_RUNNING
        except:
            return False

    def enable_startup(self):
        try:
            # 检查服务安装状态
            if self.is_service_installed():
                reply = QMessageBox.question(
                    None,
                    "确认",
                    "检测到您已安装后台服务，建议不要再将本程序设置开机启动，是否继续设置？",
                    QMessageBox.Yes | QMessageBox.No
                )
                if reply == QMessageBox.No:
                    return False, "用户取消设置"
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_SET_VALUE
            )

            if getattr(sys, 'frozen', False):
                exe_path = sys.executable
            else:
                exe_path = sys.argv[0]

            command = f'"{exe_path}" -start -min'
            winreg.SetValueEx(key, "DdnsManager", 0, winreg.REG_SZ, command)
            winreg.CloseKey(key)
            return True, "开机启动设置成功"
        except Exception as e:
            return False, f"设置开机启动失败: {str(e)}"

    def disable_startup(self):
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_SET_VALUE
            )
            try:
                winreg.DeleteValue(key, "DdnsManager")
            except WindowsError:
                pass  # 键不存在时忽略
            winreg.CloseKey(key)
            return True, "已移除开机启动"
        except Exception as e:
            return False, f"移除开机启动失败: {str(e)}"

    def is_startup_enabled(self):
        """检查是否已启用开机自启"""
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_READ
            )
            try:
                winreg.QueryValueEx(key, "DdnsManager")
                return True
            except WindowsError:
                return False
            finally:
                winreg.CloseKey(key)
        except Exception:
            return False
