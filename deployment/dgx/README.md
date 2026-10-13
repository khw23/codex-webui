# DGX / Linux 部署维护示例

这是不含个人地址或凭据的维护示例。完整工作台说明见 [WORKBENCH.md](../../WORKBENCH.md)。

建议目录：

```text
/srv/codex-workbench/
  workbench/       源码
  scripts/         从本目录复制的维护脚本
  runtime/         私有配置、登录信息、会话与附件
  releases/        固定构建版本
  current         当前版本的符号链接
  backups/        私有备份，不能上传 GitHub
/srv/codex-workbench-projects/
  example/        真实项目目录，也就是会话 cwd
```

示例脚本默认使用上述路径，部署前需检查 systemd 用户服务名称、端口、目录权限和备份空间。它们用于已有部署的维护，不是开箱即用的安装器。不要将源码目录中的脚本直接当作已经配置好的生产服务运行。

## 日常操作

在网页左侧创建或选择项目，再点击“新对话”；同项目可有多条会话。上传文件保存到项目的 `uploads/`，回复中的产物链接和文件页都可以下载文件。

运行中工具默认折成一行，点击展开限高的滚动详情；真实文字进度和推理摘要直接显示，空摘要不显示。任务结束后仍可展开整体工作过程。浏览器断网不停止后端任务；服务或主机重启可能中断执行。

## 配置与凭据

为 WebUI 设置独立的 `CODEX_HOME` 和 data 目录。公网代理与本机浏览器应连接同一个 loopback 后端。域名、代理策略、密码、session secret、API 地址和密钥只保存在部署机的私有配置中。

会话的模型和权限设置沿用上游保存机制：保存到会话，同时更新此 WebUI profile 的默认配置。完整访问、不弹审批等行为由实际部署配置决定；项目目录本身不是系统沙箱。

## 改密与维护

将 `scripts/` 中的工具复制到部署根目录下的 `scripts/`。改密脚本从其上一级目录寻找 `runtime/`，并要求已有 `webui.env`、`credentials.json` 和 `login.txt`。

```bash
python3 /srv/codex-workbench/scripts/change-password.py owner
# 等所有任务结束后重启，旧登录态失效：
systemctl --user restart codex-webui
```

部署/回退工具先检查任务空闲，保留固定 release 和 runtime 备份。备份还应另外覆盖项目根目录，Git 不保存会话或产物。回退服务配置可能恢复旧密码，因此改过密码后需要检查。
