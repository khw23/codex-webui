#!/usr/bin/env python3
"""Return to the saved service and configuration after checking the task list."""
import importlib.util, json, shutil, subprocess
from pathlib import Path
root=Path('/home/khw/projects/web-ui')
spec=importlib.util.spec_from_file_location('deployment',root/'scripts/deploy-workbench.py');deployment=importlib.util.module_from_spec(spec);spec.loader.exec_module(deployment)
deployment.auth_get_sessions()
backup=Path(json.loads((root/'evidence/workbench-deployment.json').read_text())['backup'])
subprocess.run(['systemctl','--user','stop','codex-webui'],check=True)
shutil.copy2(backup/'webui.env',root/'runtime/webui.env')
shutil.copy2(backup/'codex-webui.service',Path.home()/'.config/systemd/user/codex-webui.service')
shutil.copy2(backup/'codex-webui.service',root/'config/codex-webui.service')
subprocess.run(['systemctl','--user','daemon-reload'],check=True)
subprocess.run(['systemctl','--user','start','codex-webui'],check=True)
print('已恢复上一版服务配置；保留所有当前会话与项目文件。')
