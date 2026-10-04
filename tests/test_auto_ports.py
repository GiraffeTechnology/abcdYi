from __future__ import annotations

import os
import socket

from aivan.utils.ports import RESERVED_PORT, bind_listening_socket, record_port, usable_port


def test_usable_port_rejects_443_and_invalid_values():
    assert usable_port("443") is None
    assert usable_port("") is None
    assert usable_port("70000") is None
    assert usable_port("8443") == 8443


def test_auto_selection_binds_a_free_non_443_port():
    with bind_listening_socket("127.0.0.1") as sock:
        assert sock.getsockname()[1] not in (0, RESERVED_PORT)


def test_requested_443_is_never_bound():
    with bind_listening_socket("127.0.0.1", "443") as sock:
        assert sock.getsockname()[1] != RESERVED_PORT


def test_busy_requested_port_falls_back_to_another_free_port():
    with socket.socket() as busy:
        busy.bind(("127.0.0.1", 0))
        busy.listen()
        taken = busy.getsockname()[1]
        with bind_listening_socket("127.0.0.1", taken) as sock:
            assert sock.getsockname()[1] not in (taken, RESERVED_PORT)


def test_record_port_publishes_environment_and_file(tmp_path, monkeypatch):
    port_file = tmp_path / "api.port"
    monkeypatch.setenv("API_PORT_FILE", str(port_file))
    monkeypatch.delenv("API_PORT", raising=False)
    record_port(40123, env_var="API_PORT", file_env_var="API_PORT_FILE")
    assert os.environ["API_PORT"] == "40123"
    assert port_file.read_text(encoding="utf-8").strip() == "40123"
