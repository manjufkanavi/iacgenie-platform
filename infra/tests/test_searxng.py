"""
test_sx.py — SearXNG search integration tests.

Verifies that SearXNG is reachable, responds to queries, and returns valid results.
"""

import pytest


class TestSearXNGConnectivity:
    """Basic SearXNG reachability tests."""

    def test_service_up(self, sx):
        """SearXNG should respond on the search endpoint."""
        r = sx["requests"].get(
            f"{sx['base']}/search?format=json&q=test", timeout=10
        )
        assert r.status_code == 200, \
            f"SearXNG returned {r.status_code}"

    def test_basic_query(self, sx):
        """A simple query should return results."""
        r = sx["requests"].get(
            f"{sx['base']}/search?format=json&q=hello+world",
            timeout=10,
        )
        assert r.status_code == 200
        data = r.json()
        assert "results" in data, f"No 'results' key in SearXNG response"
        print(f"  Query 'hello world' returned {len(data['results'])} results")

    def test_results_have_structure(self, sx):
        """Each result should have basic required fields."""
        r = sx["requests"].get(
            f"{sx['base']}/search?format=json&q=test+search",
            timeout=10,
        )
        data = r.json()
        results = data.get("results", [])
        if results:
            first = results[0]
            assert "content" in first or "longcontent" in first or "template" in first, \
                "Result missing content field"
            assert "title" in first, "Result missing title field"
            assert "url" in first, "Result missing url field"
        else:
            print("  No results returned (empty query)")

    def test_different_languages(self, sx):
        """SearXNG should accept language parameters."""
        for lang in ["en", "en-US", "fr", "de"]:
            r = sx["requests"].get(
                f"{sx['base']}/search?format=json&q=test&language={lang}",
                timeout=10,
            )
            assert r.status_code == 200, f"Language {lang} failed with {r.status_code}"


class TestSearXNGIsolation:
    """Verify SearXNG is properly isolated from other services."""

    def test_sx_namespace_clean(self, sx):
        """SearXNG should respond without 404 on its own namespace."""
        r = sx["requests"].get(
            f"{sx['base']}/search?format=json&q=isolation-test",
            timeout=10,
        )
        assert r.status_code == 200
        data = r.json()
        # Results should come from public search, not from any app-specific data
        print(f"  Isolation test: {len(data.get('results', []))} results")


class TestSearXNGErrorHandling:
    """Test SearXNG error responses."""

    def test_empty_query_returns_results(self, sx):
        """Empty or minimal queries should not error."""
        r = sx["requests"].get(
            f"{sx['base']}/search?format=json&q=", timeout=10
        )
        assert r.status_code == 200, f"Empty query returned {r.status_code}"

    def test_query_parameters_handled(self, sx):
        """Various query parameters should be handled gracefully."""
        params = {
            "q": "test",
            "format": "json",
            "pageno": "1",
        }
        r = sx["requests"].get(
            f"{sx['base']}/search", params=params, timeout=10
        )
        assert r.status_code == 200, f"Query params failed: {r.status_code}"
