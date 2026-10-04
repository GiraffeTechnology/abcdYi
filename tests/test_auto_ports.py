from __future__ import annotations

import os
import socket

from aivan.utils.ports import bind_listening_socket, record_port, reserved_ports, usable_port


def test_usable_port_rejects_reserved_and_invalid_values(monkeypatch):
    monkeypatch.setenv("RESERVED_PORTS", "9300,9301")
    assert reserved_ports() == {9300, 9301}
    assert usable_port("9300") is None
    assert usable_port("") is None
    assert usable_port("70000") is None
    assert usable_port("9302") == 9302


def test_auto_selection_binds_a_free_port():
    with bind_listening_socket("127.0.0.1") as sock:
        assert sock.getsockname()[1] != 0


def test_requested_reserved_port_is_never_bound(monkeypatch):
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        reserved = probe.getsockname()[1]
    monkeypatch.setenv("RESERVED_PORTS", str(reserved))
    with bind_listening_socket("127.0.0.1", reserved) as sock:
        assert sock.getsockname()[1] != reserved


def test_busy_requested_port_falls_back_to_another_free_port():
    with socket.socket() as busy:
        busy.bind(("127.0.0.1", 0))
        busy.listen()
        taken = busy.getsockname()[1]
        with bind_listening_socket("127.0.0.1", taken) as sock:
            assert sock.getsockname()[1] != taken


def test_record_port_publishes_environment_and_file(tmp_path, monkeypatch):
    port_file = tmp_path / "api.port"
    monkeypatch.setenv("API_PORT_FILE", str(port_file))
    monkeypatch.delenv("API_PORT", raising=False)
    record_port(40123, env_var="API_PORT", file_env_var="API_PORT_FILE")
    assert os.environ["API_PORT"] == "40123"
    assert port_file.read_text(encoding="utf-8").strip() == "40123"
