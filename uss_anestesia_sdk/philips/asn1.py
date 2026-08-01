"""Codificador ASN.1 BER mínimo para Philips IntelliVue.

Implementa únicamente las primitivas necesarias para construir mensajes
ACSE como AARQ, AARE y RLRQ.

Referencia:
    ITU-T X.690 — Basic Encoding Rules (BER).

Este módulo no contiene ninguna constante ni estructura específica de
Philips IntelliVue.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import Iterable


class ASN1Error(ValueError):
    """Error al construir o codificar un elemento ASN.1."""


class TagClass(IntEnum):
    """Clases de tag ASN.1."""

    UNIVERSAL = 0
    APPLICATION = 1
    CONTEXT = 2
    PRIVATE = 3


class UniversalTag(IntEnum):
    """Tags universales que necesitaremos inicialmente."""

    BOOLEAN = 1
    INTEGER = 2
    BIT_STRING = 3
    OCTET_STRING = 4
    NULL = 5
    OBJECT_IDENTIFIER = 6
    SEQUENCE = 16
    SET = 17


@dataclass(frozen=True)
class Element:
    """Elemento ASN.1 ya preparado para serializarse."""

    tag_class: TagClass
    tag_number: int
    constructed: bool
    content: bytes

    def encode(self) -> bytes:
        """Serializa el elemento como Tag-Length-Value."""

        identifier = encode_identifier(
            tag_class=self.tag_class,
            constructed=self.constructed,
            tag_number=self.tag_number,
        )

        return identifier + encode_length(len(self.content)) + self.content

    def hex(self, separator: str = " ") -> str:
        """Devuelve la representación hexadecimal del elemento."""

        return self.encode().hex(separator)


def encode_identifier(
    *,
    tag_class: TagClass,
    constructed: bool,
    tag_number: int,
) -> bytes:
    """Codifica los octetos identificadores de un tag ASN.1.

    Admite tags de forma corta y de número alto.
    """

    if not isinstance(tag_number, int):
        raise TypeError("tag_number debe ser un entero")

    if tag_number < 0:
        raise ASN1Error("tag_number no puede ser negativo")

    first_octet = int(tag_class) << 6

    if constructed:
        first_octet |= 0x20

    # Forma corta: tag 0–30.
    if tag_number < 31:
        return bytes([first_octet | tag_number])

    # Forma de tag de número alto.
    first_octet |= 0x1F

    encoded_number = bytearray()
    value = tag_number

    while value:
        encoded_number.append(value & 0x7F)
        value >>= 7

    encoded_number.reverse()

    for index in range(len(encoded_number) - 1):
        encoded_number[index] |= 0x80

    return bytes([first_octet]) + bytes(encoded_number)


def encode_length(length: int) -> bytes:
    """Codifica una longitud ASN.1 BER definida.

    Ejemplos:
        5   -> 05
        127 -> 7f
        128 -> 81 80
        300 -> 82 01 2c
    """

    if not isinstance(length, int):
        raise TypeError("length debe ser un entero")

    if length < 0:
        raise ASN1Error("La longitud no puede ser negativa")

    if length < 0x80:
        return bytes([length])

    octets = length.to_bytes(
        (length.bit_length() + 7) // 8,
        byteorder="big",
    )

    if len(octets) > 126:
        raise ASN1Error("Longitud BER demasiado grande")

    return bytes([0x80 | len(octets)]) + octets


def encode_signed_integer(value: int) -> bytes:
    """Codifica un INTEGER con representación mínima en complemento a dos."""

    if not isinstance(value, int):
        raise TypeError("value debe ser un entero")

    if value == 0:
        return b"\x00"

    if value > 0:
        length = max(1, (value.bit_length() + 7) // 8)
        encoded = value.to_bytes(length, byteorder="big", signed=False)

        # Evita que el bit más alto haga parecer negativo al entero.
        if encoded[0] & 0x80:
            encoded = b"\x00" + encoded

        return encoded

    # Para negativos buscamos la representación signed mínima.
    length = 1

    while True:
        try:
            encoded = value.to_bytes(length, byteorder="big", signed=True)
        except OverflowError:
            length += 1
            continue

        if length == 1:
            return encoded

        # Elimina FF redundante cuando el siguiente byte ya conserva el signo.
        if encoded[0] == 0xFF and encoded[1] & 0x80:
            length -= 1
            continue

        return encoded


def encode_base128(value: int) -> bytes:
    """Codifica un entero no negativo en base 128 para OBJECT IDENTIFIER."""

    if value < 0:
        raise ASN1Error("Un componente OID no puede ser negativo")

    if value == 0:
        return b"\x00"

    octets = bytearray()

    while value:
        octets.append(value & 0x7F)
        value >>= 7

    octets.reverse()

    for index in range(len(octets) - 1):
        octets[index] |= 0x80

    return bytes(octets)


def join_encoded(elements: Iterable[Element | bytes]) -> bytes:
    """Concatena elementos ASN.1 y/o bloques de bytes."""

    output = bytearray()

    for element in elements:
        if isinstance(element, Element):
            output.extend(element.encode())
        elif isinstance(element, bytes):
            output.extend(element)
        else:
            raise TypeError(
                "Los elementos deben ser instancias de Element o bytes"
            )

    return bytes(output)


class ASN1:
    """Constructores para los tipos ASN.1 BER usados por IntelliVue."""

    @staticmethod
    def raw(
        *,
        tag_class: TagClass,
        tag_number: int,
        constructed: bool,
        content: bytes,
    ) -> Element:
        """Construye un elemento ASN.1 genérico."""

        if not isinstance(content, bytes):
            raise TypeError("content debe ser bytes")

        return Element(
            tag_class=tag_class,
            tag_number=tag_number,
            constructed=constructed,
            content=content,
        )

    @staticmethod
    def boolean(value: bool) -> Element:
        """Construye un BOOLEAN.

        BER permite cualquier valor distinto de cero para TRUE. Aquí usamos
        FF, que también es la representación canónica habitual.
        """

        if not isinstance(value, bool):
            raise TypeError("value debe ser bool")

        return Element(
            TagClass.UNIVERSAL,
            UniversalTag.BOOLEAN,
            False,
            b"\xFF" if value else b"\x00",
        )

    @staticmethod
    def integer(value: int) -> Element:
        """Construye un INTEGER firmado."""

        return Element(
            TagClass.UNIVERSAL,
            UniversalTag.INTEGER,
            False,
            encode_signed_integer(value),
        )

    @staticmethod
    def octet_string(data: bytes) -> Element:
        """Construye un OCTET STRING."""

        if not isinstance(data, bytes):
            raise TypeError("data debe ser bytes")

        return Element(
            TagClass.UNIVERSAL,
            UniversalTag.OCTET_STRING,
            False,
            data,
        )

    @staticmethod
    def null() -> Element:
        """Construye un valor NULL."""

        return Element(
            TagClass.UNIVERSAL,
            UniversalTag.NULL,
            False,
            b"",
        )

    @staticmethod
    def object_identifier(*components: int) -> Element:
        """Construye un OBJECT IDENTIFIER.

        Ejemplo:
            ASN1.object_identifier(1, 2, 840, 10008, 1)
        """

        if len(components) < 2:
            raise ASN1Error("Un OID requiere al menos dos componentes")

        first, second, *rest = components

        if first not in (0, 1, 2):
            raise ASN1Error("El primer componente OID debe ser 0, 1 o 2")

        if second < 0:
            raise ASN1Error("El segundo componente OID no puede ser negativo")

        if first < 2 and second > 39:
            raise ASN1Error(
                "Con primer componente 0 o 1, el segundo debe ser 0–39"
            )

        content = bytearray()
        content.extend(encode_base128(first * 40 + second))

        for component in rest:
            if not isinstance(component, int):
                raise TypeError("Los componentes OID deben ser enteros")

            content.extend(encode_base128(component))

        return Element(
            TagClass.UNIVERSAL,
            UniversalTag.OBJECT_IDENTIFIER,
            False,
            bytes(content),
        )

    @staticmethod
    def sequence(*elements: Element | bytes) -> Element:
        """Construye una SEQUENCE."""

        return Element(
            TagClass.UNIVERSAL,
            UniversalTag.SEQUENCE,
            True,
            join_encoded(elements),
        )

    @staticmethod
    def set(*elements: Element | bytes) -> Element:
        """Construye un SET."""

        return Element(
            TagClass.UNIVERSAL,
            UniversalTag.SET,
            True,
            join_encoded(elements),
        )

    @staticmethod
    def context(
        tag_number: int,
        *elements: Element | bytes,
        constructed: bool = True,
    ) -> Element:
        """Construye un tag específico de contexto.

        Para un elemento explícito construido:

            ASN1.context(0, ASN1.integer(5))

        produce:

            A0 03 02 01 05

        Para contenido primitivo implícito:

            ASN1.context(1, b"ABC", constructed=False)

        produce:

            81 03 41 42 43
        """

        return Element(
            TagClass.CONTEXT,
            tag_number,
            constructed,
            join_encoded(elements),
        )

    @staticmethod
    def application(
        tag_number: int,
        *elements: Element | bytes,
        constructed: bool = True,
    ) -> Element:
        """Construye un tag de clase APPLICATION.

        AARQ usa APPLICATION 0 construido, cuyo identificador es 0x60.
        """

        return Element(
            TagClass.APPLICATION,
            tag_number,
            constructed,
            join_encoded(elements),
        )

    @staticmethod
    def private(
        tag_number: int,
        *elements: Element | bytes,
        constructed: bool = True,
    ) -> Element:
        """Construye un tag de clase PRIVATE."""

        return Element(
            TagClass.PRIVATE,
            tag_number,
            constructed,
            join_encoded(elements),
        )


def hex_dump(data: bytes, width: int = 16) -> str:
    """Crea un volcado hexadecimal sencillo para depuración."""

    if width <= 0:
        raise ASN1Error("width debe ser mayor que cero")

    rows: list[str] = []

    for offset in range(0, len(data), width):
        chunk = data[offset : offset + width]
        hexadecimal = " ".join(f"{byte:02X}" for byte in chunk)
        ascii_text = "".join(
            chr(byte) if 32 <= byte <= 126 else "."
            for byte in chunk
        )

        rows.append(
            f"{offset:04X}  "
            f"{hexadecimal:<{width * 3 - 1}}  "
            f"{ascii_text}"
        )

    return "\n".join(rows)