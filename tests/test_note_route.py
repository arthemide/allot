"""The /note endpoint: the monthly note, as plain text."""

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
        assert "rien" in text
