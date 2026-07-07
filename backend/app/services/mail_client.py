import dataclasses
import datetime
import email
import email.message
import email.utils
import imaplib

_IMAP_HOST = "imap.gmail.com"


@dataclasses.dataclass(frozen=True)
class FetchedMail:
    message: email.message.Message
    from_address: str
    message_id: str


def _extract_from_address(message: email.message.Message) -> str:
    _, address = email.utils.parseaddr(message.get("From", ""))
    return address.strip().lower()


def fetch_recent_messages(
    address: str, app_password: str, since: datetime.date, mailbox: str = "INBOX"
) -> list[FetchedMail]:
    """Gmail IMAPへ接続し、指定日付以降に受信したメールを取得する(既読フラグは変更しない)。

    重複防止はIMAPの既読フラグではなくt_transactions.source_hash(Message-ID込み)に委ねるため、
    同じ期間を再取得しても安全(ADR 0010)。
    """
    mails: list[FetchedMail] = []

    with imaplib.IMAP4_SSL(_IMAP_HOST) as client:
        client.login(address, app_password)
        client.select(mailbox, readonly=True)

        status, data = client.search(None, f'(SINCE "{since.strftime("%d-%b-%Y")}")')
        if status != "OK" or not data or not data[0]:
            return mails

        for message_number in data[0].split():
            fetch_status, msg_data = client.fetch(message_number, "(BODY.PEEK[])")
            if fetch_status != "OK" or not msg_data or msg_data[0] is None:
                continue

            raw_bytes = msg_data[0][1]
            message = email.message_from_bytes(raw_bytes)
            mails.append(
                FetchedMail(
                    message=message,
                    from_address=_extract_from_address(message),
                    message_id=message.get("Message-ID", "").strip(),
                )
            )

    return mails
