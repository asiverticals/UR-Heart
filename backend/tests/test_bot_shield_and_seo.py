"""
Automated Test Suite for Bot Shield, SEO Endpoints & Uvicorn Access Log Noise Filter
Validates:
- GET /robots.txt (200 OK, text/plain)
- GET /sitemap.xml (200 OK, application/xml)
- GET /favicon.ico (204 No Content, Cache-Control)
- GET /?rest_route=/ (404 Not Found - WordPress REST API probe neutralization)
- GET / and HEAD / (200 OK keep-alive)
- Scanner probe paths (/.env, /wp-login.php, /xmlrpc.php, /blog/wp-json/) -> 404 with X-Sanctuary-Shield header
- UvicornAccessNoiseFilter suppresses noisy probe records
"""

import logging
import httpx
from httpx import ASGITransport
import pytest
from backend.app.main import app, UvicornAccessNoiseFilter


@pytest.mark.asyncio
async def test_robots_txt_endpoint():
    """Verifies /robots.txt returns 200 OK with proper text/plain content."""
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/robots.txt")
        assert res.status_code == 200
        assert "text/plain" in res.headers.get("content-type", "")
        assert "User-agent: *" in res.text
        assert "Disallow: /admin/" in res.text
        assert "Disallow: /api/" in res.text
        assert "Sitemap: https://urheart.app/sitemap.xml" in res.text


@pytest.mark.asyncio
async def test_sitemap_xml_endpoint():
    """Verifies /sitemap.xml returns 200 OK with valid XML structure."""
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/sitemap.xml")
        assert res.status_code == 200
        assert "application/xml" in res.headers.get("content-type", "")
        assert "<urlset" in res.text
        assert "https://urheart.app/store" in res.text
        assert "https://urheart.app/emergency-takedown" in res.text


@pytest.mark.asyncio
async def test_favicon_ico_endpoint():
    """Verifies /favicon.ico returns 204 No Content with long-lived Cache-Control."""
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/favicon.ico")
        assert res.status_code == 204
        assert "max-age" in res.headers.get("cache-control", "")


@pytest.mark.asyncio
async def test_rest_route_wordpress_probe_rejected():
    """Verifies /?rest_route=/ returns 404 so WordPress scanners do not mistake app for WP."""
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/?rest_route=/")
        assert res.status_code == 404
        assert res.text == "Not Found"


@pytest.mark.asyncio
async def test_clean_root_sentinel():
    """Verifies normal GET / and HEAD / return 200 keep-alive."""
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        head_res = await client.head("/")
        assert head_res.status_code == 200
        assert head_res.headers.get("X-Sanctuary-Alive") == "true"

        get_res = await client.get("/")
        assert get_res.status_code == 200
        assert get_res.json()["sanctuary"] == "active"


@pytest.mark.asyncio
async def test_scanner_probe_shield_blocks_malicious_paths():
    """Verifies scanner probe shield intercepts .env, wp-login, and xmlrpc probes."""
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        for probe_path in ["/.env", "/wp-login.php", "/xmlrpc.php", "/blog/wp-json/", "/.git/config", "/site/wp-json/"]:
            res = await client.get(probe_path)
            assert res.status_code == 404
            assert res.headers.get("X-Sanctuary-Shield") == "blocked"


def test_uvicorn_access_noise_filter():
    """Verifies log noise filter suppresses repetitive probe records and keep-alive pings."""
    noise_filter = UvicornAccessNoiseFilter()

    # Should filter repetitive HEAD 200 ping
    head_record = logging.LogRecord(
        name="uvicorn.access",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg='10.24.124.2:0 - "HEAD / HTTP/1.1" 200 OK',
        args=(),
        exc_info=None,
    )
    assert noise_filter.filter(head_record) is False

    # Should filter scanner 404 probe noise
    wp_record = logging.LogRecord(
        name="uvicorn.access",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg='10.24.6.28:0 - "GET /blog/ HTTP/1.1" 404 Not Found',
        args=(),
        exc_info=None,
    )
    assert noise_filter.filter(wp_record) is False

    env_record = logging.LogRecord(
        name="uvicorn.access",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg='10.24.124.2:0 - "GET /.env HTTP/1.1" 404 Not Found',
        args=(),
        exc_info=None,
    )
    assert noise_filter.filter(env_record) is False

    # Should ALLOW genuine API requests
    api_record = logging.LogRecord(
        name="uvicorn.access",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg='10.24.124.2:0 - "POST /api/v1/auth/login HTTP/1.1" 200 OK',
        args=(),
        exc_info=None,
    )
    assert noise_filter.filter(api_record) is True
