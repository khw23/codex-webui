# 个人远程 Codex 工作台

这是基于 [seo-rii/codex-webui](https://github.com/seo-rii/codex-webui) 的个人项目工作台改造。适合从电脑或手机浏览器向一台常驻主机发布任务、管理小项目。保留上游 Codex app-server、鉴权、WebSocket、附件和文件编辑能力，不新增 Agent Harness 或科研自动唤醒系统。

## 使用方式

1. 左侧“项目空间”的 **＋** 创建真实文件夹，也可选择项目根下已经存在的直接子目录。
2. 选择项目后点击 **新对话**，输入标题和任务，发送。首次发送或上传附件时创建会话。同项目可以有多条对话，共享项目文件。
3. 顶部始终显示实际工作目录。会话创建后固定在这个项目，切换项目会进入另一份新对话草稿。
4. “文件”页浏览真实项目目录。文件名按钮打开预览，**@** 把完整文件路径放入输入框，下载按钮将文件保存到当前电脑/手机。上传保存在项目 `uploads/`，名称带唯一标识，防止同名覆盖。
5. “展开工作过程”载入最近 8 轮的过程与工具详情；超长输出保持按需加载。模型实际提供的推理摘要才能展示，没有摘要时不会编造。
6. 关闭浏览器不停止任务。重开同一条对话可恢复状态；在另一个浏览器登录同一个后端，也能看见同一批项目与会话。

运行中命令和工具默认收成一行，点击后在限高区域滚动查看详情；中文进度及实际返回的推理摘要直接显示，不折叠或截断，空摘要不占位。完成后的整体工作过程仍默认折叠；再次展开时，内部沿用相同的小字、单行工具与限高滚动样式。最终回答保持正常排版与复制按钮。

主机重启、WebUI 服务停止、Codex 进程退出与浏览器断网不同。已写入的会话和文件会保留，但运行中的命令不保证跨进程重启继续。

## 独立部署

复用上游构建说明（Node 22、pnpm、Rust）。先构建再启动 Rust 网关，前端静态文件由同一网关提供。正式域名的反向代理应指向同一个 loopback 网关端口，不要额外启动一份带不同数据目录的后端。

在原部署环境中增加下列两项，路径应是已创建的绝对目录：

```dotenv
CODEX_WEBUI_PROJECTS_ROOT=/srv/codex-workbench/projects
CODEX_WEBUI_ALLOWED_ROOTS=/srv/codex-workbench/projects
```

同时给此部署配置独立的 `CODEX_HOME`、`CODEX_WEBUI_DATA_DIR` 和（如使用多 profile）`CODEX_WEBUI_PROFILES_JSON`。所有 profile 路径也必须指向独立目录，不能沿用个人原生 Codex 的 home。密码哈希、session secret、API 配置只在部署私有目录中维护。

`CODEX_WEBUI_PROJECTS_ROOT` 未设置时保留原上游导航。设置后，cwd 必须是项目根的直接子文件夹，不支持用根目录本身或软链接项目开会话。项目目录与 allowed roots 在启动时校验。目录约束用于会话归属和网页文件访问；Codex 的 shell 权限仍由原部署的 sandbox/approval 配置决定，项目目录不是系统级沙箱。

会话模型和权限选项沿用上游机制：保存会话偏好时，也会更新当前 WebUI profile 的默认配置，可能影响之后新建的会话。这些设置不直接修改另一套原生 Codex 环境。

项目导航使用后端 `projects/list`、`projects/create`、`projects/files`；会话列表复用 `sessions/list` 的 `filter.cwd`，在分页前过滤。数据仍由既有 ui-state 和 Codex rollout 持久化，不引入另一套任务数据库。

## 文件与备份

项目目录存放工作产物；WebUI profile 的 data 目录存放附件原始快照、草稿、队列与界面状态；独立 Codex home 存放配置和会话记录。应一起备份，Git 只备份源代码。

上传文件有两份：项目中的可编辑副本，以及 WebUI 私有 data 目录中的原始附件快照。Codex 优先引用项目副本；历史附件下载仍读取原始快照。删除附件不会删除项目副本。原始附件受上游上传限额/配额管理，项目中的文件占用另行计入磁盘。

支持文本/Markdown 预览与编辑、常见位图预览，以及一般文件下载。不执行上传的 HTML/脚本预览；PDF、Office、压缩包等可下载后用本地软件打开。一个目录最多列出 500 项，软链接及上游判定的敏感路径不显示。

## 本次兼容修复

- 原生字符串形式的 command 不再在输出或完成事件合并时丢失。
- 小于 64 KiB 的实时工具记录保留输出；大记录使用原详情接口。
- 读取新版 Codex `event_msg/item_completed` 的消息、命令和结果，兼容 PascalCase 类型与 snake_case 字段。保持原始 item ID，防止刷新后漏过程或重复最终回复。
- `exec` JavaScript 工具包装调用按工具展示，实际 shell 命令单独展示。补充 MCP 进度与 fileChange 输出增量的前端处理。
- 主题启动代码使用同源静态脚本，保留原 CSP，不增加 `unsafe-inline` 脚本权限。

具体提供哪些事件取决于 Codex 版本与 API 服务商。本次真实验收覆盖 shell/附件/进度/最终输出；MCP 进度与推理摘要规范化使用协议回归测试，没有声称服务商在真实测试中提供了这些信息。

## 版本维护

上游基线：`2619d78c55c6095aa8b9a7a1412fd0c7abf5e564`；改造分支：`workbench/projects`。保留上游历史与许可证，后续通过上游 remote fetch 后审查合并。正式部署使用固定构建目录；开发编译不直接覆盖运行目录。

本地检查：

```bash
pnpm check
node --experimental-strip-types --test frontend-tests/chat-state.test.mjs
cargo test --manifest-path backend/Cargo.toml -- --test-threads=4
pnpm build
pnpm verify:static-build
pnpm verify:api-parity
pnpm verify:tunnel-safety
```

发布前检查暂存内容，排除 `.env`、runtime、会话、密码、Token、浏览器登录态、备份和构建产物。`.gitignore` 已包含这些部署目录；不要用 `git add -f` 添加它们。
