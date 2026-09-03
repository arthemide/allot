"""The /note endpoints: the note as text, and the calendar feed."""

from __future__ import annotations


class TestNote:
    def test_the_note_is_served_as_plain_text(self, client, portfolio_data):
        # Given a funded envelope with two assets
        # When the note is read
        response = client.get("/note")
        # Then it is text, not JSON, so it can be pasted straight into a reminder
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/plain")
        assert "PEA - 300 " in response.text
        assert "WPEA.PA" in response.text

    def test_every_line_links_back_to_the_app_that_served_it(
        self, client, portfolio_data
    ):
        # Given the note read over some host
        text = client.get("/note").text
        # Then the links point at that same host: there is no configured
        # public URL, and a link to 127.0.0.1 would be useless on a phone
        assert "http://testserver/?asset=WPEA.PA" in text

    def test_the_note_is_recomputed_on_every_request(
        self, client, portfolio_data, mocker
    ):
        # Given the note rendered once
        render = mocker.patch("src.services.note.render", return_value="note")
        # When it is read twice
        assert client.get("/note").text == "note"
        assert client.get("/note").text == "note"
        # Then nothing was memoised between the two
        assert render.call_count == 2

    def test_an_empty_portfolio_still_renders_a_note(self, client):
        # Given nothing tracked at all
        # When the note is read
        text = client.get("/note").text
        # Then it says so rather than failing
        assert "Aucune transaction saisie." in text


class TestFeed:
    def test_the_feed_is_served_as_a_calendar(self, client, portfolio_data):
        # Given a funded envelope
        # When the feed is fetched
        response = client.get("/note.ics")
        # Then it is a calendar a client can subscribe to
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/calendar")
        assert response.text.startswith("BEGIN:VCALENDAR")
        assert response.text.count("BEGIN:VEVENT") == 12

    def test_a_calendar_client_gets_in_with_the_feed_token(
        self, guarded_client, monkeypatch
    ):
        # Given a feed token, and a client with no session
        monkeypatch.setenv("ALLOT_FEED_TOKEN", "a-long-random-token")
        # When it fetches the feed with the token in the URL
        response = guarded_client.get("/note.ics?feed=a-long-random-token")
        # Then it is served: a calendar cannot log in
        assert response.status_code == 200
        assert response.text.startswith("BEGIN:VCALENDAR")

    def test_a_wrong_token_gets_nothing(self, guarded_client, monkeypatch):
        monkeypatch.setenv("ALLOT_FEED_TOKEN", "a-long-random-token")
        assert guarded_client.get("/note.ics?feed=wrong").status_code == 401

    def test_no_token_configured_leaves_the_feed_behind_the_session(
        self, guarded_client
    ):
        # Given no ALLOT_FEED_TOKEN: the default is closed
        assert guarded_client.get("/note.ics?feed=").status_code == 401
        assert guarded_client.get("/note.ics").status_code == 401

    def test_the_note_itself_still_needs_a_session(self, guarded_client, monkeypatch):
        # Given a feed token, which opens the feed and nothing else
        monkeypatch.setenv("ALLOT_FEED_TOKEN", "a-long-random-token")
        assert guarded_client.get("/note?feed=a-long-random-token").status_code == 401
        assert guarded_client.get("/assets?feed=a-long-random-token").status_code == 401


class TestFeedUrl:
    def test_it_hands_out_the_address_to_subscribe_to(self, client, portfolio_data):
        body = client.get("/note/feed-url").json()
        assert body == {"url": "http://testserver/note.ics", "token": False}

    def test_the_token_travels_in_the_url(self, authenticated_client, monkeypatch):
        monkeypatch.setenv("ALLOT_FEED_TOKEN", "a-long-random-token")
        body = authenticated_client.get("/note/feed-url").json()
        assert body["url"].endswith("/note.ics?feed=a-long-random-token")
        assert body["token"] is True

    def test_it_is_itself_behind_the_session(self, guarded_client):
        # The token opens the feed, so the URL carrying it is a credential
        assert guarded_client.get("/note/feed-url").status_code == 401
