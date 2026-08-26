"""Encode and send the 29-byte SP gimbal command over USB CDC."""

from __future__ import annotations

import os
import select
import struct
import termios
import tty
from dataclasses import dataclass


PAYLOAD = struct.Struct("<2sB6f")
CRC = struct.Struct("<H")
TELEMETRY = struct.Struct("<2sBB4HIH")
TELEMETRY_VERSION = 1
TELEMETRY_STATUS_USB_CONNECTED = 1 << 0
TELEMETRY_STATUS_COMMAND_FRESH = 1 << 1
TELEMETRY_STATUS_TRACKING_ACTIVE = 1 << 2
TELEMETRY_STATUS_YAW_SATURATED = 1 << 3
TELEMETRY_STATUS_PITCH_SATURATED = 1 << 4
TELEMETRY_COMMAND_AGE_UNKNOWN = 0xFFFF


@dataclass(frozen=True)
class GimbalTelemetry:
    mode: int
    status_flags: int
    yaw_pulse_us: int
    pitch_pulse_us: int
    command_age_ms: int | None
    sequence: int


def crc16(data: bytes) -> int:
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = (crc >> 1) ^ 0x8408 if crc & 1 else crc >> 1
    return crc


def encode_command(mode: int, yaw_error: float = 0.0, pitch_error: float = 0.0) -> bytes:
    if mode not in (0, 1, 2):
        raise ValueError("Gimbal mode must be 0, 1, or 2")

    payload = PAYLOAD.pack(
        b"SP",
        mode,
        yaw_error,
        0.0,
        0.0,
        pitch_error,
        0.0,
        0.0,
    )
    return payload + CRC.pack(crc16(payload))


def decode_telemetry(frame: bytes) -> GimbalTelemetry:
    if len(frame) != TELEMETRY.size:
        raise ValueError(f"Telemetry frame must be {TELEMETRY.size} bytes")

    (
        header,
        version,
        mode,
        status_flags,
        yaw_pulse_us,
        pitch_pulse_us,
        command_age_ms,
        sequence,
        received_crc,
    ) = TELEMETRY.unpack(frame)
    if header != b"ST":
        raise ValueError("Invalid telemetry header")
    if version != TELEMETRY_VERSION:
        raise ValueError(f"Unsupported telemetry version: {version}")
    if mode not in (0, 1, 2):
        raise ValueError(f"Invalid telemetry mode: {mode}")
    if received_crc != crc16(frame[:-CRC.size]):
        raise ValueError("Invalid telemetry CRC")

    return GimbalTelemetry(
        mode=mode,
        status_flags=status_flags,
        yaw_pulse_us=yaw_pulse_us,
        pitch_pulse_us=pitch_pulse_us,
        command_age_ms=(
            None if command_age_ms == TELEMETRY_COMMAND_AGE_UNKNOWN else command_age_ms
        ),
        sequence=sequence,
    )


class TelemetryParser:
    def __init__(self) -> None:
        self._buffer = bytearray()

    def feed(self, data: bytes) -> list[GimbalTelemetry]:
        self._buffer.extend(data)
        decoded = []

        while True:
            header = self._buffer.find(b"ST")
            if header < 0:
                self._buffer[:] = self._buffer[-1:] if self._buffer.endswith(b"S") else b""
                break
            if header:
                del self._buffer[:header]
            if len(self._buffer) < TELEMETRY.size:
                break

            frame = bytes(self._buffer[: TELEMETRY.size])
            try:
                telemetry = decode_telemetry(frame)
            except ValueError:
                del self._buffer[0]
                continue

            decoded.append(telemetry)
            del self._buffer[: TELEMETRY.size]

        return decoded


class GimbalLink:
    def __init__(self, device: str) -> None:
        self.device = device
        self.fd = os.open(device, os.O_RDWR | os.O_NOCTTY)
        try:
            tty.setraw(self.fd, termios.TCSANOW)
        except Exception:
            os.close(self.fd)
            self.fd = -1
            raise
        self._telemetry_parser = TelemetryParser()

    def send(self, mode: int, yaw_error: float = 0.0, pitch_error: float = 0.0) -> None:
        frame = encode_command(mode, yaw_error, pitch_error)
        written = 0
        while written < len(frame):
            written += os.write(self.fd, frame[written:])

    def read_available_telemetry(self) -> list[GimbalTelemetry]:
        telemetry = []
        while self.fd >= 0 and select.select([self.fd], [], [], 0.0)[0]:
            chunk = os.read(self.fd, 256)
            if not chunk:
                break
            telemetry.extend(self._telemetry_parser.feed(chunk))
        return telemetry

    def close(self) -> None:
        if self.fd < 0:
            return
        try:
            try:
                self.send(0)
                termios.tcdrain(self.fd)
            except OSError:
                pass
        finally:
            os.close(self.fd)
            self.fd = -1

    def __enter__(self) -> "GimbalLink":
        return self

    def __exit__(self, _type: object, _value: object, _traceback: object) -> None:
        self.close()
