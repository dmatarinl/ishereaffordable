from pathlib import Path


def test_static_html_uses_external_assets() -> None:
    html = Path("static/index.html").read_text()

    assert "<script>" not in html
    assert "<style>" not in html
    assert 'src="/static/app.js' in html
    assert 'href="/static/styles.css' in html


def test_admin_html_uses_external_assets() -> None:
    html = Path("static/admin.html").read_text()

    assert "<script>" not in html
    assert "<style>" not in html
    assert '<meta name="robots" content="noindex,nofollow">' in html
    assert 'src="/static/admin.js"' in html
    assert 'href="/static/admin.css"' in html


def test_netlify_csp_blocks_inline_assets() -> None:
    netlify_config = Path("netlify.toml").read_text()

    assert "Content-Security-Policy" in netlify_config
    assert "script-src 'self'" in netlify_config
    assert "style-src 'self'" in netlify_config
    assert "unsafe-inline" not in netlify_config
    assert 'X-Robots-Tag = "noindex, nofollow"' in netlify_config


def test_admin_key_is_not_persisted_in_browser_storage() -> None:
    admin_script = Path("static/admin.js").read_text()

    assert "sessionStorage" not in admin_script
    assert "localStorage" not in admin_script


def test_netlify_public_api_adds_cdn_cache_for_public_read_endpoints() -> None:
    public_api = Path("netlify/functions/public-api.mts").read_text()

    assert '"/api/cities"' in public_api
    assert '"/api/affordability"' in public_api
    assert '"Netlify-CDN-Cache-Control"' in public_api
    assert "public, durable, max-age=3600, stale-while-revalidate=86400" in public_api
    assert "public, durable, max-age=300, stale-while-revalidate=900" in public_api
    assert "public, max-age=0, must-revalidate" in public_api
    assert "DATABASE_URL" in public_api


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
