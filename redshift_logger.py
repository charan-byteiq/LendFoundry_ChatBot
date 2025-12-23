# redshift_logger.py
import os
import json
from uuid import uuid4
from datetime import datetime, timezone
import redshift_connector
from logger import logger

MAX_VARCHAR_BYTES = 65000

def truncate_utf8_bytes(s: str | None, max_bytes: int = MAX_VARCHAR_BYTES) -> str | None:
    if s is None:
        return None
    b = s.encode("utf-8")
    if len(b) <= max_bytes:
        return s
    suffix = "...[TRUNCATED]"
    cut = max_bytes - len(suffix.encode("utf-8"))
    return b[:cut].decode("utf-8", errors="ignore") + suffix

def get_conn():
    return redshift_connector.connect(
        host=os.getenv("REDSHIFT_HOST"),
        database=os.getenv("REDSHIFT_DB"),
        port=int(os.getenv("REDSHIFT_PORT", "5439")),
        user=os.getenv("REDSHIFT_USER"),
        password=os.getenv("REDSHIFT_PASSWORD"),
    )

def safe_log_to_redshift(*, session_id: str | None, chatbot: str, user_message: str | None,
                         answer: str | None, response_payload: dict | None,
                         is_error: bool, error_message: str | None):
    try:
        event_id = str(uuid4())
        created_at = datetime.now(timezone.utc)

        response_json = json.dumps(response_payload, ensure_ascii=False, default=str) if response_payload else None

        session_id = truncate_utf8_bytes(session_id)
        chatbot = truncate_utf8_bytes(chatbot)
        user_message = truncate_utf8_bytes(user_message)
        answer = truncate_utf8_bytes(answer)
        response_json = truncate_utf8_bytes(response_json)
        error_message = truncate_utf8_bytes(error_message)

        sql = """
          INSERT INTO analytics.chat_logs
          (event_id, created_at, session_id, chatbot, user_message, answer, response_json, is_error, error_message)
          VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """

        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (event_id, created_at, session_id, chatbot, user_message,
                                  answer, response_json, is_error, error_message))
            conn.commit()

        logger.info(f"Logged to Redshift: chatbot={chatbot}, is_error={is_error}")

    except Exception as e:
        logger.error(f"Redshift logging failed (non-fatal): {e}")
