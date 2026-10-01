"""Reproduces 3A bug 3 (docs/checkin/BUGS_3A.md): work done by the 3A Store is not visible to other
connections until a later write commits. Marked xfail: it documents the defect without fixing it."""

import pytest
from checkin_fixtures import applied_schema, checkin_rt, clock, commit_3a, db  # noqa: F401  (fixtures)
from checkin_helpers import make_world


@pytest.mark.xfail(reason="3A bug 3: Store.transaction() leaves the transaction open after a read", strict=False)
def test_tickets_issued_by_the_3a_are_visible_to_other_connections(client, db, checkin_rt):
    make_world(client, db, commit=lambda: None)  # no commit: exactly what the 3A does
    assert db.execute("select count(*) as c from tickets").fetchone()["c"] == 1
