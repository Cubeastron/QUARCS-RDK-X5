"""Manage the startup driver list of the existing RDK X5 INDI service."""

import json
import os
import re
import shlex
import shutil
import socket
import subprocess
import tempfile
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

UNIT = "indi.service"
API = "/api/indi-startup"
DROP_IN = Path("/etc/systemd/system/indi.service.d/99-quarcs-drivers.conf")
COMMAND = (
    "/usr/bin/env",
    "LD_LIBRARY_PATH=/usr/local/lib:/usr/lib/aarch64-linux-gnu",
    "/usr/bin/indiserver",
    "-v",
)
DRIVERS = {
    "qhy": "/usr/local/bin/indi-qhy-ascom-style",
    "onstep": "indi_lx200_OnStep",
    "nikon": "/usr/bin/indi_nikon_ccd",
    "robofocus": "indi_robo_focus",
    "v4l2": "indi_v4l2_ccd",
}
DRIVER_IDS = {executable: name for name, executable in DRIVERS.items()}


def systemctl(*args):
    return subprocess.run(
        ["/usr/bin/systemctl", *args], check=True, capture_output=True,
        text=True, timeout=20,
    ).stdout.strip()


def parse_drivers(args, prefix):
    if tuple(args[:len(prefix)]) != prefix:
        raise RuntimeError("Unexpected INDI service startup command")
    drivers = args[len(prefix):]
    if not drivers or any(driver not in DRIVER_IDS for driver in drivers):
        raise RuntimeError("Unexpected drivers in INDI service startup command")
    return [DRIVER_IDS[driver] for driver in drivers]


def service_drivers():
    value = systemctl("show", "-p", "ExecStart", "--value", UNIT)
    match = re.search(r"argv\[\]=(.*?) ;", value)
    if not match:
        raise RuntimeError("Unable to read the INDI service startup command")
    return parse_drivers(shlex.split(match[1]), COMMAND)


def settings():
    if DROP_IN.exists():
        lines = DROP_IN.read_text().splitlines()
        if len(lines) != 3 or lines[:2] != ["[Service]", "ExecStart="] or not lines[2].startswith("ExecStart="):
            raise RuntimeError("Unexpected QUARCS driver settings")
        return parse_drivers(shlex.split(lines[2].removeprefix("ExecStart=")), COMMAND)
    return service_drivers()


def state():
    saved = settings()
    pid = int(systemctl("show", "-p", "MainPID", "--value", UNIT))
    try:
        argv = (Path("/proc") / str(pid) / "cmdline").read_bytes() if pid else b""
    except FileNotFoundError:
        argv = b""
    running = parse_drivers(os.fsdecode(argv).rstrip("\0").split("\0"), COMMAND[2:]) if argv else []
    return {
        "drivers": [
            {"id": name, "executable": executable,
             "available": bool(shutil.which(executable, path="/usr/local/bin:/usr/bin"))}
            for name, executable in DRIVERS.items()
        ],
        "saved": saved,
        "running": running,
    }


def save(selection):
    current = state()
    if not isinstance(selection, list) or not selection or any(
        not isinstance(name, str) or name not in DRIVERS for name in selection
    ) or len(set(selection)) != len(selection):
        raise ValueError("invalidDrivers")
    available = {driver["id"] for driver in current["drivers"] if driver["available"]}
    if any(name not in available for name in selection):
        raise ValueError("driverUnavailable")
    # Preserve the relative startup order of existing drivers.
    ordered = [name for name in dict.fromkeys([*current["saved"], *DRIVERS]) if name in selection]
    args = (*COMMAND, *(DRIVERS[name] for name in ordered))
    data = "[Service]\nExecStart=\nExecStart=" + shlex.join(args) + "\n"
    with tempfile.NamedTemporaryFile(dir=DROP_IN.parent, mode="w", delete=False) as output:
        temporary = Path(output.name)
    try:
        temporary.write_text(data)
        temporary.chmod(0o644)
        temporary.replace(DROP_IN)
    finally:
        temporary.unlink(missing_ok=True)
    return state()


def restart():
    before = state()
    if set(before["saved"]) == set(before["running"]):
        return before
    systemctl("daemon-reload")
    if service_drivers() != before["saved"]:
        raise RuntimeError("The effective INDI unit differs from the saved driver settings")
    systemctl("restart", UNIT)
    systemctl("is-active", UNIT)
    return state()


class Handler(BaseHTTPRequestHandler):
    def setup(self):
        self.request.settimeout(5)
        super().setup()

    def address_string(self):
        return "nginx"

    def reply(self, status, data):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def respond(self, action):
        try:
            result = action()
        except (RuntimeError, OSError, subprocess.SubprocessError) as error:
            self.log_error("%s", error)
            self.reply(503, {"error": "serviceError"})
        except ValueError as error:
            self.reply(400, {"error": str(error)})
        else:
            self.reply(200, result)

    def do_GET(self):
        if self.path == API:
            self.respond(state)
        else:
            self.reply(404, {"error": "serviceError"})

    def do_POST(self):
        if self.path not in (API, API + "/restart"):
            self.reply(404, {"error": "serviceError"})
            return
        origin = self.headers.get("Origin")
        if not origin or origin != self.headers.get("X-Quarcs-Origin"):
            self.reply(403, {"error": "serviceError"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if self.headers.get_content_type() != "application/json" or not 0 < length <= 2048:
                raise ValueError
            data = json.loads(self.rfile.read(length))
            if not isinstance(data, dict):
                raise ValueError
        except (ValueError, OSError):
            self.reply(400, {"error": "invalidDrivers"})
            return
        if self.path == API:
            self.respond(lambda: save(data.get("drivers")))
        else:
            self.respond(restart)


class UnixHTTPServer(HTTPServer):
    address_family = socket.AF_UNIX


if __name__ == "__main__":
    if os.environ.get("LISTEN_FDS") != "1" or os.environ.get("LISTEN_PID") != str(os.getpid()):
        raise SystemExit("Start this program using quarcs-indi-startup.socket")
    with UnixHTTPServer("", Handler, bind_and_activate=False) as server:
        server.socket.close()
        server.socket = socket.socket(fileno=3)
        server.serve_forever()
