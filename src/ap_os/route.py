from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from .schemas import RoutingDecision


@dataclass
class Approver:
    name: str
    email: str
    max_amount: float


def load_approvers(data_dir: Path) -> list[Approver]:
    approvers = []
    with open(data_dir / "approvers.csv", newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            approvers.append(Approver(row["approver_name"].strip(), row["approver_email"].strip(), float(row["max_amount"])))
    return sorted(approvers, key=lambda a: a.max_amount)


def route_invoice(amount: float, approvers: list[Approver]) -> tuple[RoutingDecision, bool]:
    """Returns (decision, over_all_thresholds)."""
    if not approvers:
        raise ValueError("No approvers configured in approvers.csv")

    for approver in approvers:
        if amount <= approver.max_amount:
            return (
                RoutingDecision(
                    approver_name=approver.name,
                    approver_email=approver.email,
                    reason=f"Amount ${amount:,.2f} is within {approver.name}'s approval limit of ${approver.max_amount:,.2f}.",
                ),
                False,
            )

    top = approvers[-1]
    return (
        RoutingDecision(
            approver_name=top.name,
            approver_email=top.email,
            reason=(
                f"Amount ${amount:,.2f} exceeds every configured approval limit "
                f"(highest is {top.name} at ${top.max_amount:,.2f}) - routed to them for manual sign-off."
            ),
        ),
        True,
    )
