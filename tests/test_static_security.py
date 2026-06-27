from pathlib import Path


def test_static_html_uses_external_assets() -> None:
    html = Path("static/index.html").read_text()

    assert "<script>" not in html
    assert "<style>" not in html
    assert 'src="/static/app.js"' in html
    assert 'href="/static/styles.css"' in html


def test_netlify_csp_blocks_inline_assets() -> None:
    netlify_config = Path("netlify.toml").read_text()

    assert "Content-Security-Policy" in netlify_config
    assert "script-src 'self'" in netlify_config
    assert "style-src 'self'" in netlify_config
    assert "unsafe-inline" not in netlify_config
