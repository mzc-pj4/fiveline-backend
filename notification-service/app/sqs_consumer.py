import json
import logging
import threading
import time

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.notification import Notification

logger = logging.getLogger(__name__)

TITLE_MAP = {
    "ORDER_PLACED": "주문이 완료되었습니다",
    "ORDER_SHIPPED": "주문이 배송 중입니다",
    "ORDER_DELIVERED": "주문이 배달되었습니다",
    "STOCK_ALERT": "재고 알림",
}


def _process_message(body: dict) -> None:
    user_id = body.get("user_id")
    if not user_id:
        return

    event_type = body.get("event_type", "SYSTEM")
    title = TITLE_MAP.get(event_type, "알림")
    message = body.get("message", title)

    with SessionLocal() as db:
        db.add(Notification(user_id=user_id, type=event_type, title=title, message=message))
        db.commit()


def _poll(sqs, queue_url: str) -> None:
    while True:
        try:
            response = sqs.receive_message(
                QueueUrl=queue_url,
                MaxNumberOfMessages=10,
                WaitTimeSeconds=20,
            )
            for msg in response.get("Messages", []):
                try:
                    _process_message(json.loads(msg["Body"]))
                    sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=msg["ReceiptHandle"])
                except Exception as e:
                    logger.error(f"message processing failed: {e}")
        except Exception as e:
            logger.error(f"SQS polling error: {e}")
            time.sleep(5)


def start_sqs_consumer() -> None:
    if not settings.sqs_queue_url:
        logger.info("SQS_QUEUE_URL not configured — SQS consumer disabled")
        return

    import boto3
    sqs = boto3.client("sqs", region_name=settings.aws_region)
    thread = threading.Thread(target=_poll, args=(sqs, settings.sqs_queue_url), daemon=True)
    thread.start()
    logger.info("SQS consumer started")
