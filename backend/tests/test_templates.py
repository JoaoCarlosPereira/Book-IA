"""Smoke tests for HTML template rendering."""

from starlette.testclient import TestClient

from app.main import app


def test_login_page_renders():
  client = TestClient(app)
  response = client.get("/api/v1/auth/login")
  assert response.status_code == 200
  assert "Book-IA" in response.text
  assert "pacman-tech-theme" in response.text


def test_dashboard_redirects_unauthenticated():
  client = TestClient(app)
  response = client.get("/dashboard", follow_redirects=False)
  assert response.status_code == 302
  assert response.headers["location"] == "/login"
