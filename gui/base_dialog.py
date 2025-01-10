from PySide2.QtWidgets import QDialog, QInputDialog, QLineEdit, QMessageBox


class ProtectedDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        # 在显示对话框之前进行密码验证
        self.verified = self.verify_password()
        if not self.verified:
            # 验证失败时直接关闭
            self.close()

    def showEvent(self, event):
        # 重写showEvent,只有验证通过才允许显示
        if not self.verified:
            event.ignore()
            self.close()
        else:
            super().showEvent(event)

    def exec_(self):
        # 重写exec_方法,验证失败直接返回QDialog.Rejected
        if not self.verified:
            return QDialog.Rejected
        return super().exec_()

    def verify_password(self):
        config_manager = self.parent().config_manager
        if not config_manager.global_settings.get('password_protected', False):
            return True

        while True:  # 添加循环,给用户多次输入机会
            password, ok = QInputDialog.getText(
                self.parent(),
                "密码验证",
                "请输入密码:",
                QLineEdit.Password
            )
            if not ok:  # 用户点击取消
                return False
            if password == config_manager.global_settings.get('settings_password', 'letvar'):
                return True
            QMessageBox.warning(self.parent(), "错误", "密码错误!请重试")

