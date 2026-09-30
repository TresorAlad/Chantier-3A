
def test_google_oauth_callback_creates_user_and_session(client, monkeypatch):
    class FakeGoogle:
        async def authorize_access_token(self, request):
            return {
                "userinfo": {
                    "sub": "google-123",
                    "email": "alice@example.com",
                    "email_verified": True,
                    "given_name": "Alice",
                    "family_name": "Dupont",
                    "name": "Alice Dupont",
                    "picture": "https://example.com/avatar.png",
                }
            }

    from http_layer.routes import oauth as oauth_route

    monkeypatch.setattr(oauth_route, "oauth_gle", type("X", (), {"google": FakeGoogle()})())
    r = client.get("/api/auth/google/callback")
    assert r.status_code == 200
    assert "token" in r.json()
    assert "user" in r.json()