import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from typing import List, Optional, Tuple


class NginxConfError(Exception):
    """Raised when a conf.d operation cannot be completed."""


@dataclass
class ConfFile:
    name: str
    size: int
    modified: float


class NginxConfManager:
    """Service layer for listing, creating and editing /etc/nginx/conf.d/*.conf files.

    Every write is validated with `nginx -t`; on failure the previous content is
    restored (or the new file removed) so a bad edit never breaks the server.
    """

    CONF_DIR = "/etc/nginx/conf.d"
    NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,99}\.conf$")
    TEST_CMD = ["nginx", "-t"]
    RELOAD_CMD = ["nginx", "-s", "reload"]

    def __init__(self, conf_dir: Optional[str] = None):
        self.conf_dir = conf_dir or self.CONF_DIR

    # ---------- state ----------

    @staticmethod
    def is_nginx_installed() -> bool:
        return bool(shutil.which("nginx")) or os.path.isdir("/etc/nginx")

    def dir_exists(self) -> bool:
        return os.path.isdir(self.conf_dir)

    # ---------- read ----------

    def list_files(self) -> List[ConfFile]:
        if not self.dir_exists():
            raise NginxConfError(f"Directory not found: {self.conf_dir}")
        files = []
        for name in sorted(os.listdir(self.conf_dir)):
            path = os.path.join(self.conf_dir, name)
            if name.endswith(".conf") and os.path.isfile(path):
                st = os.stat(path)
                files.append(ConfFile(name=name, size=st.st_size, modified=st.st_mtime))
        return files

    def read(self, name: str) -> str:
        path = self._existing_path(name)
        with open(path, "r") as f:
            return f.read()

    # ---------- write ----------

    def create(self, name: str, content: str = "") -> str:
        path = self._path(name)
        if os.path.exists(path):
            raise NginxConfError(f"File already exists: {name}")
        self._write(path, content)
        ok, output = self._test()
        if not ok:
            os.remove(path)
            raise NginxConfError(f"nginx -t failed, file not created:\n{output}")
        return self._reload()

    def save(self, name: str, content: str) -> str:
        path = self._existing_path(name)
        with open(path, "r") as f:
            backup = f.read()
        self._write(path, content)
        ok, output = self._test()
        if not ok:
            self._write(path, backup)
            raise NginxConfError(f"nginx -t failed, changes reverted:\n{output}")
        return self._reload()

    # ---------- internals ----------

    def _path(self, name: str) -> str:
        name = (name or "").strip()
        if not self.NAME_PATTERN.match(name) or ".." in name:
            raise NginxConfError(
                "Invalid filename. Use letters, digits, '.', '_' or '-' and end with .conf"
            )
        if not self.dir_exists():
            raise NginxConfError(f"Directory not found: {self.conf_dir}")
        base = os.path.realpath(self.conf_dir)
        path = os.path.realpath(os.path.join(base, name))
        if os.path.dirname(path) != base:
            raise NginxConfError("Invalid file path.")
        return path

    def _existing_path(self, name: str) -> str:
        path = self._path(name)
        if not os.path.isfile(path):
            raise NginxConfError(f"File not found: {name}")
        return path

    @staticmethod
    def _write(path: str, content: str) -> None:
        content = content.replace("\r\n", "\n")
        with open(path, "w") as f:
            f.write(content)

    def _test(self) -> Tuple[bool, str]:
        try:
            proc = subprocess.run(
                self.TEST_CMD, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, check=False
            )
            return proc.returncode == 0, (proc.stdout or "").strip()
        except FileNotFoundError:
            return False, "nginx binary not found."

    def _reload(self) -> str:
        proc = subprocess.run(
            self.RELOAD_CMD, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, check=False
        )
        if proc.returncode != 0:
            return f"Saved, but nginx reload failed: {(proc.stdout or '').strip()}"
        return "Saved and nginx reloaded."
