from cryptography.fernet import Fernet
import base64
import hashlib
import subprocess
import json


class EncryptionHandler:
    def __init__(self):
        self._key = self._generate_machine_key()
        self._cipher = Fernet(self._key)

    def _generate_machine_key(self):
        """基于机器特征生成加密密钥"""
        # 使用无窗口方式获取机器码
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE

        # 获取机器唯一标识
        cmd = 'wmic csproduct get uuid'
        uuid = subprocess.check_output(cmd, startupinfo=startupinfo).decode('utf-8').strip()
        uuid = uuid.split('\n')[1].strip()

        # 生成密钥
        key = hashlib.sha256(uuid.encode()).digest()[:32]
        return base64.urlsafe_b64encode(key)

    def encrypt(self, data: str) -> str:
        """加密数据"""
        return self._cipher.encrypt(data.encode()).decode()

    def decrypt(self, encrypted_data: str) -> str:
        """解密数据"""
        return self._cipher.decrypt(encrypted_data.encode()).decode()

