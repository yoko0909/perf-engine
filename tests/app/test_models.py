from perfengine.app.errors import OperatorError
from perfengine.app.models import LiveSnapshot, PhoneStatus, SessionPhase, SessionState


def test_live_snapshot_uses_domain_defaults():
    snapshot = LiveSnapshot(
        session=SessionState(phase=SessionPhase.IDLE),
        status=PhoneStatus(last_updated_at="2026-04-24T00:00:00Z"),
    )

    assert snapshot.metrics == []
    assert snapshot.session.phase is SessionPhase.IDLE


def test_operator_error_keeps_user_facing_message():
    error = OperatorError(code="adb_unavailable", message="Android 设备通信不可用")

    assert error.code == "adb_unavailable"
    assert error.message == "Android 设备通信不可用"
    assert str(error) == "Android 设备通信不可用"
