"""The password, the signed cookie, and what the guard lets through."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from src.services import auth


class TestPasswordHash:
    def test_a_password_verifies_against_its_own_hash(self):
        # Given a hashed password
        encoded = auth.hash_password("hunter2")
        # When the same password is checked
        # Then it passes
        assert auth.verify_password("hunter2", encoded)

    def test_another_password_does_not(self):
        # Given a hashed password
        encoded = auth.hash_password("hunter2")
        # When a different one is checked
        # Then it fails
        assert not auth.verify_password("hunter3", encoded)

    def test_two_hashes_of_one_password_differ(self):
        # Given the same password hashed twice
        first = auth.hash_password("hunter2")
        second = auth.hash_password("hunter2")
        # Then the salt made them different, and both still verify
        assert first != second
        assert auth.verify_password("hunter2", first)
        assert auth.verify_password("hunter2", second)

    @pytest.mark.parametrize(
        "encoded",
        ["", "not-a-hash", "bcrypt$1$2$3$4$5", "scrypt$notanumber$8$1$c2FsdA$a2V5"],
        ids=["empty", "shapeless", "wrong-scheme", "unparseable"],
    )
    def test_a_hash_it_cannot_read_is_a_refusal_not_a_crash(self, encoded):
        # Given a hash that is malformed or from another scheme
        # When a password is checked against it
        # Then it is refused, quietly
        assert not auth.verify_password("hunter2", encoded)


class TestToken:
    def test_a_freshly_issued_token_verifies(self, password):
        # Given a token issued now
        # When it is checked
        # Then it passes
        assert auth.verify(auth.issue())

    def test_a_tampered_token_does_not(self, password):
        # Given a token whose expiry was pushed out by hand
        payload, _, signature = auth.issue().rpartition(".")
        forged = payload.replace("20", "29", 1) + "." + signature
        # When it is checked
        # Then the signature no longer matches
        assert not auth.verify(forged)

    def test_a_token_signed_with_another_key_does_not(
        self, password, monkeypatch: pytest.MonkeyPatch
    ):
        # Given a token issued under one key
        token = auth.issue()
        # When the key changes underneath it
        monkeypatch.setenv("ALLOT_SECRET_KEY", "a different key entirely")
        # Then it is worthless
        assert not auth.verify(token)

    def test_an_expired_token_does_not(self, password):
        # Given a token issued a session ago
        long_ago = datetime.now(timezone.utc) - timedelta(days=auth.session_days() + 1)
        token = auth.issue(now=long_ago)
        # When it is checked
        # Then it is out of date
        assert not auth.verify(token)

    @pytest.mark.parametrize(
        "token", ["", "nosignature", "not-a-date.abc"], ids=["empty", "bare", "garbage"]
    )
    def test_a_shapeless_token_does_not(self, password, token):
        # Given something that is not a token
        # When it is checked
        # Then it is refused without raising
        assert not auth.verify(token)

    def test_the_window_slides_with_the_configured_length(
        self, password, monkeypatch: pytest.MonkeyPatch
    ):
        # Given a session length of one day
        monkeypatch.setenv("ALLOT_SESSION_DAYS", "1")
        token = auth.issue()
        # When two days pass
        later = datetime.now(timezone.utc) + timedelta(days=2)
        # Then the token has expired
        assert auth.verify(token)
        assert not auth.verify(token, now=later)


class TestConfiguration:
    def test_authentication_is_off_without_a_password_hash(self, monkeypatch):
        # Given no password configured
        monkeypatch.delenv("ALLOT_PASSWORD_HASH", raising=False)
        # Then the app does not ask for one
        assert not auth.enabled()

    def test_a_password_without_a_key_is_a_loud_error(
        self, password, monkeypatch: pytest.MonkeyPatch
    ):
        # Given a password but no signing key
        monkeypatch.delenv("ALLOT_SECRET_KEY")
        # When a token is issued
        # Then it says what is missing rather than inventing a key
        with pytest.raises(RuntimeError, match="ALLOT_SECRET_KEY"):
            auth.issue()

    def test_the_cookie_is_secure_unless_told_otherwise(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        # Given nothing configured
        monkeypatch.delenv("ALLOT_COOKIE_SECURE", raising=False)
        # Then the cookie is HTTPS-only by default
        assert auth.cookie_secure()
        # And it takes an explicit opt-out to serve it over plain HTTP
        monkeypatch.setenv("ALLOT_COOKIE_SECURE", "0")
        assert not auth.cookie_secure()


class TestLogin:
    def test_the_right_password_hands_back_a_cookie(self, guarded_client, password):
        # Given an instance with a password
        # When it is given the right one
        response = guarded_client.post("/login", json={"password": password})
        # Then the session cookie is set
        assert response.status_code == 204
        assert auth.COOKIE_NAME in guarded_client.cookies

    def test_the_wrong_password_does_not(self, guarded_client):
        # Given an instance with a password
        # When it is given the wrong one
        response = guarded_client.post("/login", json={"password": "sesame"})
        # Then nothing is handed out
        assert response.status_code == 401
        assert auth.COOKIE_NAME not in guarded_client.cookies

    def test_there_is_nothing_to_log_into_without_a_password(self, client):
        # Given an instance with no password configured
        # When someone tries to log in anyway
        response = client.post("/login", json={"password": "sesame"})
        # Then the route says there is nothing here
        assert response.status_code == 404


class TestSessionEndpoint:
    def test_it_reports_an_open_instance(self, client):
        # Given no password configured
        # When the front asks
        response = client.get("/session")
        # Then it is told not to show a login screen
        assert response.json() == {"required": False, "authenticated": True}

    def test_it_reports_a_guarded_one(self, guarded_client):
        # Given a password, and nobody logged in
        # When the front asks
        response = guarded_client.get("/session")
        # Then it is told to show the login screen
        assert response.json() == {"required": True, "authenticated": False}

    def test_it_reports_a_logged_in_browser(self, authenticated_client):
        # Given a browser holding a valid cookie
        # When the front asks
        response = authenticated_client.get("/session")
        # Then it goes straight to the portfolio
        assert response.json() == {"required": True, "authenticated": True}


class TestGuard:
    @pytest.mark.parametrize(
        "path",
        ["/assets", "/assets/summary", "/envelopes", "/transactions?symbol=X", "/note"],
    )
    def test_the_api_is_closed_without_a_session(self, guarded_client, path):
        # Given a guarded instance
        # When the API is called with no cookie
        response = guarded_client.get(path)
        # Then it refuses
        assert response.status_code == 401
        assert response.json() == {"detail": "Not authenticated."}

    def test_writes_are_closed_too(self, guarded_client):
        # Given a guarded instance
        # When a deletion is attempted without a cookie
        response = guarded_client.delete("/assets/WPEA.PA")
        # Then it never reaches the database
        assert response.status_code == 401

    def test_a_forged_cookie_is_refused(self, guarded_client):
        # Given a cookie that was not issued here
        guarded_client.cookies.set(auth.COOKIE_NAME, "2999-01-01T00:00:00+00:00.forged")
        # When the API is called
        response = guarded_client.get("/assets")
        # Then it is refused like any other stranger
        assert response.status_code == 401

    def test_the_api_opens_with_a_session(self, authenticated_client):
        # Given a logged-in browser
        # When the API is called
        response = authenticated_client.get("/assets")
        # Then it answers
        assert response.status_code == 200

    def test_health_stays_open(self, guarded_client):
        # Given a guarded instance
        # When the health endpoint is called, as the container does
        response = guarded_client.get("/health")
        # Then it answers without a cookie, because the deployment waits on it
        assert response.status_code == 200

    def test_every_call_pushes_the_expiry_out(self, authenticated_client, password):
        # Given a session about to be used
        before = authenticated_client.cookies[auth.COOKIE_NAME]
        # When a later request goes through
        later = datetime.now(timezone.utc) + timedelta(seconds=1)
        response = authenticated_client.get("/assets", headers={"X-Test": "1"})
        # Then a fresh cookie came back, so the window slid
        assert response.status_code == 200
        assert auth.COOKIE_NAME in response.cookies
        assert auth.verify(before, now=later)

    def test_nothing_is_guarded_when_no_password_is_configured(self, client):
        # Given the LAN arrangement the README describes
        # When the API is called with no cookie at all
        response = client.get("/assets")
        # Then it behaves exactly as it did before authentication existed
        assert response.status_code == 200
