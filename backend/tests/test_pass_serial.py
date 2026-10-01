"""Regression test: two tickets of one order must never draw the same public reference."""

from store.pass_serial import next_pass_ref


class _Conn:
    """Stand-in connection: no ticket exists in the database yet (as while an order is minted)."""

    def execute(self, *_a):
        return self

    def fetchone(self):
        return None


def test_refs_drawn_for_one_order_are_unique(monkeypatch):
    monkeypatch.setattr("store.pass_serial.random_pass_suffix", lambda _it=iter([7, 7, 7, 8]): next(_it))
    taken: set[str] = set()
    refs = [next_pass_ref(None, _Conn(), 2026, taken) for _ in range(2)]
    assert refs == ["TDEV-2026-0007", "TDEV-2026-0008"]
