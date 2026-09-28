"""Organizer payout bank details (encrypted at rest when vault unlocked)."""

from __future__ import annotations

from dataclasses import dataclass

from store.store import NotFoundError, Store


@dataclass
class BankAccount:
    """Bankaccount."""
    org_id: str
    bank_code: str
    account_number: str
    account_name: str


def get_bank_account(st: Store, org_id: str) -> BankAccount:
    """Get bank account."""
    row = st.fetchone(
        """
        SELECT org_id, bank_code, account_number, account_name
        FROM org_bank_accounts WHERE org_id = ?
        """,
        (org_id,),
    )
    if row is None:
        raise NotFoundError()
    if hasattr(row, "keys"):
        return BankAccount(
            org_id=row["org_id"],
            bank_code=row["bank_code"],
            account_number=row["account_number"],
            account_name=row["account_name"],
        )
    return BankAccount(org_id=row[0], bank_code=row[1], account_number=row[2], account_name=row[3])


def set_bank_account(st: Store, acct: BankAccount) -> None:
    """Set bank account."""
    st.execute("DELETE FROM org_bank_accounts WHERE org_id = ?", (acct.org_id,))
    st.execute(
        """
        INSERT INTO org_bank_accounts (org_id, bank_code, account_number, account_name)
        VALUES (?, ?, ?, ?)
        """,
        (acct.org_id, acct.bank_code, acct.account_number, acct.account_name),
    )
