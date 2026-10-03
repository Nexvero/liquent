"""Shared, script-free Liquent presentation with a digest-bound stylesheet."""

import base64
import hashlib


STYLE = """:root{font-family:ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color:#082d56;background:#fff;font-synthesis:none;line-height:1.6}
*{box-sizing:border-box}body{margin:0}main{max-width:1120px;margin:auto;padding:0 48px 64px}
.brand-header{display:flex;align-items:center;justify-content:space-between;gap:24px;padding:38px 0 32px;border-bottom:1px solid #e6edf4;margin-bottom:48px}
.wordmark{font-size:48px;font-weight:600;letter-spacing:-2.8px;line-height:1;color:#002b58}.brand-caption{font-size:11px;letter-spacing:2px;text-transform:uppercase;color:#667b91}
h1,h2{letter-spacing:-.035em;line-height:1.2}h1{font-size:clamp(30px,4vw,46px);font-weight:600;margin:28px 0 20px}h2{font-size:22px;font-weight:600;margin:0 0 22px}
p{max-width:76ch;color:#435b73}a{color:#003e73;text-decoration-color:#a4b7ca;text-underline-offset:5px}a:hover{color:#001f41;text-decoration-color:currentColor}a:focus-visible,button:focus-visible{outline:3px solid #608fb8;outline-offset:5px}
nav{font-size:14px;margin-bottom:28px}.notice{border-left:3px solid #073463;background:#f5f8fc;padding:20px 24px;margin:32px 0}
section{background:#fff;border:1px solid #e3eaf1;border-radius:16px;padding:32px;margin:32px 0}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:16px;margin:24px 0 36px}.cards div{border:1px solid #e3eaf1;border-radius:14px;padding:24px 20px;background:#fbfcfe}
dt{font-size:13px;font-weight:500;color:#506980}dd{margin:12px 0 0;font-size:26px;font-weight:600;letter-spacing:-.03em;font-variant-numeric:tabular-nums}
table{width:100%;border-collapse:collapse}th,td{text-align:left;padding:18px 12px;border-bottom:1px solid #e7edf3;overflow-wrap:anywhere}thead th{font-size:12px;text-transform:uppercase;letter-spacing:.08em;color:#667b91}tbody th{font-weight:500}td{font-variant-numeric:tabular-nums}
code{font-size:12px;overflow-wrap:anywhere}small,time{color:#657b91;font-size:13px}ul{padding-left:20px}ul li{padding:7px 0;color:#435b73}
ol{list-style:none;padding:0;margin:28px 0}ol li{border:1px solid #e3eaf1;border-radius:12px;padding:22px;margin-bottom:12px;display:flex;align-items:center;flex-wrap:wrap;gap:12px;font-size:13px}ol li span:first-child{flex:1 1 300px;overflow-wrap:anywhere;font-family:ui-monospace,monospace}ol li a{font-weight:600;white-space:nowrap}
form{margin:32px 0}button{font:inherit;font-size:15px;font-weight:600;background:#002b58;color:#fff;border:1px solid #002b58;border-radius:8px;padding:14px 26px;cursor:pointer}button:hover{background:#001f41}
.brand-footer{margin-top:64px;padding-top:24px;border-top:1px solid #e6edf4;font-size:12px;letter-spacing:.03em;color:#6d8195}
@media(max-width:600px){main{padding:0 20px 36px}.brand-header{padding:28px 0;margin-bottom:32px}.wordmark{font-size:38px}.brand-caption{font-size:9px;letter-spacing:1px}section{padding:22px 18px;border-radius:12px}.cards{grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}.cards div{padding:18px 14px}dd{font-size:23px}th,td{padding:14px 6px;font-size:14px}.notice{padding:16px 18px}ol li{padding:18px}.brand-footer{margin-top:40px}}
"""

STYLE_DIGEST = base64.b64encode(hashlib.sha256(STYLE.encode()).digest()).decode()
CONTENT_SECURITY_POLICY = (
    "default-src 'none'; style-src 'sha256-" + STYLE_DIGEST
    + "'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"
)


def brand_document(document: str) -> str:
    """Decorate trusted server HTML; no user input or permission changes."""
    if 'class="brand-header"' in document:
        return document
    if "<style>" not in document:
        document = document.replace("</head>", f"<style>{STYLE}</style></head>", 1)
    document = document.replace(
        "<main>",
        '<main><header class="brand-header"><span class="wordmark" aria-label="Liquent">'
        'liquent</span><span class="brand-caption">Research workspace</span></header>',
        1,
    )
    return document.replace(
        "</main>", '<footer class="brand-footer">liquent · Klarheit durch Research</footer></main>', 1
    )
