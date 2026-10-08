import json
from pathlib import Path
from typing import Any
from app.config import BASE_DIR, load_profile
from app.sessions import get_session


def get_tool_definitions(profile_id: str) -> list[dict[str, Any]]:
    profile = load_profile(profile_id)
    profile_tools = profile.get("tools", {})

    definitions = []

    if "lookup_record" in profile_tools:
        definitions.append(
            {
                "name": "lookup_record",
                "description": "Look up a customer or employee record by ID.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "record_id": {
                            "type": "STRING",
                            "description": "The record ID to look up (e.g. ORD-1001 or EMP-2001)",
                        }
                    },
                    "required": ["record_id"],
                },
            }
        )

    if "read_document" in profile_tools:
        definitions.append(
            {
                "name": "read_document",
                "description": "Read the text contents of a document file.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "name": {
                            "type": "STRING",
                            "description": "The name of the document file to read",
                        }
                    },
                    "required": ["name"],
                },
            }
        )

    if "send_email" in profile_tools:
        definitions.append(
            {
                "name": "send_email",
                "description": "Send an email message to a recipient.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "to": {
                            "type": "STRING",
                            "description": "Recipient email address",
                        },
                        "subject": {
                            "type": "STRING",
                            "description": "Subject of the email",
                        },
                        "body": {
                            "type": "STRING",
                            "description": "Body text of the email",
                        },
                    },
                    "required": ["to", "subject", "body"],
                },
            }
        )

    return definitions


def execute_lookup_record(profile_id: str, record_id: str) -> str:
    path = BASE_DIR / "data" / profile_id / "records.json"
    if not path.exists():
        return f"Error: records file for profile '{profile_id}' not found."

    try:
        with open(path, "r", encoding="utf-8") as f:
            records = json.load(f)

        if record_id in records:
            return json.dumps(records[record_id], indent=2)
        else:
            return f"Record '{record_id}' not found."
    except Exception as e:
        return f"Error loading records: {e}"


def execute_read_document(profile_id: str, name: str) -> str:
    docs_dir = (BASE_DIR / "data" / profile_id / "documents").resolve()
    doc_path = (docs_dir / name).resolve()

    # Path traversal check
    if not str(doc_path).startswith(str(docs_dir)):
        return "Error: Access denied (path traversal blocked)."

    if not doc_path.exists() or not doc_path.is_file():
        return f"Document '{name}' not found."

    try:
        with open(doc_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except Exception as e:
        return f"Error reading document: {e}"


def execute_send_email(
    session_id: str, to: str, subject: str, body: str
) -> str:
    session = get_session(session_id)
    email_entry = {
        "to": to,
        "subject": subject,
        "body": body,
        "timestamp": json.dumps(
            json.dumps({"to": to, "subject": subject, "body": body})
        ),
    }
    session.outbox.append(email_entry)
    return f"Email queued to Outbox for {to} (Subject: {subject})."
