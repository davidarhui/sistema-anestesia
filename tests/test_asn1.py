import unittest

from philips_intellivue.asn1 import (
    ASN1,
    ASN1Error,
    TagClass,
    encode_identifier,
    encode_length,
    encode_signed_integer,
    hex_dump,
)


class TestBERLength(unittest.TestCase):

    def test_short_form(self):
        self.assertEqual(encode_length(0), b"\x00")
        self.assertEqual(encode_length(5), b"\x05")
        self.assertEqual(encode_length(127), b"\x7F")

    def test_long_form(self):
        self.assertEqual(encode_length(128), b"\x81\x80")
        self.assertEqual(encode_length(200), b"\x81\xC8")
        self.assertEqual(encode_length(300), b"\x82\x01\x2C")


class TestBERIdentifier(unittest.TestCase):

    def test_universal_sequence(self):
        encoded = encode_identifier(
            tag_class=TagClass.UNIVERSAL,
            constructed=True,
            tag_number=16,
        )
        self.assertEqual(encoded, b"\x30")

    def test_application_zero(self):
        encoded = encode_identifier(
            tag_class=TagClass.APPLICATION,
            constructed=True,
            tag_number=0,
        )
        self.assertEqual(encoded, b"\x60")

    def test_context_zero(self):
        encoded = encode_identifier(
            tag_class=TagClass.CONTEXT,
            constructed=True,
            tag_number=0,
        )
        self.assertEqual(encoded, b"\xA0")


class TestBERInteger(unittest.TestCase):

    def test_integer_content(self):
        self.assertEqual(encode_signed_integer(0), b"\x00")
        self.assertEqual(encode_signed_integer(5), b"\x05")
        self.assertEqual(encode_signed_integer(127), b"\x7F")
        self.assertEqual(encode_signed_integer(128), b"\x00\x80")
        self.assertEqual(encode_signed_integer(-1), b"\xFF")
        self.assertEqual(encode_signed_integer(-128), b"\x80")
        self.assertEqual(encode_signed_integer(-129), b"\xFF\x7F")

    def test_integer_tlv(self):
        self.assertEqual(
            ASN1.integer(5).encode(),
            bytes.fromhex("02 01 05"),
        )

        self.assertEqual(
            ASN1.integer(128).encode(),
            bytes.fromhex("02 02 00 80"),
        )


class TestBERElements(unittest.TestCase):

    def test_boolean(self):
        self.assertEqual(
            ASN1.boolean(False).encode(),
            bytes.fromhex("01 01 00"),
        )

        self.assertEqual(
            ASN1.boolean(True).encode(),
            bytes.fromhex("01 01 FF"),
        )

    def test_octet_string(self):
        self.assertEqual(
            ASN1.octet_string(b"ABC").encode(),
            bytes.fromhex("04 03 41 42 43"),
        )

    def test_null(self):
        self.assertEqual(
            ASN1.null().encode(),
            bytes.fromhex("05 00"),
        )

    def test_sequence(self):
        element = ASN1.sequence(
            ASN1.integer(5),
            ASN1.integer(8),
        )

        self.assertEqual(
            element.encode(),
            bytes.fromhex(
                "30 06 "
                "02 01 05 "
                "02 01 08"
            ),
        )

    def test_context_explicit(self):
        element = ASN1.context(
            0,
            ASN1.integer(5),
        )

        self.assertEqual(
            element.encode(),
            bytes.fromhex("A0 03 02 01 05"),
        )

    def test_context_primitive(self):
        element = ASN1.context(
            1,
            b"ABC",
            constructed=False,
        )

        self.assertEqual(
            element.encode(),
            bytes.fromhex("81 03 41 42 43"),
        )

    def test_aarq_outer_tag(self):
        element = ASN1.application(
            0,
            ASN1.context(
                1,
                ASN1.object_identifier(1, 2, 3),
            ),
        )

        encoded = element.encode()

        # APPLICATION 0 construido = AARQ = 0x60.
        self.assertEqual(encoded[0], 0x60)

    def test_object_identifier(self):
        self.assertEqual(
            ASN1.object_identifier(1, 2, 3).encode(),
            bytes.fromhex("06 02 2A 03"),
        )


if __name__ == "__main__":
    unittest.main()