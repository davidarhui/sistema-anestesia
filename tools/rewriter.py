"""
===============================================================================
USS Patch Engine - Source Rewriter
===============================================================================

Modificación quirúrgica de código fuente.

Usa rangos localizados mediante AST y sustituye únicamente el fragmento
seleccionado, preservando intacto el resto del archivo.

===============================================================================
"""

from __future__ import annotations

import ast
import textwrap

from tools.ast_tools import (
    ASTToolError,
    SourceRange,
    node_source_range,
    replace_range,
)


class RewriterError(RuntimeError):
    """Error durante una modificación de código fuente."""


def line_start_of_node(source: str, node: ast.AST) -> int:
    """Devuelve el offset donde comienza físicamente la línea del nodo."""

    source_range = node_source_range(source, node)

    line_start = source.rfind(
        "\n",
        0,
        source_range.start,
    )

    if line_start == -1:
        return 0

    return line_start + 1


def indentation_of_node(source: str, node: ast.AST) -> str:
    """
    Devuelve la indentación que precede al nodo en su línea.
    """

    source_range = node_source_range(source, node)
    line_start = line_start_of_node(source, node)

    prefix = source[line_start:source_range.start]

    if prefix.strip():
        raise RewriterError(
            "El nodo no comienza después de una indentación limpia."
        )

    return prefix


def indent_block(text: str, indentation: str) -> str:
    """
    Aplica una indentación base a un bloque de código.
    """

    clean = textwrap.dedent(text).strip("\n")

    if not clean:
        return ""

    return "\n".join(
        indentation + line if line else ""
        for line in clean.splitlines()
    )


def replace_node_code(
    source: str,
    node: ast.AST,
    replacement: str,
    *,
    auto_indent: bool = True,
) -> str:
    """
    Sustituye exactamente un nodo AST.

    Cuando auto_indent=True:
      - incluye en el reemplazo la indentación original del nodo;
      - sustituye desde el comienzo físico de la línea;
      - evita duplicar la indentación existente.
    """

    try:
        source_range = node_source_range(source, node)
    except ASTToolError as exc:
        raise RewriterError(str(exc)) from exc

    if auto_indent:
        indentation = indentation_of_node(
            source,
            node,
        )

        replacement = indent_block(
            replacement,
            indentation,
        )

        replacement_range = SourceRange(
            line_start_of_node(source, node),
            source_range.end,
        )

    else:
        replacement_range = source_range

    return replace_range(
        source,
        replacement_range,
        replacement,
    )


def insert_before_node(
    source: str,
    node: ast.AST,
    code: str,
) -> str:
    """
    Inserta código inmediatamente antes de un nodo,
    usando su misma indentación.
    """

    indentation = indentation_of_node(
        source,
        node,
    )

    block = indent_block(
        code,
        indentation,
    )

    if block:
        block += "\n"

    insertion_point = line_start_of_node(
        source,
        node,
    )

    return replace_range(
        source,
        SourceRange(
            insertion_point,
            insertion_point,
        ),
        block,
    )


def insert_after_node(
    source: str,
    node: ast.AST,
    code: str,
) -> str:
    """
    Inserta código inmediatamente después de un nodo,
    usando su misma indentación.
    """

    source_range = node_source_range(source, node)

    indentation = indentation_of_node(
        source,
        node,
    )

    block = indent_block(
        code,
        indentation,
    )

    if block:
        block = "\n" + block

    return replace_range(
        source,
        SourceRange(
            source_range.end,
            source_range.end,
        ),
        block,
    )
