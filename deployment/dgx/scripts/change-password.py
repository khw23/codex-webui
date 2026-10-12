#!/usr/bin/env python3
"""Change this deployment's WebUI password without restarting the service."""

import argparse
import base64
import fcntl
import getpass
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import sys
import tempfile


class PasswordError(Exception):
    """A message that is safe to show without exposing configuration values."""


def password_hash(password):
    salt = secrets.token_bytes(16)
    key = hashlib.scrypt(password.encode(), salt=salt, n=16384, r=8, p=1, dklen=64)
    encode = lambda value: base64.urlsafe_b64encode(value).decode().rstrip('=')
    return f'scrypt${encode(salt)}${encode(key)}'


def atomic_write(path, content):
    fd, temporary = tempfile.mkstemp(prefix='.password-update-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def change_password(runtime, role, password):
    if role not in ('owner', 'admin'):
        raise PasswordError('角色必须是 owner 或 admin。')
    if not 12 <= len(password) <= 1024 or any(char in password for char in '\r\n\0'):
        raise PasswordError('请使用 12–1024 个字符，且不含换行或空字符。')

    lock_fd = os.open(runtime / '.password-change.lock', os.O_CREAT | os.O_RDWR, 0o600)
    with os.fdopen(lock_fd, 'w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        paths = {name: runtime / name for name in ('webui.env', 'credentials.json', 'login.txt')}
        original = {name: path.read_bytes() for name, path in paths.items()}
        credentials = json.loads(original['credentials.json'])
        if not isinstance(credentials, dict) or not all(
            isinstance(credentials.get(key), str) for key in ('owner', 'admin')
        ):
            raise PasswordError('credentials.json 格式不符合本部署约定，未修改密码。')
        other_role = 'admin' if role == 'owner' else 'owner'
        if password == credentials[other_role]:
            raise PasswordError('owner 和 admin 应使用不同密码。')

        environment = original['webui.env'].decode()
        prefix = 'CODEX_WEBUI_OWNER_PASSWORD' if role == 'owner' else 'CODEX_WEBUI_PASSWORD'
        if re.search(rf'^{prefix}=', environment, re.MULTILINE):
            raise PasswordError('检测到额外的明文密码配置，请先核对 webui.env。')
        replacements = {
            prefix + '_HASH': password_hash(password),
            'CODEX_WEBUI_SESSION_SECRET': secrets.token_urlsafe(48),
        }
        for key, value in replacements.items():
            environment, count = re.subn(
                rf'^{re.escape(key)}=.*$', lambda _: f"{key}='{value}'",
                environment, flags=re.MULTILINE,
            )
            if count != 1:
                raise PasswordError(f'{key} 必须恰好出现一次，未修改密码。')

        credentials[role] = password
        login = (
            '公网地址：https://workbench.example.com\n'
            '本地地址：http://127.0.0.1:4173\n'
            f'日常登录密码（admin）：{credentials["admin"]}\n'
            f'完整控制密码（owner）：{credentials["owner"]}\n'
            '在同一个密码框输入对应密码即可。请勿将此文件提交 Git 或发送给他人。\n'
        )
        updated = {
            'credentials.json': (json.dumps(credentials, ensure_ascii=False) + '\n').encode(),
            'login.txt': login.encode(),
            'webui.env': environment.encode(),
        }
        backup = Path(tempfile.mkdtemp(prefix='password-backup-', dir=runtime))
        for name, content in original.items():
            atomic_write(backup / name, content)
        try:
            for name, content in updated.items():
                atomic_write(paths[name], content)
        except (OSError, KeyboardInterrupt):
            for name, content in original.items():
                atomic_write(paths[name], content)
            raise
        return backup


def main():
    parser = argparse.ArgumentParser(description='修改 WebUI 登录密码；不会自动重启服务。')
    parser.add_argument('role', choices=('owner', 'admin'), nargs='?', default='owner',
                        help='默认修改 owner；指定 admin 可修改普通管理密码。')
    args = parser.parse_args()
    if not sys.stdin.isatty():
        parser.exit(1, '请在 DGX 的交互式终端运行；不要把密码写进命令行或管道。\n')
    try:
        password = getpass.getpass(f'新的 {args.role} 密码（至少 12 个字符，输入时不显示）：')
        if password != getpass.getpass('再次输入新密码：'):
            parser.exit(1, '两次输入不同，未修改密码。\n')
        runtime = Path(__file__).resolve().parents[1] / 'runtime'
        backup = change_password(runtime, args.role, password)
    except PasswordError as error:
        parser.exit(1, f'{error}\n')
    except (ValueError, OSError, EOFError):
        # Do not include exception text: malformed input/config may contain secrets.
        parser.exit(1, '修改未完成，请检查 runtime 文件及权限；不要重启服务。\n')
    except KeyboardInterrupt:
        parser.exit(1, '\n已取消。\n')
    print(f'{args.role} 新密码已保存；当前运行中的服务仍使用旧密码。')
    print(f'旧配置备份：{backup}')
    print('等所有对话任务结束，在 DGX 终端执行：systemctl --user restart codex-webui')
    print('重启后所有 WebUI 登录态失效，需要重新登录；聊天记录和项目文件会保留。')


if __name__ == '__main__':
    main()
