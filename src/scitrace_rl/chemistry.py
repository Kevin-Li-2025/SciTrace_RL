from __future__ import annotations

import re
from dataclasses import dataclass


ATOMIC_WEIGHTS = {
    "B": 10.81,
    "C": 12.011,
    "F": 18.998,
    "H": 1.008,
    "Li": 6.94,
    "N": 14.007,
    "O": 15.999,
    "P": 30.974,
    "S": 32.06,
}


@dataclass(frozen=True)
class FormulaStats:
    formula: str
    atoms: dict[str, int]
    molecular_weight: float
    hetero_atom_count: int


def parse_formula(formula: str) -> dict[str, int]:
    """Parse simple chemical formulae used by this demo, e.g. C3H3FO3."""
    atoms: dict[str, int] = {}
    for element, count_text in re.findall(r"([A-Z][a-z]?)(\d*)", formula):
        if element not in ATOMIC_WEIGHTS:
            raise ValueError(f"Unsupported element in demo formula: {element}")
        atoms[element] = atoms.get(element, 0) + int(count_text or "1")
    if not atoms:
        raise ValueError(f"Invalid formula: {formula}")
    return atoms


def formula_stats(formula: str) -> FormulaStats:
    atoms = parse_formula(formula)
    molecular_weight = sum(ATOMIC_WEIGHTS[element] * count for element, count in atoms.items())
    hetero_atom_count = sum(count for element, count in atoms.items() if element not in {"C", "H"})
    return FormulaStats(
        formula=formula,
        atoms=atoms,
        molecular_weight=round(molecular_weight, 3),
        hetero_atom_count=hetero_atom_count,
    )

