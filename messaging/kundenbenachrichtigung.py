from broker import Broker
from events import ReturnStatus, ReturnStatusChanged

MESSAGES = {
    ReturnStatus.NEW: "Ihre Retoure ist angemeldet, das Versandlabel ist unterwegs.",
    ReturnStatus.RECEIVED: "Ihre Rücksendung ist bei uns eingegangen.",
    ReturnStatus.APPROVED: "Ihre Retoure wurde angenommen, die Erstattung wird veranlasst.",
    ReturnStatus.REJECTED: "Ihre Retoure wurde abgelehnt. Die Begründung erhalten Sie separat.",
    ReturnStatus.REFUNDED: "Ihre Erstattung wurde ausgelöst.",
}


def send_status_mail(event: ReturnStatusChanged) -> None:
    print(f"E-Mail zu Retoure {event.return_id}: {MESSAGES[event.status]}")


if __name__ == "__main__":
    Broker().subscribe(
        "kundenbenachrichtigung", [status.routing_key for status in MESSAGES], send_status_mail
    )
