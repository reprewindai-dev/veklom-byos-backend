import pytest
from backend.core.utils.email import sanitize_sender, html_to_text

def test_html_to_text():
    html_content = """
    <html>
      <head><style>body { color: #fff; }</style></head>
      <body>
        <h1>Verify Email</h1>
        <p>Hi Anthony,</p>
        <p>Please click the link below to verify:</p>
        <div><a href="https://example.com">Verify Link</a></div>
      </body>
    </html>
    """
    text = html_to_text(html_content)
    
    assert "body {" not in text
    assert "Verify Email" in text
    assert "Hi Anthony," in text
    assert "Please click the link below to verify:" in text
    assert "Verify Link" in text

def test_sanitize_sender_none():
    assert sanitize_sender(None) == "Veklom <hello@mail.veklom.com>"
    assert sanitize_sender("") == "Veklom <hello@mail.veklom.com>"

def test_sanitize_sender_noreply():
    assert sanitize_sender("noreply@veklom.com") == "hello@mail.veklom.com"
    assert sanitize_sender("no-reply@veklom.com") == "hello@mail.veklom.com"
    assert sanitize_sender("Veklom <noreply@veklom.com>") == "Veklom <hello@mail.veklom.com>"
    assert sanitize_sender("Veklom <no-reply@mail.veklom.com>") == "Veklom <hello@mail.veklom.com>"

def test_sanitize_sender_veklom_domain():
    assert sanitize_sender("sales@veklom.com") == "sales@mail.veklom.com"
    assert sanitize_sender("Veklom Sales <sales@veklom.com>") == "Veklom Sales <sales@mail.veklom.com>"
    assert sanitize_sender("hello@mail.veklom.com") == "hello@mail.veklom.com"

def test_sanitize_sender_other_domain():
    # If someone sends with an external domain, rewrite it to mail.veklom.com to prevent Resend delivery failure
    assert sanitize_sender("test@gmail.com") == "test@mail.veklom.com"
    assert sanitize_sender("random@arbitrary.org") == "random@mail.veklom.com"
