import datetime

from app.services.mail_client import fetch_recent_messages


class _FakeIMAP:
    instances: list["_FakeIMAP"] = []

    def __init__(self, host):
        self.host = host
        self.search_criteria = None
        self.selected_mailbox = None
        self.selected_readonly = None
        _FakeIMAP.instances.append(self)

    def login(self, address, app_password):
        self.login_args = (address, app_password)

    def select(self, mailbox, readonly=False):
        self.selected_mailbox = mailbox
        self.selected_readonly = readonly

    def search(self, charset, criteria):
        self.search_criteria = criteria
        return "OK", [b"1 2"]

    def fetch(self, message_number, parts):
        raw = (
            b"From: Card Co <alerts@example.com>\r\n"
            b"Message-ID: <msg-" + message_number + b">\r\n"
            b"Subject: test\r\n\r\nbody"
        )
        return "OK", [(b"1 (BODY[] {123}", raw)]

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False


def test_fetch_recent_messages_parses_from_and_message_id(monkeypatch):
    _FakeIMAP.instances.clear()
    monkeypatch.setattr("app.services.mail_client.imaplib.IMAP4_SSL", _FakeIMAP)

    mails = fetch_recent_messages("me@gmail.com", "app-pass", datetime.date(2026, 7, 1))

    assert len(mails) == 2
    assert mails[0].from_address == "alerts@example.com"
    assert mails[0].message_id == "<msg-1>"
    assert mails[1].message_id == "<msg-2>"

    fake = _FakeIMAP.instances[-1]
    assert fake.selected_readonly is True
    assert "SINCE" in fake.search_criteria
    assert "01-Jul-2026" in fake.search_criteria


def test_fetch_recent_messages_returns_empty_list_when_no_results(monkeypatch):
    class _EmptyFakeIMAP(_FakeIMAP):
        def search(self, charset, criteria):
            self.search_criteria = criteria
            return "OK", [b""]

    monkeypatch.setattr("app.services.mail_client.imaplib.IMAP4_SSL", _EmptyFakeIMAP)

    mails = fetch_recent_messages("me@gmail.com", "app-pass", datetime.date(2026, 7, 1))

    assert mails == []
