import unittest

from philips.asn1 import (
    ASN1,
    ASN1Error,
    TagClass,
    encode_identifier,
    encode_length,
    encode_signed_integer,
    hex_dump,
)


class EncodeLengthTests(unittest.TestCase):
    def test_short_length(self):
        self.assertEqual(encode_length(5), b"\x05")

    def test_largest_short_length(self):
        self.assertEqual(encode_length(127), b"\x7f")

    def test_long_length_128(self):
        self.assertEqual(encode_length(128), b"\x81\x80")

    def test_long_length_300(self):
        self.assertEqual(encode_length(300), b"\x82\x01\x2c")

    def test_negative_length_is_rejected(self):
        with self.assertRaises(ASN1Error):
            encode_length(-1)


class EncodeIdentifierTests(unittest.TestCase):
    def test_universal_primitive_short_tag(self):
        result = encode_identifier(
            tag_class=TagClass.UNIVERSAL,
            constructed=False,
            tag_number=4,
        )

        self.assertEqual(result, b"\x04")

    def test_application_constructed_short_tag(self):
        result = encode_identifier(
            tag_class=TagClass.APPLICATION,
            constructed=True,
            tag_number=0,
        )

        self.assertEqual(result, b"\x60")

    def test_context_constructed_high_tag_number(self):
        result = encode_identifier(
            tag_class=TagClass.CONTEXT,
            constructed=True,
            tag_number=31,
        )

        self.assertEqual(result, b"\xbf\x1f")


class SignedIntegerTests(unittest.TestCase):
    def test_zero(self):
        self.assertEqual(encode_signed_integer(0), b"\x00")

    def test_positive_without_sign_padding(self):
        self.assertEqual(encode_signed_integer(127), b"\x7f")

    def test_positive_with_sign_padding(self):
        self.assertEqual(encode_signed_integer(128), b"\x00\x80")

    def test_negative_one(self):
        self.assertEqual(encode_signed_integer(-1), b"\xff")

    def test_negative_128(self):
        self.assertEqual(encode_signed_integer(-128), b"\x80")

    def test_negative_129(self):
        self.assertEqual(encode_signed_integer(-129), b"\xff\x7f")


class ObjectIdentifierTests(unittest.TestCase):
    def test_common_oid(self):
        element = ASN1.object_identifier(
            1,
            2,
            840,
            10008,
            1,
        )

        self.assertEqual(
            element.encode(),
            bytes.fromhex("06 06 2A 86 48 CE 18 01"),
        )

    def test_oid_requires_two_components(self):
        with self.assertRaises(ASN1Error):
            ASN1.object_identifier(1)

    def test_invalid_first_component(self):
        with self.assertRaises(ASN1Error):
            ASN1.object_identifier(3, 1)

    def test_invalid_second_component_for_first_one(self):
        with self.assertRaises(ASN1Error):
            ASN1.object_identifier(1, 40)


class ConstructorTests(unittest.TestCase):
    def test_boolean_true(self):
        self.assertEqual(
            ASN1.boolean(True).encode(),
            b"\x01\x01\xff",
        )

    def test_integer(self):
        self.assertEqual(
            ASN1.integer(5).encode(),
            b"\x02\x01\x05",
        )

    def test_octet_string(self):
        self.assertEqual(
            ASN1.octet_string(b"ABC").encode(),
            b"\x04\x03ABC",
        )

    def test_null(self):
        self.assertEqual(
            ASN1.null().encode(),
            b"\x05\x00",
        )

    def test_sequence(self):
        element = ASN1.sequence(
            ASN1.integer(1),
            ASN1.null(),
        )

        self.assertEqual(
            element.encode(),
            bytes.fromhex("30 05 02 01 01 05 00"),
        )

    def test_set(self):
        element = ASN1.set(
            ASN1.integer(1),
        )

        self.assertEqual(
            element.encode(),
            bytes.fromhex("31 03 02 01 01"),
        )

    def test_explicit_context_tag(self):
        element = ASN1.context(
            0,
            ASN1.integer(5),
        )

        self.assertEqual(
            element.encode(),
            bytes.fromhex("A0 03 02 01 05"),
        )

    def test_implicit_primitive_context_tag(self):
        element = ASN1.context(
            1,
            b"ABC",
            constructed=False,
        )

        self.assertEqual(
            element.encode(),
            bytes.fromhex("81 03 41 42 43"),
        )

    def test_aarq_application_identifier(self):
        element = ASN1.application(
            0,
            ASN1.integer(1),
        )

        self.assertEqual(
            element.encode(),
            bytes.fromhex("60 03 02 01 01"),
        )


class HexDumpTests(unittest.TestCase):
    def test_hex_dump(self):
        result = hex_dump(b"ABC\x00", width=4)

        self.assertEqual(
            result,
            "0000  41 42 43 00  ABC.",
        )

    def test_invalid_width(self):
        with self.assertRaises(ASN1Error):
            hex_dump(b"ABC", width=0)


if __name__ == "__main__":
    unittest.main()