import base64
import hashlib
from pathlib import Path

from liquent_platform.transport.http.ui_brand import (
    STYLE, STYLE_DIGEST, CONTENT_SECURITY_POLICY, brand_document,
)
from liquent_platform.transport.http.research_results import result_document


def test_shared_brand_is_script_free_and_idempotent() -> None:
    document = '<html><head></head><body><main><h1>Research</h1></main></body></html>'
    branded = brand_document(document)
    assert branded.count('<style>') == 1
    assert branded.count('class="brand-header"') == 1
    assert brand_document(branded) == branded
    assert '<h1>Research</h1>' in branded
    assert '<script' not in branded
    assert 'https://' not in branded
    assert '#002b58' in STYLE
    assert '@media(max-width:600px)' in STYLE


def test_stylesheet_digest_matches_every_edge_policy() -> None:
    assert STYLE_DIGEST == base64.b64encode(hashlib.sha256(STYLE.encode()).digest()).decode()
    edge = (Path(__file__).resolve().parents[1] / 'operations/edge/staging.conf').read_text()
    policies = [line for line in edge.splitlines() if 'add_header Content-Security-Policy' in line]
    assert len(policies) == 4
    assert all(f"style-src 'sha256-{STYLE_DIGEST}'" in line for line in policies)
    assert 'unsafe-inline' not in CONTENT_SECURITY_POLICY
    from liquent_platform.transport.http.research_customer_ui import CUSTOMER_CSP, CUSTOMER_CONTROLS, CUSTOMER_SCRIPT, CUSTOMER_STYLE
    script_hash = base64.b64encode(hashlib.sha256(CUSTOMER_SCRIPT.encode()).digest()).decode()
    customer_style_hash = base64.b64encode(hashlib.sha256(CUSTOMER_STYLE.encode()).digest()).decode()
    assert "script-src 'sha256-" + script_hash + "'" in edge
    assert "'sha256-" + customer_style_hash + "'" in edge
    assert "'sha256-" + customer_style_hash + "'" in CUSTOMER_CSP
    assert "script-src 'sha256-" + script_hash + "'" in CUSTOMER_CSP
    assert 'integrity="sha256-' + script_hash + '"' in CUSTOMER_CONTROLS
    assert 'unsafe-inline' not in CUSTOMER_CSP
    assert 'unsafe-eval' not in CUSTOMER_CSP
    assert "default-src 'none'" in CONTENT_SECURITY_POLICY


def test_result_keeps_escaped_content_and_one_shared_stylesheet() -> None:
    document = result_document('example', 'succeeded', {'title': '<script>bad</script>'})
    assert document.count('<style>') == 1
    assert 'class="wordmark"' in document
    assert '&lt;script&gt;bad&lt;/script&gt;' in document
    assert '<script>' not in document
