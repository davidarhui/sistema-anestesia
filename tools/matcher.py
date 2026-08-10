"""
===============================================================================
USS Patch Engine - Structural Matcher
===============================================================================

Búsqueda semántica de nodos dentro de código Python.

Permite localizar estructuras por su AST, sin depender de:
- espacios,
- saltos de línea,
- comentarios,
- formato visual.

===============================================================================
"""

from __future__ import annotations

import ast
from typing import Iterator, TypeVar


class MatcherError(RuntimeError):
    """Error durante una búsqueda estructural."""


class MatchNotFoundError(MatcherError):
    """No se encontró el patrón solicitado."""


class AmbiguousMatchError(MatcherError):
    """Se encontraron varios nodos cuando se esperaba uno."""


T = TypeVar("T", bound=ast.AST)


def parse_expression(expression: str) -> ast.expr:
    """
    Convierte una expresión Python en AST.

    Ejemplo:
        fc_real is not None and not self.grafica.datos_sv
    """

    try:
        return ast.parse(
            expression,
            mode="eval",
        ).body
    except SyntaxError as exc:
        raise MatcherError(
            f"Expresión inválida: {expression!r}"
        ) from exc


def ast_equal(left: ast.AST, right: ast.AST) -> bool:
    """
    Compara dos nodos por estructura semántica,
    ignorando posiciones dentro del archivo.
    """

    return ast.dump(
        left,
        include_attributes=False,
    ) == ast.dump(
        right,
        include_attributes=False,
    )


def walk_scope(
    root: ast.AST,
    *,
    descend_into_nested_scopes: bool = False,
) -> Iterator[ast.AST]:
    """
    Recorre un nodo y sus descendientes.

    Por defecto NO entra en funciones, métodos, lambdas o clases
    anidadas dentro del scope principal.

    Esto evita que una búsqueda dentro de:

        recibir_muestra_monitor()

    encuentre accidentalmente un `if` perteneciente a la función
    interna `mostrar()`.
    """

    scope_nodes = (
        ast.FunctionDef,
        ast.AsyncFunctionDef,
        ast.ClassDef,
        ast.Lambda,
    )

    def visit(node: ast.AST, is_root: bool = False):
        yield node

        if (
            not is_root
            and not descend_into_nested_scopes
            and isinstance(node, scope_nodes)
        ):
            return

        for child in ast.iter_child_nodes(node):
            yield from visit(child)

    yield from visit(root, is_root=True)


def find_nodes(
    root: ast.AST,
    node_type: type[T],
    *,
    descend_into_nested_scopes: bool = False,
) -> list[T]:
    """Encuentra nodos de un tipo concreto dentro de un scope."""

    return [
        node
        for node in walk_scope(
            root,
            descend_into_nested_scopes=descend_into_nested_scopes,
        )
        if isinstance(node, node_type)
    ]


def find_ifs_by_test(
    root: ast.AST,
    expression: str,
    *,
    descend_into_nested_scopes: bool = False,
) -> list[ast.If]:
    """
    Encuentra IF cuya condición sea estructuralmente equivalente
    a la expresión proporcionada.
    """

    wanted = parse_expression(expression)

    matches = []

    for node in find_nodes(
        root,
        ast.If,
        descend_into_nested_scopes=descend_into_nested_scopes,
    ):
        if ast_equal(node.test, wanted):
            matches.append(node)

    return matches


def find_unique_if(
    root: ast.AST,
    expression: str,
    *,
    descend_into_nested_scopes: bool = False,
) -> ast.If:
    """
    Encuentra exactamente un IF por su condición.

    Falla si no existe o si hay más de uno.
    """

    matches = find_ifs_by_test(
        root,
        expression,
        descend_into_nested_scopes=descend_into_nested_scopes,
    )

    if not matches:
        raise MatchNotFoundError(
            "No encontré ningún IF con la condición:\n"
            f"    {expression}"
        )

    if len(matches) > 1:
        raise AmbiguousMatchError(
            f"Encontré {len(matches)} IF con la condición:\n"
            f"    {expression}"
        )

    return matches[0]
