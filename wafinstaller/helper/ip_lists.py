import ipaddress
import os
from typing import Dict, List, Optional, Tuple, Type

from wafinstaller.helper.server_conf import ApacheConfManager, NginxConfManager, ServerConfManager


class IpListError(Exception):
    """Raised when an IP list cannot be validated or published."""


Entry = Tuple[str, str]  # (normalized ip/cidr, comment)


def parse_entries(text: str) -> Tuple[List[Entry], List[str]]:
    """Parse 'one IP/CIDR per line, optional # comment'. Returns (entries, errors)."""
    entries: List[Entry] = []
    errors: List[str] = []
    seen = set()
    for lineno, raw in enumerate((text or "").splitlines(), start=1):
        value, _, comment = raw.partition("#")
        value, comment = value.strip(), comment.strip()
        if not value:
            continue
        try:
            net = ipaddress.ip_network(value, strict=True)
        except ValueError as e:
            errors.append(f"Line {lineno}: '{value}' is not a valid IP or CIDR ({e}).")
            continue
        single = net.num_addresses == 1
        normalized = str(net.network_address) if single else str(net)
        if normalized in seen:
            continue
        seen.add(normalized)
        entries.append((normalized, comment))
    return entries, errors


def normalize_entries(entries: List[Entry]) -> str:
    return "\n".join(f"{ip}  # {c}" if c else ip for ip, c in entries)


# -------------------------
# Writers: one per web server
# -------------------------

class IpListWriter:
    """Renders an IpList into the include-file syntax of one web server."""

    manager_cls: Type[ServerConfManager] = ServerConfManager
    BASE_DIR = ""

    def __init__(self):
        self.manager = self.manager_cls()

    @classmethod
    def is_available(cls) -> bool:
        return cls.manager_cls.is_installed()

    @classmethod
    def base_dir(cls) -> str:
        return cls.BASE_DIR

    @classmethod
    def path_for(cls, ip_list) -> str:
        return os.path.join(cls.base_dir(), f"{ip_list.name}.conf")

    def header(self, ip_list) -> str:
        lines = [
            "# Managed by OWASP WafControl - do not edit by hand, changes will be overwritten.",
            f"# IP list: {ip_list.name} ({ip_list.action})",
        ]
        if ip_list.description:
            # Single line only: a newline would turn the rest of the text into a directive.
            lines.append("# " + " ".join(ip_list.description.split()))
        return "\n".join(lines) + "\n"

    def render(self, ip_list, entries: List[Entry]) -> str:
        raise NotImplementedError

    @staticmethod
    def _line(directive: str, comment: str) -> str:
        return f"{directive}  # {comment}" if comment else directive


class NginxIpListWriter(IpListWriter):
    key = "nginx"
    label = "Nginx"
    manager_cls = NginxConfManager
    BASE_DIR = "/etc/nginx/wafcontrol/iplists"

    def render(self, ip_list, entries):
        body = [self._line(f"{ip_list.action} {ip};", c) for ip, c in entries]
        return self.header(ip_list) + "\n".join(body) + ("\n" if body else "")


class ApacheIpListWriter(IpListWriter):
    key = "apache"
    label = "Apache"
    manager_cls = ApacheConfManager

    @classmethod
    def base_dir(cls) -> str:
        root = "/etc/httpd" if not os.path.isdir("/etc/apache2") and os.path.isdir("/etc/httpd") else "/etc/apache2"
        return os.path.join(root, "wafcontrol", "iplists")

    @staticmethod
    def _line(directive: str, comment: str) -> str:
        # Apache only allows whole-line comments.
        return f"# {comment}\n{directive}" if comment else directive

    def render(self, ip_list, entries):
        keyword = "Require ip" if ip_list.is_allow else "Require not ip"
        body = [self._line(f"{keyword} {ip}", c) for ip, c in entries]
        if not body and ip_list.is_allow:
            # An empty <RequireAny> is a config error; an empty allow list means nobody is allowed.
            body = ["# list is empty", "Require all denied"]
        return self.header(ip_list) + "\n".join(body) + ("\n" if body else "")


WRITERS: List[Type[IpListWriter]] = [NginxIpListWriter, ApacheIpListWriter]


# -------------------------
# Service
# -------------------------

class IpListService:
    """Publishes IP lists as include files for every installed web server.

    Writes are transactional across servers: all files are written, each server's
    config is tested, and on any failure every file is restored before raising.
    """

    def __init__(self, writers: Optional[List[IpListWriter]] = None):
        self.writers = writers if writers is not None else [w() for w in WRITERS if w.is_available()]

    @staticmethod
    def include_paths(ip_list) -> Dict[str, str]:
        return {w.key: w.path_for(ip_list) for w in WRITERS}

    def publish(self, ip_list) -> List[str]:
        entries, errors = parse_entries(ip_list.entries)
        if errors:
            raise IpListError("\n".join(errors))
        changes = {w.path_for(ip_list): w.render(ip_list, entries) for w in self.writers}
        return self._apply(changes)

    def remove(self, ip_list) -> List[str]:
        return self._apply({w.path_for(ip_list): None for w in self.writers})

    # ---------- internals ----------

    def _apply(self, changes: Dict[str, Optional[str]]) -> List[str]:
        if not self.writers:
            return ["No web server detected: list saved but no include file was generated."]
        backups: Dict[str, Optional[str]] = {}
        try:
            for path, content in changes.items():
                backups[path] = self._read(path)
                self._write(path, content)
            for writer in self.writers:
                ok, output = writer.manager.test_config()
                if not ok:
                    raise IpListError(f"{writer.label} config test failed, changes reverted:\n{output}")
        except (IpListError, OSError) as e:
            for path, old in backups.items():
                try:
                    self._write(path, old)
                except OSError:
                    pass
            if isinstance(e, OSError):
                raise IpListError(f"Cannot write include file: {e}") from e
            raise
        return [w.manager.reload() for w in self.writers]

    @staticmethod
    def _read(path: str) -> Optional[str]:
        if not os.path.isfile(path):
            return None
        with open(path, "r") as f:
            return f.read()

    @staticmethod
    def _write(path: str, content: Optional[str]) -> None:
        if content is None:
            if os.path.isfile(path):
                os.remove(path)
            return
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(content)
