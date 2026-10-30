"""
LogicFlow Symbol Table
Tracks variable names and their inferred types.
"""
from .errors import SemanticError


class SymbolTable:
    """
    A simple symbol table that records variables and their inferred types.
    Type inference rules:
      - SET x TO <number literal>   -> 'number'
      - SET x TO <string literal>   -> 'string'
      - SET x TO <expr>             -> type inferred from expr (may be 'unknown')
      - ASK FOR x                   -> 'any' (type determined at runtime)
    """

    def __init__(self):
        self._table: dict[str, dict] = {}

    def declare(self, name: str, inferred_type: str = 'any', line: int = None):
        self._table[name] = {'type': inferred_type, 'line': line}

    def update_type(self, name: str, inferred_type: str):
        if name in self._table:
            self._table[name]['type'] = inferred_type

    def lookup(self, name: str) -> dict | None:
        return self._table.get(name)

    def is_defined(self, name: str) -> bool:
        return name in self._table

    def all_symbols(self) -> dict:
        return dict(self._table)

    def to_dict(self) -> dict:
        return {name: info for name, info in self._table.items()}
