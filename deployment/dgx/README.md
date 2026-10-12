# DGX 上的 Codex 远程工作台

公网入口：**<https://workbench.example.com>**
DGX 本机入口：**<http://127.0.0.1:4173>**

两个地址连接同一个后端。Mac 和手机用于发任务、看进度、上传下载文件；真正的命令和文件操作发生在 DGX。此工作台使用独立的第三方 API 环境，适合临时小项目，不与原生 Codex CLI 实时同步，也没有新增科研自动唤醒系统。

## 1. 登录和新建任务

先通过 Cloudflare Access，再输入 WebUI 密码。你此前的 Access 登录问题已解决：允许策略中需要包含自己的登录邮箱。

日常本人使用建议输入 **owner** 密码；admin 的终端及完整操作权限受到限制。两者都使用同一个密码框，不需要用户名。现有密码保存在本机私有文件 `runtime/login.txt`，需要时在 DGX 终端查看，不要把内容发到聊天或 GitHub。

开始一个项目：

1. 在左侧“项目空间”点 **＋**，填写名字，例如 `旅行计划`，点击“创建项目”。这会创建真实的 DGX 文件夹。
2. 选中这个项目，点击 **新对话**。顶部可填写对话标题。
3. 在底部输入任务，点 **发送**。第一次发送或上传文件时，会话才正式保存。
4. 以后先选项目，再点左侧对话继续。一个项目可以有多条对话；这些对话共享项目文件。

手机上点左上角菜单，或顶部 **项目与文件**，展开导航。若仍看到旧界面，请刷新页面；主要按钮已中文化，部分上游高级菜单仍是英文。

## 2. 项目文件实际在哪里

所有 WebUI 项目统一放在：

```text
/home/khw/projects/web-ui-projects/
```

例如网页创建“旅行计划”后，会得到：

```text
/home/khw/projects/web-ui-projects/旅行计划/
```

**这就是对应会话的真实 cwd（工作目录）**，会自动保存，不必再在开场白中要求助手切换目录。网页顶部会显示实际路径。相对路径 `reports/result.md` 通常就位于这个项目的 `reports/` 中；仍以任务实际写入路径为准。

选择其他项目会进入该项目的新对话草稿，不会移动旧会话。已有会话的项目目录不能直接改掉；想在另一项目工作，应另开一条会话。也可以先在 DGX 的这个根目录下放入一个现有真实文件夹，刷新后选择它。根目录本身、根外目录和软链接不作为可选项目。

聊天里出现一段代码，不等于已经写入磁盘。需要产物时可直接说：

> 请把结果实际保存到当前项目的 reports/result.md，并在回复里给我文件链接。

项目目录是文件归属约定，**不是系统沙箱**。owner 仍保留原部署的完整 shell 权限；同时在多条对话修改同一文件时，需要自行协调。

## 3. 上传、引用、预览和下载

| 想做什么 | 网页操作 | 实际效果 |
|---|---|---|
| 上传手机/电脑文件 | 输入框的回形针，或左侧“文件”页的上传按钮 | 上传后附加到当前对话，在项目 `uploads/` 保存副本 |
| 查看 DGX 文件 | 左侧切换“文件”，点文件名 | 文本/Markdown 打开预览或源码，常见图片直接预览 |
| 让 Codex 读取项目文件 | 文件右侧的 **@** | 完整路径加入输入框；再补充任务并发送 |
| 下载产物 | 文件右侧下载图标，或文件页的 **Download** | 保存到正在使用的 Mac/手机，由浏览器选择下载位置 |
| 修改文本文件 | 文件页 **Edit → Save** | 直接修改 DGX 上的文件；修改后任务会读到新内容 |

上传的实际路径类似：

```text
/home/khw/projects/web-ui-projects/旅行计划/uploads/<唯一标识>-预算.txt
```

唯一标识防止同名上传互相覆盖。侧栏尽量显示易读的原文件名，悬停可看完整路径。Codex 默认读取项目副本，可以再要求它整理进 `data/` 等子目录。

系统还会保留原始附件快照，供历史附件下载。删除聊天附件或编辑项目副本，不会自动删除/修改另一份。项目副本和任务产物也占 DGX 磁盘空间。

Markdown、文本与常见图片已验证。PDF、Office、压缩包等先下载后用本地软件打开；不在页面执行上传的 HTML/脚本。大文件预览仍受上游限制，但可以下载。单目录最多显示 500 项；软链接及敏感路径不显示。文件页可手动刷新，可见时约每 10 秒更新一次。

## 4. 怎样看工作过程，断网会怎样

任务运行时会显示实际返回的进度消息、工具调用、shell 命令、输出与完成回复。点 **展开工作过程** 载入最近 8 轮的过程和工具详情；工具卡片可以继续展开，大输出按需加载。更早的回合可逐条展开。

