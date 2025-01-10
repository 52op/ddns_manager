# DDNS_Manager 动态IP自动解析工具

## 简介

将动态IP地址自动更新到腾讯云和DNSPod的域名解析记录中。支持多账号、多域名，以及IPv4的A记录和IPv6的AAAA记录。

工具提供了两种运行方式：通过程序窗口手动更新或安装为Windows系统服务自动更新。

# 为什么重复造轮子？
***现在能用的相似工具太高端了，什么go什么rust啊等等写的，好看也好用***
***就是一拿到win7上就跑不起来了,试烦了索性就自己造了***
- 所以我的这个工具就一个优点，win7下开发的，所以win7兼容的好
- 当然得益于windows不错的向下兼容特性,win10 win11等也是没问题的  
- 开发它的原因其一是想让我另外一个小工具 [file_share](https://github.com/52op/file_share)
  在没有公网IPV4的情况下，可以让主机也能随时提供文件共享服务
- **效果展示:** [http://v6.sztcrs.com](http://v6.sztcrs.com)


## 功能特性

- **多账号支持**：可以配置多个腾讯云和DNSPod账号。
- **多域名支持**：支持同时更新多个域名的解析记录。
- **IPv4 & IPv6支持**：支持A记录（IPv4）和AAAA记录（IPv6）。
- **两种运行模式**：
  - **窗口模式**：通过GUI界面手动触发IP更新。
  - **服务模式**：安装为Windows系统服务，自动检测IP变化并更新。

## 系统要求

- 操作系统：Windows 7、Windows 10、Windows 11

## 使用

直接下载 [Releases](https://github.com/52op/ddns_manager/releases) 解压运行 DM动态IP自动解析工具.exe

## 开发

1. **克隆仓库**：
   
   ```bash
   git clone https://github.com/52op/ddns_manager.git
   cd ddns_manager
   ```

2. **安装依赖**：
   
   ```shell
   pip install -r requirements.txt
   ```
   
   

3. **编译运行程序**：
   
   ```shell
   build.bat
   python deploy.py
   ```
## 截图
![1](https://github.com/52op/ddns_manager/blob/master/preview_images/1.png)

![2](https://github.com/52op/ddns_manager/blob/master/preview_images/2.png)

![3](https://github.com/52op/ddns_manager/blob/master/preview_images/3.png)

![4](https://github.com/52op/ddns_manager/blob/master/preview_images/4.png)

## 贡献

欢迎提交Issue和Pull Request。如果你有任何问题或建议，请随时联系[letvar@qq.com](mailto:letvar@qq.com)。

## 许可证

本项目采用MIT许可证。详情请见[LICENSE](https://github.com/52op/ddns_manager?tab=License-1-ov-file)文件。


