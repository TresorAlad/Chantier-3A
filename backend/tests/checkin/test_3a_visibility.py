"""Regression test for 3A bug 3 (docs/checkin/BUGS_3A.md, fixed): work done by the 3A Store must be visible
to other connections as soon as the request ends, not only after a later write commits."""

from checkin_fixtures import applied_schema, checkin_rt, clock, commit_3a, db  # noqa: F401  (fixtures)
from checkin_helpers import make_world


def test_tickets_issued_by_the_3a_are_visible_to_other_connections(client, db, checkin_rt):
    make_world(client, db, commit=lambda: None)  # no explicit commit: the Store must commit by itself
    assert db.execute("select count(*) as c from tickets").fetchone()["c"] == 1
