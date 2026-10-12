# 部署维护材料

`dgx/` 保存个人 DGX 部署的使用说明及维护脚本，**不包含运行环境或凭据**。这些脚本是本机维护副本：部署时把 `dgx/scripts/` 的内容放到 `/home/khw/projects/web-ui/scripts/`，不要直接从源码工作树中的嵌套位置运行改密工具。改密工具按脚本上一级寻找 `runtime/`；部署和回退工具是明确绑定本机路径的。

`dgx/README.md` 中的 evidence、CURRENT_SUMMARY、runtime 等链接是部署根目录中的本机文件，不随 Git 仓库发布。通用部署与开发说明见 [WORKBENCH.md](../WORKBENCH.md)。公开源码不能代替私有运行数据备份。
