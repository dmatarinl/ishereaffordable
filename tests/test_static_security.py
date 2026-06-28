from pathlib import Path


def test_static_html_uses_external_assets() -> None:
    html = Path("static/index.html").read_text()

    assert "<script>" not in html
    assert "<style>" not in html
    assert 'src="/static/app.js"' in html
    assert 'href="/static/styles.css"' in html


def test_admin_html_uses_external_assets() -> None:
    html = Path("static/admin.html").read_text()

    assert "<script>" not in html
    assert "<style>" not in html
    assert 'src="/static/admin.js"' in html
    assert 'href="/static/admin.css"' in html


def test_netlify_csp_blocks_inline_assets() -> None:
    netlify_config = Path("netlify.toml").read_text()

    assert "Content-Security-Policy" in netlify_config
    assert "script-src 'self'" in netlify_config
    assert "style-src 'self'" in netlify_config
    assert "unsafe-inline" not in netlify_config


def test_netlify_proxy_adds_cdn_cache_for_public_read_endpoints() -> None:
    proxy = Path("netlify/functions/api-proxy.mts").read_text()

    assert '"/api/cities"' in proxy
    assert '"/api/affordability"' in proxy
    assert '"Netlify-CDN-Cache-Control"' in proxy
    assert "public, durable, max-age=3600, stale-while-revalidate=86400" in proxy
    assert "public, durable, max-age=300, stale-while-revalidate=900" in proxy
    assert "public, max-age=0, must-revalidate" in proxy


def test_netlify_proxy_does_not_cache_errors() -> None:
    proxy = Path("netlify/functions/api-proxy.mts").read_text()

    assert "status < 200 || status >= 300" in proxy
    assert 'headers.set("Cache-Control", "no-store")' in proxy


def test_netlify_admin_proxy_requires_secret_and_never_caches() -> None:
    proxy = Path("netlify/functions/admin-proxy.mts").read_text()

    assert "ADMIN_API_SECRET" in proxy
    assert '"/admin-api/sources/status"' in proxy
    assert '"/admin-api/refresh"' in proxy
    assert '"cache-control": "no-store"' in proxy
    assert 'responseHeaders.set("cache-control", "no-store")' in proxy
