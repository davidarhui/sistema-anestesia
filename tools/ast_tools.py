"""
===============================================================================
USS Patch Engine - AST Tools
===============================================================================

Herramientas estructurales para localizar código Python sin depender
del formato, espacios o comentarios.

IMPORTANTE:
    Este módulo usa AST para LOCALIZAR código, no para regenerar archivos
    completos con ast.unparse().

    Las modificaciones se realizan únicamente sobre rangos concretos del
    texto original, preservando el resto del archivo byte por byte.

===============================================================================
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import Iterable, Optional


class ASTToolError(RuntimeError):
    """Error durante una operación estructural sobre código Python."""


class NodeNotFoundError(ASTToolError):
    """No se encontró el nodo solicitado."""


class AmbiguousNodeError(ASTToolError):
    """Se encontraron varios nodos cuando se esperaba uno solo."""


@dataclass(frozen=True)
class SourceRange:
    """
    Rango de caracteres dentro del texto fuente.

    start es inclusivo.
    end es exclusivo.
    """

    start: int
    end: int

    def extract(self, source: str) -> str:
        return source[self.start:self.end]


def parse_python(source: str, filename: str = "<string>") -> ast.Module:
    """Convierte código Python en AST."""

    try:
        return ast.parse(source, filename=filename)
    except SyntaxError as exc:
        raise ASTToolError(
            f"No se pudo analizar {filename}: {exc}"
        ) from exc


def _line_offsets(source: str) -> list[int]:
    """
    Devuelve el offset absoluto donde inicia cada línea.

    El índice 0 corresponde a la línea 1.
    """

    offsets = [0]

    for index, char in enumerate(source):
        if char == "\n":
            offsets.append(index + 1)

    return offsets


def node_source_range(
    source: str,
    node: ast.AST,
) -> SourceRange:
    """
    Obtiene el rango exacto de caracteres correspondiente a un nodo AST.

    Requiere lineno, col_offset, end_lineno y end_col_offset.
    Python 3.9+ los proporciona para los nodos relevantes.
    """

    required = (
        "lineno",
        "col_offset",
        "end_lineno",
        "end_col_offset",
    )

    if not all(hasattr(node, attr) for attr in required):
        raise ASTToolError(
            f"El nodo {type(node).__name__} no contiene "
            "información completa de posición."
        )

    offsets = _line_offsets(source)

    start_line = node.lineno - 1
    end_line = node.end_lineno - 1

    try:
        start = offsets[start_line] + node.col_offset
        end = offsets[end_line] + node.end_col_offset
    except IndexError as exc:
        raise ASTToolError(
            "Las posiciones AST no corresponden con el texto fuente."
        ) from exc

    return SourceRange(start=start, end=end)


def node_source(source: str, node: ast.AST) -> str:
    """Devuelve el texto original correspondiente a un nodo."""

    return node_source_range(source, node).extract(source)


def find_functions(
    tree: ast.AST,
    name: str,
) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
    """Encuentra funciones o métodos por nombre."""

    found = []

    for node in ast.walk(tree):
        if isinstance(
            node,
            (ast.FunctionDef, ast.AsyncFunctionDef),
        ):
            if node.name == name:
                found.append(node)

    return found


def find_function(
    tree: ast.AST,
    name: str,
) -> ast.FunctionDef | ast.AsyncFunctionDef:
    """
    Encuentra exactamente una función o método por nombre.

    Falla si no existe o si hay varias.
    """

    found = find_functions(tree, name)

    if not found:
        raise NodeNotFoundError(
            f"No encontré ninguna función llamada {name!r}."
        )

    if len(found) > 1:
        raise AmbiguousNodeError(
            f"Encontré {len(found)} funciones llamadas {name!r}."
        )

    return found[0]


def find_class(
    tree: ast.AST,
    name: str,
) -> ast.ClassDef:
    """Encuentra exactamente una clase por nombre."""

    found = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.ClassDef)
        and node.name == name
    ]

    if not found:
        raise NodeNotFoundError(
            f"No encontré ninguna clase llamada {name!r}."
        )

    if len(found) > 1:
        raise AmbiguousNodeError(
            f"Encontré {len(found)} clases llamadas {name!r}."
        )

    return found[0]


def find_method(
    tree: ast.AST,
    class_name: str,
    method_name: str,
) -> ast.FunctionDef | ast.AsyncFunctionDef:
    """
    Encuentra exactamente un método dentro de una clase concreta.
    """

    cls = find_class(tree, class_name)

    found = [
        node
        for node in cls.body
        if isinstance(
            node,
            (ast.FunctionDef, ast.AsyncFunctionDef),
        )
        and node.name == method_name
    ]

    if not found:
        raise NodeNotFoundError(
            f"No encontré {class_name}.{method_name}()."
        )

    if len(found) > 1:
        raise AmbiguousNodeError(
            f"Encontré varias definiciones de "
            f"{class_name}.{method_name}()."
        )

    return found[0]


def replace_range(
    source: str,
    source_range: SourceRange,
    replacement: str,
) -> str:
    """
    Sustituye exclusivamente un rango del texto fuente.
    """

    if source_range.start < 0:
        raise ASTToolError("start no puede ser negativo.")

    if source_range.end < source_range.start:
        raise ASTToolError("Rango de fuente inválido.")

    if source_range.end > len(source):
        raise ASTToolError(
            "El rango excede la longitud del archivo."
        )

    return (
        source[:source_range.start]
        + replacement
        + source[source_range.end:]
    )


def replace_node(
    source: str,
    node: ast.AST,
    replacement: str,
) -> str:
    """
    Sustituye exactamente el código ocupado por un nodo AST.
    """

    return replace_range(
        source,
        node_source_range(source, node),
        replacement,
    )
