from __future__ import annotations

import shlex
import shutil
import subprocess
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from .config import Settings


class ADBError(RuntimeError):
    pass


class Runner(Protocol):
    def run(
        self, args: list[str], timeout: int = 30
    ) -> subprocess.CompletedProcess[str]: ...


class SubprocessRunner:
    def run(
        self, args: list[str], timeout: int = 30
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(args, capture_output=True, text=True, timeout=timeout)


@dataclass(frozen=True)
class ADBCommand:
    args: list[str]

    def display(self) -> str:
        return " ".join(self.args)


class ADBLauncher:
    def __init__(
        self,
        settings: Settings,
        runner: Runner | None = None,
        step_timeout: float | None = None,
    ) -> None:
        self.settings = settings
        self.runner = runner or SubprocessRunner()
        self.step_timeout = (
            settings.launch_timeout_seconds if step_timeout is None else step_timeout
        )

    def check(self) -> str:
        self._require_config()
        self._require_adb()
        devices = self._adb(["devices", "-l"]).stdout
        state = self._device_state(devices)
        if state in {None, "offline"}:
            connect = self._adb(["connect", self.settings.adb_device or ""])
            if connect.returncode != 0:
                raise ADBError(
                    self._connection_error(connect.stderr or connect.stdout, devices)
                )
            devices = self._adb(["devices", "-l"]).stdout
            state = self._device_state(devices)
        if state != "device":
            raise ADBError(self._device_error(devices))
        model = self._device_adb(
            ["shell", "getprop", "ro.product.model"]
        ).stdout.strip()
        return f"connected to {self.settings.adb_device} ({model or 'unknown model'})"

    def dry_run_commands(self, url: str) -> list[ADBCommand]:
        self._require_config()
        return [
            ADBCommand(
                self._device_args(["shell", "input", "keyevent", "KEYCODE_WAKEUP"])
            ),
            ADBCommand(
                self._device_args(
                    ["shell", "am", "start", "-n", self.settings.shield_activity]
                )
            ),
            ADBCommand(
                self._device_args(["shell", "input", "keyevent", "KEYCODE_BACK"])
            ),
            ADBCommand(self._watch_intent_args(url)),
        ]

    def launch(self, url: str) -> None:
        self.check()
        self.ensure_plex()
        self.leave_player()
        result = self.runner.run(self._watch_intent_args(url), timeout=30)
        if result.returncode != 0:
            raise ADBError(result.stderr or result.stdout)
        self._wait_for("playback", lambda: self.player_state() == "started")

    def ensure_plex(self) -> None:
        if self.plex_in_front():
            return
        self._device_adb(["shell", "input", "keyevent", "KEYCODE_WAKEUP"])
        result = self._device_adb(
            ["shell", "am", "start", "-n", self.settings.shield_activity]
        )
        if result.returncode != 0:
            raise ADBError(result.stderr or result.stdout)
        self._wait_for("Plex in front", self.plex_in_front)

    def leave_player(self) -> None:
        deadline = time.monotonic() + self.step_timeout
        while self.player_state() is not None:
            if time.monotonic() >= deadline:
                raise ADBError(f"Player was still open after {self.step_timeout:g}s.")
            self._device_adb(["shell", "input", "keyevent", "KEYCODE_BACK"])
            time.sleep(0.4)

    def plex_in_front(self) -> bool:
        output = self._device_adb(["shell", "dumpsys", "window"]).stdout
        return any(
            "mCurrentFocus=" in line and f"{self.settings.shield_package}/" in line
            for line in output.splitlines()
        )

    def player_state(self) -> str | None:
        pid = self._device_adb(
            ["shell", "pidof", self.settings.shield_package]
        ).stdout.split()
        if not pid:
            return None
        needle = f"/{pid[0]} "
        found = None
        for line in self._device_adb(["shell", "dumpsys", "audio"]).stdout.splitlines():
            if (
                "AudioPlaybackConfiguration" not in line
                or "AudioTrack" not in line
                or needle not in line
            ):
                continue
            if "state:started" in line:
                return "started"
            if "state:paused" in line:
                found = "paused"
        return found

    def _wait_for(self, label: str, ready: Callable[[], bool]) -> None:
        deadline = time.monotonic() + self.step_timeout
        while True:
            if ready():
                return
            if time.monotonic() >= deadline:
                raise ADBError(
                    f"{label} was not reached within {self.step_timeout:g}s."
                )
            time.sleep(0.4)

    def _require_config(self) -> None:
        if not self.settings.adb_device:
            raise ADBError(
                "JPLEX_ADB_DEVICE is not set. Use a serial like 192.168.1.126:5555."
            )

    def _require_adb(self) -> None:
        if shutil.which(self.settings.adb_bin) is None:
            raise ADBError(
                "adb was not found. Install Android platform tools or set JPLEX_ADB_BIN."
            )

    def _adb(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        return self.runner.run([self.settings.adb_bin, *args], timeout=30)

    def _device_adb(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        return self.runner.run(self._device_args(args), timeout=30)

    def _device_args(self, args: list[str]) -> list[str]:
        return [self.settings.adb_bin, "-s", self.settings.adb_device or "", *args]

    def _watch_intent_args(self, url: str) -> list[str]:
        command = (
            "am start -a android.intent.action.VIEW -d "
            + shlex.quote(url)
            + " -n "
            + shlex.quote(self.settings.shield_activity)
        )
        return self._device_args(["shell", command])

    def _device_state(self, devices_output: str) -> str | None:
        for line in devices_output.splitlines():
            parts = line.split()
            if len(parts) >= 2 and parts[0] == self.settings.adb_device:
                return parts[1]
        return None

    def _connection_error(self, message: str, devices: str) -> str:
        if "refused" in message or "timed out" in message:
            return (
                "ADB could not connect. Enable SHIELD Developer Options -> Network debugging "
                "and check JPLEX_ADB_DEVICE.\n\n"
                f"adb devices -l:\n{devices}"
            )
        if "authenticate" in message.lower() or "unauthorized" in message.lower():
            return "ADB is unauthorized. Approve the debugging prompt on the SHIELD, then rerun jplex adb check."
        return f"ADB connection failed: {message}"

    def _device_error(self, devices: str) -> str:
        if "unauthorized" in devices:
            return "ADB device is unauthorized. Approve the debugging prompt on the SHIELD."
        return f"ADB device is not connected or is offline. Visible devices:\n{devices}"
