import struct
import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from gimbal_link import crc16, encode_command


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


if __name__ == "__main__":
    unittest.main()