“推理摘要”只展示模型/API 真正提供的内容，不能查看未公开的内部思考。本次第三方真实测试没有返回可显示的推理摘要；命令、工具与进度已实测。历史中不存在的事件无法凭空补回。

关闭标签页、手机锁屏或网络断开，不会直接停止后端任务。重新登录并打开同一条对话，会恢复运行或完成状态。另一个浏览器也能查看同一条任务；无需让电脑一直开着网页。

**停止 WebUI 服务、重启 DGX 或 Codex 进程退出，则可能中断运行中的命令。** 已保存的对话和文件仍在，不保证在途任务跨服务/主机重启无缝继续。DGX 已启用无人登录常驻 `Linger=yes`；整机重启未实际演练。

## 5. 聊天与配置的保存位置

| 内容 | DGX 位置 |
|---|---|
| 项目文件和产物 | `/home/khw/projects/web-ui-projects/<项目名>/` |
| 会话记录 | `/home/khw/projects/web-ui/runtime/codex-home/sessions/` 下按日期保存的 `rollout-*.jsonl` |
| 归档记录 | `/home/khw/projects/web-ui/runtime/codex-home/archived_sessions/` |
| 会话 cwd、草稿、队列与其他状态 | `/home/khw/projects/web-ui/runtime/data/profiles/thirdparty/ui-state.json` |
| 原始附件快照 | `/home/khw/projects/web-ui/runtime/data/profiles/thirdparty/uploads/<会话ID>/` |
| WebUI 独立模型/API 配置 | `/home/khw/projects/web-ui/runtime/codex-home/config.toml`，属于私密文件 |
| 服务环境、登录凭据 | `/home/khw/projects/web-ui/runtime/`，属于私密目录 |

会话 ID 是浏览器地址中 `session=` 后面的字符串。平时用网页看历史，不要手改 rollout 或 ui-state。

以前导入的 CLI/Cryochamber 历史保留在原位置，本轮未删除或重新导入。新的项目导航按真实 cwd 过滤，因此旧根目录下的对话不挤占项目列表。本轮不承诺修复所有旧历史；原 `/home/khw/.codex` 的配置、认证与全局指令未修改。

## 6. 怎样改密码

修改 **WebUI owner 密码**，在 DGX 或 SSH 的交互式终端执行：

```bash
python3 /home/khw/projects/web-ui/scripts/change-password.py owner
```

按提示输入两遍，至少 12 个字符，输入时屏幕不显示字符。改 admin 时把最后的 `owner` 换成 `admin`，两者应不同。不要把密码直接写进命令行。

工具会备份旧配置，更新密码哈希、登录记录和 session secret。**等正在运行的任务结束后**再执行：

```bash
systemctl --user restart codex-webui
systemctl --user is-active codex-webui
```

显示 `active` 后，刷新网页用新密码登录；旧登录态失效。聊天和文件保留，正在执行的任务可能被重启中断。只改 `runtime/login.txt` 不会改变真实密码。这不改变 Cloudflare 账号密码或第三方 API 密钥。

## 7. 维护、备份和回退

源代码工作树：`/home/khw/projects/web-ui/workbench`，分支 `workbench/projects`。正式构建通过 `current` 指向固定的 `releases/workbench-…/`，开发构建不会覆盖正在运行的网页。

```bash
systemctl --user status codex-webui
journalctl --user -u codex-webui -n 50 --no-pager
readlink /home/khw/projects/web-ui/current
```

**备份需要同时覆盖整个 `runtime/` 和 `web-ui-projects/`**。Git 只备份代码，不备份聊天、密钥、密码或项目产物。私有部署备份在 `backups/`，本轮正式切换记录在 [部署记录](evidence/workbench-deployment.json)。

需要退回上一版时，先等所有任务结束，再运行：

```bash
python3 /home/khw/projects/web-ui/scripts/rollback-workbench.py
```

它恢复切换前的服务与环境配置，保留当前会话和项目文件，不会用旧数据覆盖新产物。若切换之后改过密码，回退配置会恢复切换前密码，需要重新改密。只恢复旧版界面不会自动迁移新项目。

Cloudflare、Access 和 SSH 配置保持原样；后端仍只监听 loopback，既有资源上限为 4 CPU、8 GiB、最多 2 个 app-server。第三方 API 调用仍产生该服务商的费用。

实现与上游维护方式见 [代码说明](workbench/WORKBENCH.md)。本轮验收记录见 [验收说明](evidence/WORKBENCH_VALIDATION.md)。GitHub 推送状态见 [当前摘要](CURRENT_SUMMARY.md)。
