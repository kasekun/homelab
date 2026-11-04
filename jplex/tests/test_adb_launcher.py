from __future__ import annotations

import subprocess

import pytest

from jplex.adb_launcher import ADBError, ADBLauncher
from jplex.config import load_settings


Output = subprocess.CompletedProcess[str] | list[subprocess.CompletedProcess[str]]


class FakeRunner:
    def __init__(self, outputs: dict[tuple[str, ...], Output]) -> None:
        self.outputs = outputs
        self.calls: list[list[str]] = []

    def run(
        self, args: list[str], timeout: int = 30
    ) -> subprocess.CompletedProcess[str]:
        self.calls.append(args)
        key = tuple(args)
        if key not in self.outputs:
            raise AssertionError(f"unexpected command: {args!r}")
        output = self.outputs.get(key)
        if isinstance(output, list):
            if not output:
                raise AssertionError(f"unexpected repeated command: {args!r}")
            return output.pop(0)
        return output


def completed(
    args: list[str], stdout: str = "", stderr: str = "", returncode: int = 0
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args, returncode, stdout, stderr)


def settings():
    return load_settings(adb_bin="adb", adb_device="192.168.1.126")


def test_dry_run_contains_safe_adb_launch_command() -> None:
    commands = ADBLauncher(settings()).dry_run_commands(
        "https://watch.plex.tv/watch/video?uri=x&offset=0"
    )

    assert commands[-2].args == [
        "adb",
        "-s",
        "192.168.1.126:5555",
        "shell",
        "am start -a android.intent.action.VIEW -d https://watch.plex.tv/home -n com.plexapp.android/tv.plex.app.MainActivity",
    ]
    assert commands[-1].args == [
        "adb",
        "-s",
        "192.168.1.126:5555",
        "shell",
        "am start -a android.intent.action.VIEW -d 'https://watch.plex.tv/watch/video?uri=x&offset=0' -n com.plexapp.android/tv.plex.app.MainActivity",
    ]


def test_dry_run_seeds_details_page_when_provided() -> None:
    commands = ADBLauncher(settings()).dry_run_commands(
        "https://watch.plex.tv/watch/video?uri=x&offset=0",
        "https://watch.plex.tv/libraries/m/show/item/10",
    )

    assert [command.args[-1] for command in commands[-3:]] == [
        "am start -a android.intent.action.VIEW -d https://watch.plex.tv/home -n com.plexapp.android/tv.plex.app.MainActivity",
        "am start -a android.intent.action.VIEW -d https://watch.plex.tv/libraries/m/show/item/10 -n com.plexapp.android/tv.plex.app.MainActivity",
        "am start -a android.intent.action.VIEW -d 'https://watch.plex.tv/watch/video?uri=x&offset=0' -n com.plexapp.android/tv.plex.app.MainActivity",
    ]


def test_adb_check_accepts_space_separated_device_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("shutil.which", lambda _: "/usr/bin/adb")
    fake = FakeRunner(
        {
            (
                "adb",
                "devices",
                "-l",
            ): completed(
                [],
                "List of devices attached\n"
                "192.168.1.126:5555     device product:mdarcy model:SHIELD_Android_TV device:mdarcy transport_id:1\n",
            ),
            (
                "adb",
                "-s",
                "192.168.1.126:5555",
                "shell",
                "getprop",
                "ro.product.model",
            ): completed([], "SHIELD Android TV\n"),
        }
    )

    assert (
        ADBLauncher(settings(), fake).check()
        == "connected to 192.168.1.126:5555 (SHIELD Android TV)"
    )
    assert ["adb", "connect", "192.168.1.126:5555"] not in fake.calls


def test_adb_check_connects_once_when_device_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("shutil.which", lambda _: "/usr/bin/adb")
    fake = FakeRunner(
        {
            ("adb", "devices", "-l"): [
                completed([], "List of devices attached\n"),
                completed(
                    [],
                    "List of devices attached\n192.168.1.126:5555     device product:shield\n",
                ),
            ],
            ("adb", "connect", "192.168.1.126:5555"): completed(
                [], "connected to 192.168.1.126:5555\n"
            ),
            (
                "adb",
                "-s",
                "192.168.1.126:5555",
                "shell",
                "getprop",
                "ro.product.model",
            ): completed([], "SHIELD Android TV\n"),
        }
    )

    assert (
        ADBLauncher(settings(), fake).check()
        == "connected to 192.168.1.126:5555 (SHIELD Android TV)"
    )
    assert fake.calls.count(["adb", "connect", "192.168.1.126:5555"]) == 1


def test_adb_check_reconnects_once_when_device_offline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("shutil.which", lambda _: "/usr/bin/adb")
    fake = FakeRunner(
        {
            ("adb", "devices", "-l"): [
                completed(
                    [], "List of devices attached\n192.168.1.126:5555     offline\n"
                ),
                completed(
                    [],
                    "List of devices attached\n192.168.1.126:5555     device product:shield\n",
                ),
            ],
            ("adb", "connect", "192.168.1.126:5555"): completed(
                [], "already connected to 192.168.1.126:5555\n"
            ),
            (
                "adb",
                "-s",
                "192.168.1.126:5555",
                "shell",
                "getprop",
                "ro.product.model",
            ): completed([], "SHIELD Android TV\n"),
        }
    )

    assert (
        ADBLauncher(settings(), fake).check()
        == "connected to 192.168.1.126:5555 (SHIELD Android TV)"
    )


