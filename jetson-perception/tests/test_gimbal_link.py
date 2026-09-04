import struct
import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from gimbal_link import (
    TELEMETRY_COMMAND_AGE_UNKNOWN,
    TelemetryParser,
    crc16,
    decode_telemetry,
    encode_command,
)


class GimbalLinkTests(unittest.TestCase):
    def test_crc_check_value(self) -> None:
        self.assertEqual(crc16(b"123456789"), 0x6F91)

    def test_command_matches_sp_layout(self) -> None:
        frame = encode_command(1, -0.25, 0.5)

        self.assertEqual(len(frame), 29)
        self.assertEqual(frame[:3], b"SP\x01")
        self.assertEqual(struct.unpack_from("<f", frame, 3)[0], -0.25)
        self.assertEqual(struct.unpack_from("<f", frame, 15)[0], 0.5)
        self.assertEqual(frame[7:15], bytes(8))
        self.assertEqual(frame[19:27], bytes(8))
        self.assertEqual(struct.unpack_from("<H", frame, 27)[0], crc16(frame[:27]))

    def test_hold_is_all_zero_after_mode(self) -> None:
        frame = encode_command(0)

        self.assertEqual(frame[:3], b"SP\x00")
        self.assertEqual(frame[3:27], bytes(24))

    def test_invalid_mode_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            encode_command(3)

    def test_decodes_stm32_telemetry_golden_frame(self) -> None:
        frame = bytes.fromhex("535401010700c305f505110078563412058a")

        telemetry = decode_telemetry(frame)

        self.assertEqual(telemetry.mode, 1)
        self.assertEqual(telemetry.status_flags, 0x0007)
        self.assertEqual(telemetry.yaw_pulse_us, 1475)
        self.assertEqual(telemetry.pitch_pulse_us, 1525)
        self.assertEqual(telemetry.command_age_ms, 17)
        self.assertEqual(telemetry.sequence, 0x12345678)

    def test_unknown_telemetry_age_decodes_as_none(self) -> None:
        payload = struct.pack(
            "<2sBB4HI",
            b"ST",
            1,
            0,
            0,
            1500,
            1500,
            TELEMETRY_COMMAND_AGE_UNKNOWN,
            4,
        )
        telemetry = decode_telemetry(payload + struct.pack("<H", crc16(payload)))

        self.assertIsNone(telemetry.command_age_ms)

    def test_telemetry_parser_handles_splits_garbage_and_bad_crc(self) -> None:
        first = bytes.fromhex("535401010700c305f505110078563412058a")
        second_payload = struct.pack("<2sBB4HI", b"ST", 1, 0, 1, 1500, 1500, 250, 9)
        second = second_payload + struct.pack("<H", crc16(second_payload))
        bad = bytearray(first)
        bad[-1] ^= 0x80
        parser = TelemetryParser()

        self.assertEqual(parser.feed(b"noiseS" + first[:5]), [])
        decoded = parser.feed(first[5:] + bytes(bad) + second)

        self.assertEqual([item.sequence for item in decoded], [0x12345678, 9])

    def test_rejects_invalid_telemetry(self) -> None:
        valid = bytes.fromhex("535401010700c305f505110078563412058a")

        with self.assertRaises(ValueError):
            decode_telemetry(valid[:-1])
        with self.assertRaises(ValueError):
            decode_telemetry(b"XX" + valid[2:])
        corrupt = bytearray(valid)
        corrupt[8] ^= 1
        with self.assertRaises(ValueError):
            decode_telemetry(bytes(corrupt))


if __name__ == "__main__":
    unittest.main()
