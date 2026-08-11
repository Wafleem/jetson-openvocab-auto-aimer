"""Encode and send the 29-byte SP gimbal command over USB CDC."""

import os
import struct
import termios
import tty


PAYLOAD = struct.Struct("<2sB6f")
CRC = struct.Struct("<H")


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

    def send(self, mode: int, yaw_error: float = 0.0, pitch_error: float = 0.0) -> None:
        frame = encode_command(mode, yaw_error, pitch_error)
        written = 0
        while written < len(frame):
            written += os.write(self.fd, frame[written:])

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
