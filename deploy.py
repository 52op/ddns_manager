import os
import shutil
import zipfile
from datetime import datetime


def create_deployment():
    # 创建临时部署目录
    deploy_dir = 'deploy'
    if os.path.exists(deploy_dir):
        shutil.rmtree(deploy_dir)
    os.makedirs(deploy_dir)

    # 创建Releases目录
    releases_dir = 'Releases'
    if not os.path.exists(releases_dir):
        os.makedirs(releases_dir)

    # 复制必要文件
    files_to_copy = [
        ('dist/ddns_manager.exe', 'DM动态IP自动解析工具.exe'),
        ('dist/ddns_service.exe', 'ddns_service.exe'),
        ('readme.md', 'readme.md'),
        ('LICENSE', 'LICENSE')
    ]

    for src, dst in files_to_copy:
        shutil.copy2(src, os.path.join(deploy_dir, dst))

    # 创建目录结构
    os.makedirs(os.path.join(deploy_dir, 'logs'))

    # 创建zip文件在Releases目录中
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    zip_filename = f'ddns_manager_{timestamp}.zip'
    zip_path = os.path.join(releases_dir, zip_filename)

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # 遍历部署目录中的所有文件和文件夹
        for root, dirs, files in os.walk(deploy_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, deploy_dir)
                zipf.write(file_path, arcname)
            for dir in dirs:
                dir_path = os.path.join(root, dir)
                arcname = os.path.relpath(dir_path, deploy_dir) + '/'
                zipf.write(dir_path, arcname)

    # 清理临时部署目录
    shutil.rmtree(deploy_dir)

    print(f"部署包已创建: {zip_path}")


if __name__ == '__main__':
    create_deployment()