def test_launch_leaves_active_player_before_watch_intent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("shutil.which", lambda _: "/usr/bin/adb")
    monkeypatch.setattr("jplex.adb_launcher.time.sleep", lambda _: None)
    url = "https://watch.plex.tv/watch/video?uri=x&offset=0&shuffle=1"
    back = [
        "adb",
        "-s",
        "192.168.1.126:5555",
        "shell",
        "input",
        "keyevent",
        "KEYCODE_BACK",
    ]
    watch = [
        "adb",
        "-s",
        "192.168.1.126:5555",
        "shell",
        "am start -a android.intent.action.VIEW -d 'https://watch.plex.tv/watch/video?uri=x&offset=0&shuffle=1' -n com.plexapp.android/tv.plex.app.MainActivity",
    ]
    home = [
        "adb",
        "-s",
        "192.168.1.126:5555",
        "shell",
        "am start -a android.intent.action.VIEW -d https://watch.plex.tv/home -n com.plexapp.android/tv.plex.app.MainActivity",
    ]
    details = [
        "adb",
        "-s",
        "192.168.1.126:5555",
        "shell",
        "am start -a android.intent.action.VIEW -d https://watch.plex.tv/libraries/m/show/item/10 -n com.plexapp.android/tv.plex.app.MainActivity",
    ]
    fake = FakeRunner(
        {
            ("adb", "devices", "-l"): completed(
                [], "List of devices attached\n192.168.1.126:5555     device\n"
            ),
            (
                "adb",
                "-s",
                "192.168.1.126:5555",
                "shell",
                "getprop",
                "ro.product.model",
            ): completed([], "SHIELD Android TV\n"),
            (
                "adb",
                "-s",
                "192.168.1.126:5555",
                "shell",
                "dumpsys",
                "window",
            ): completed(
                [],
                "mCurrentFocus=Window{abc u0 com.plexapp.android/tv.plex.app.MainActivity}\n",
            ),
            (
                "adb",
                "-s",
                "192.168.1.126:5555",
                "shell",
                "pidof",
                "com.plexapp.android",
            ): [
                completed([], "123\n"),
                completed([], ""),
                completed([], "123\n"),
            ],
            (
                "adb",
                "-s",
                "192.168.1.126:5555",
                "shell",
                "dumpsys",
                "audio",
            ): [
                completed(
                    [],
                    "AudioPlaybackConfiguration player type:AudioTrack /123 state:started\n",
                ),
                completed(
                    [],
                    "AudioPlaybackConfiguration player type:AudioTrack /123 state:started\n",
                ),
            ],
            tuple(back): completed([]),
            tuple(watch): completed([]),
            tuple(home): completed([]),
            tuple(details): completed([]),
        }
    )

    ADBLauncher(settings(), fake).launch(
        url, "https://watch.plex.tv/libraries/m/show/item/10"
    )

    assert (
        fake.calls.index(back)
        < fake.calls.index(home)
        < fake.calls.index(details)
        < fake.calls.index(watch)
    )


def test_prepare_clears_stale_player_screen_without_audio(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("shutil.which", lambda _: "/usr/bin/adb")
    monkeypatch.setattr("jplex.adb_launcher.time.sleep", lambda _: None)
    home = [
        "adb",
        "-s",
        "192.168.1.126:5555",
        "shell",
        "am start -a android.intent.action.VIEW -d https://watch.plex.tv/home -n com.plexapp.android/tv.plex.app.MainActivity",
    ]
    fake = FakeRunner(
        {
            ("adb", "devices", "-l"): completed(
                [], "List of devices attached\n192.168.1.126:5555     device\n"
            ),
            (
                "adb",
                "-s",
                "192.168.1.126:5555",
                "shell",
                "getprop",
                "ro.product.model",
            ): completed([], "SHIELD Android TV\n"),
            (
                "adb",
                "-s",
                "192.168.1.126:5555",
                "shell",
                "dumpsys",
                "window",
            ): completed(
                [],
                "mCurrentFocus=Window{abc u0 com.plexapp.android/tv.plex.app.MainActivity}\n",
            ),
            (
                "adb",
                "-s",
                "192.168.1.126:5555",
                "shell",
                "pidof",
                "com.plexapp.android",
            ): completed([], ""),
            tuple(home): completed([]),
        }
    )

    ADBLauncher(settings(), fake).prepare()

    assert home in fake.calls


def test_adb_check_reports_missing_adb(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("shutil.which", lambda _: None)

    with pytest.raises(ADBError, match="adb was not found"):
        ADBLauncher(settings(), FakeRunner({})).check()


def test_adb_check_reports_unauthorized(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("shutil.which", lambda _: "/usr/bin/adb")
    fake = FakeRunner(
        {
            ("adb", "devices", "-l"): completed(
                [], "List of devices attached\n192.168.1.126:5555\tunauthorized\n"
            ),
        }
    )

    with pytest.raises(ADBError, match="unauthorized"):
        ADBLauncher(settings(), fake).check()
