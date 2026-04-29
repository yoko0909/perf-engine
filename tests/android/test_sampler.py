from perfengine.android.adb_client import AdbClient
from perfengine.android.metrics import normalize_metric_point
from perfengine.android.sampler import AndroidSampler
from perfengine.android.status_provider import StatusProvider
from perfengine.app.models import AppInfo, DeviceInfo, PhoneStatus, SessionPhase
from perfengine.app.service import PerfToolService


class FakeCompletedProcess:
    def __init__(self, stdout: str, returncode: int = 0):
        self.stdout = stdout
        self.returncode = returncode
        self.stderr = ""


def fake_runner_factory(outputs):
    def _runner(cmd):
        key = " ".join(cmd)
        return FakeCompletedProcess(stdout=outputs.get(key, ""), returncode=0 if key in outputs else 1)

    return _runner


def test_normalize_metric_point_parses_cpu_memory_and_frame_text():
    status = PhoneStatus(
        connection_state="connected",
        device_label="Pixel 8",
        screen_state="on",
        app_state="running",
        battery_level=87,
        temperature_c=32.0,
        last_updated_at="2026-04-24T00:00:00Z",
    )

    point = normalize_metric_point(
        timestamp="2026-04-24T00:00:00Z",
        package_name="com.demo.app",
        cpu_output="12% TOTAL\n3.5% 1234/com.demo.app: 2.0% user + 1.5% kernel\n",
        memory_output="TOTAL PSS: 262144\n",
        frame_output="Average FPS: 58.3\nAverage frame time: 17.2ms\n",
        status=status,
    )

    assert point is not None
    assert point.total_cpu_percent == 12.0
    assert point.app_cpu_percent == 3.5
    assert point.memory_mb == 256.0
    assert point.fps == 58.3
    assert point.frame_time_ms == 17.2


def test_sampler_reads_status_and_metric_point():
    outputs = {
        "adb -s SERIAL1 shell dumpsys battery": "level: 87\ntemperature: 320\n",
        "adb -s SERIAL1 shell dumpsys power": "Display Power: state=ON\n",
        "adb -s SERIAL1 shell pidof com.demo.app": "2314\n",
        "adb -s SERIAL1 shell dumpsys cpuinfo": (
            "12% TOTAL\n"
            "3.5% 1234/com.demo.app: 2.0% user + 1.5% kernel\n"
        ),
        "adb -s SERIAL1 shell dumpsys meminfo com.demo.app": "TOTAL PSS: 262144\n",
        "adb -s SERIAL1 shell dumpsys gfxinfo com.demo.app": (
            "Average FPS: 58.3\n"
            "Average frame time: 17.2ms\n"
        ),
    }
    client = AdbClient(runner=fake_runner_factory(outputs))
    sampler = AndroidSampler(client, StatusProvider(client))

    sampler.begin("SERIAL1", "com.demo.app")
    status, point = sampler.read("SERIAL1", "com.demo.app")

    assert status.connection_state == "connected"
    assert point is not None
    assert point.fps == 58.3


class FakeDeviceProvider:
    def list_devices(self):
        return [DeviceInfo(device_id="SERIAL1", display_name="Pixel 8")]


class FakeAppProvider:
    def list_apps(self, device_id: str):
        return [AppInfo(package_name="com.demo.app", display_name="com.demo.app")]


class SequencedCollector:
    def __init__(self):
        self.index = 0

    def begin(self, device_id: str, package_name: str):
        return None

    def stop(self):
        return None

    def read(self, device_id: str, package_name: str):
        self.index += 1
        return (
            PhoneStatus(
                connection_state="connected",
                device_label="Pixel 8",
                screen_state="on",
                app_state="running",
                battery_level=80,
                temperature_c=31.0,
                last_updated_at=f"2026-04-24T00:00:{self.index:02d}Z",
            ),
            normalize_metric_point(
                timestamp=f"2026-04-24T00:00:{self.index:02d}Z",
                package_name="com.demo.app",
                cpu_output=f"12% TOTAL\n{self.index}% 1234/com.demo.app:\n",
                memory_output="TOTAL PSS: 102400\n",
                frame_output="Average FPS: 60\nAverage frame time: 16.6ms\n",
                status=PhoneStatus(
                    connection_state="connected",
                    device_label="Pixel 8",
                    screen_state="on",
                    app_state="running",
                    battery_level=80,
                    temperature_c=31.0,
                    last_updated_at="2026-04-24T00:00:00Z",
                ),
            ),
        )


def test_service_snapshot_history_is_trimmed_to_fixed_length():
    service = PerfToolService(
        device_provider=FakeDeviceProvider(),
        app_provider=FakeAppProvider(),
        collector=SequencedCollector(),
        history_limit=3,
    )

    service.start_session("SERIAL1", "com.demo.app")
    for _ in range(5):
        snapshot = service.get_live_snapshot()

    assert snapshot.session.phase is SessionPhase.RUNNING
    assert len(snapshot.metrics) == 3
    assert snapshot.metrics[-1].timestamp == "2026-04-24T00:00:05Z"
