"""The ceiling on the two endpoints that reach out to Yahoo."""

from __future__ import annotations

from src.services import ratelimit


class TestWindow:
    def test_it_lets_the_first_calls_through(self):
        # Given an untouched window
        # When it is called up to the limit
        # Then every call is allowed
        assert all(ratelimit.allow("a", limit=3, now=0.0) for _ in range(3))

    def test_it_refuses_the_one_over(self):
        # Given a caller that used up its allowance
        for _ in range(3):
            ratelimit.allow("a", limit=3, now=0.0)
        # When it calls again inside the window
        # Then it is refused
        assert not ratelimit.allow("a", limit=3, now=0.5)

    def test_it_opens_again_once_the_window_has_passed(self):
        # Given a caller that used up its allowance
        for _ in range(3):
            ratelimit.allow("a", limit=3, window=60.0, now=0.0)
        # When the window has rolled past those calls
        # Then it may call again
        assert ratelimit.allow("a", limit=3, window=60.0, now=61.0)

    def test_it_slides_rather_than_resetting(self):
        # Given calls spread across a window
        for second in (0.0, 30.0, 59.0):
            ratelimit.allow("a", limit=3, window=60.0, now=second)
        # When only the oldest has fallen out
        # Then exactly one more call fits, and no more
        assert ratelimit.allow("a", limit=3, window=60.0, now=61.0)
        assert not ratelimit.allow("a", limit=3, window=60.0, now=62.0)

    def test_callers_are_counted_apart(self):
        # Given one caller that used up its allowance
        for _ in range(3):
            ratelimit.allow("a", limit=3, now=0.0)
        # When another one calls
        # Then it is unaffected
        assert ratelimit.allow("b", limit=3, now=0.0)

    def test_retry_after_points_past_the_oldest_call(self):
        # Given a caller whose oldest call was ten seconds ago
        ratelimit.allow("a", limit=1, window=60.0, now=0.0)
        # When it is told when to come back
        # Then it is after the window closes on that call
        assert ratelimit.retry_after("a", window=60.0, now=10.0) == 51

    def test_retry_after_falls_back_to_the_whole_window(self):
        # Given a caller nothing is known about
        # When it is told when to come back
        # Then it is given the full window rather than nothing
        assert ratelimit.retry_after("unknown", window=60.0) == 60


class TestEndpoints:
    def test_the_search_is_capped(self, client, mocker):
        # Given a search that is hammered
        mocker.patch.object(ratelimit, "allow", return_value=False)
        # When it is called
        response = client.get("/assets/search?q=world")
        # Then it is refused, with a hint of when to come back
        assert response.status_code == 429
        assert "Retry-After" in response.headers

    def test_the_chart_is_capped(self, client, portfolio_data, mocker):
        # Given a chart that is hammered
        mocker.patch.object(ratelimit, "allow", return_value=False)
        # When it is called
        response = client.get("/assets/WPEA.PA/chart")
        # Then it is refused too
        assert response.status_code == 429

    def test_the_cap_really_bites_after_enough_calls(self, client):
        # Given a real window rather than a stubbed one
        limit = ratelimit.DEFAULT_LIMIT
        # When the search is called past the ceiling
        codes = [client.get("/assets/search?q=x").status_code for _ in range(limit + 1)]
        # Then everything up to the limit passed, and the next did not
        assert codes[:limit] == [200] * limit
        assert codes[limit] == 429

    def test_the_rest_of_the_api_is_not_capped(self, client):
        # Given the endpoints that never leave the machine
        # When they are called far past the search ceiling
        codes = [client.get("/assets").status_code for _ in range(40)]
        # Then none of them is refused: only the Yahoo-facing ones are
        assert set(codes) == {200}
