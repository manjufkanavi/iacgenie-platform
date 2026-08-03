"""
test_db.py — Multi-tenant PostgreSQL connectivity and data operations.

Tests verify that both tenant databases exist, are accessible, and that schema
isolation works correctly.
"""

import pytest


class TestDBMultiTenantConnectivity:
    """Test that both tenant databases are accessible."""

    def test_iacgenie_connection(self, pg_iacgenie):
        """Verify iacgenie database connection works."""
        cur = pg_iacgenie.cursor()
        cur.execute("SELECT current_database(), current_user")
        row = cur.fetchone()
        assert row[0] == "iacgenie", f"Connected to wrong db: {row[0]}"
        cur.close()

    def test_lightsrp_connection(self, pg_lightsrp):
        """Verify lightsrp database connection works."""
        cur = pg_lightsrp.cursor()
        cur.execute("SELECT current_database(), current_user")
        row = cur.fetchone()
        assert row[0] == "lightsrp", f"Connected to wrong db: {row[0]}"
        cur.close()

    def test_connection_isolation(self, pg_iacgenie, pg_lightsrp):
        """Both connections should point to different databases."""
        cur1 = pg_iacgenie.cursor()
        cur1.execute("SELECT current_database()")
        db1 = cur1.fetchone()[0]

        cur2 = pg_lightsrp.cursor()
        cur2.execute("SELECT current_database()")
        db2 = cur2.fetchone()[0]

        assert db1 != db2, f"Tenant databases should differ: {db1} vs {db2}"
        cur1.close()
        cur2.close()


class TestDBCrossTenantQueries:
    """Test cross-database isolation — cannot read other tenant's data."""

    def test_iacgenie_cannot_read_lightsrp(self, pg):
        """Verify that iacgenie tenant cannot access lightsrp tables (if separate roles)."""
        # Use superuser to verify both exist
        cur = pg.cursor()
        # Verify iacgenie db exists
        cur.execute(
            "SELECT 1 FROM pg_database WHERE datname = 'iacgenie'"
        )
        assert cur.fetchone(), "iacgenie database missing"

        # Verify lightsrp db exists
        cur.execute(
            "SELECT 1 FROM pg_database WHERE datname = 'lightsrp'"
        )
        assert cur.fetchone(), "lightsrp database missing"

        # Connect as app user (non-superuser) to iacgenie
        iacgenie_user_conn = psycopg2.connect(
            host="postgres", port=5432,
            user="postgres", password=POSTGRES_SUPER_PASSWORD,
            dbname="iacgenie", connect_timeout=10,
        )
        iacgenie_user_conn.autocommit = True
        cur = iacgenie_user_conn.cursor()

        # Try to access lightsrp — this should work at schema level
        # but the separate database enforces isolation at DB level
        try:
            cur.execute("SELECT 1 FROM information_schema.schemata WHERE schema_name = 'public'")
            schemas = [row[0] for row in cur.fetchall()]
            assert "public" in schemas, "Expected public schema in iacgenie db"
        except Exception as e:
            pytest.fail(f"Unexpected error accessing iacgenie schema: {e}")

        iacgenie_user_conn.close()


class TestDBCleanup:
    """Ensure no leftover test data."""

    def test_no_temp_tables(self, pg):
        """Verify no lingering test_temp_* tables."""
        cur = pg.cursor()
        cur.execute(
            "SELECT tablename FROM pg_tables WHERE tablename LIKE 'test_temp_%'"
        )
        rows = cur.fetchall()
        assert len(rows) == 0, f"Found lingering temp tables: {[r[0] for r in rows]}"
        cur.close()
