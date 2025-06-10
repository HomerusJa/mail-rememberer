import os
from datetime import date
import textwrap
from typing import Literal
from dataclasses import dataclass
import sqlite3
import logging

from postmarker.core import PostmarkClient
from mistralai import Mistral

try:
    import dotenv
except ImportError:
    print(
        "The python-dotenv package is required to automatically load "
        "environment variables from a .env file."
    )
else:
    dotenv.load_dotenv()

IS_DEV: bool = os.getenv("ENV").lower() == "dev"

RECEIVER_MAIL: str = os.getenv("RECEIVER_MAIL")
POSTMARK_SERVER_API_TOKEN: str = os.getenv("POSTMARK_SERVER_API_TOKEN")

MISTRAL_API_KEY: str = os.getenv("MISTRAL_API_KEY")
MISTRAL_MODEL: str = os.getenv("MISTRAL_MODEL")

MESSAGE_DB_PATH: str = os.getenv("MESSAGE_DB_PATH")

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@dataclass
class Message:
    id: int | None
    added_at: date
    message: str

    @classmethod
    def from_message(cls, message: str):
        return cls(id=None, added_at=date.today(), message=message)

    @classmethod
    def from_db(cls, row: sqlite3.Row):
        return cls(id=row[0], added_at=date.fromisoformat(row[1]), message=row[2])

    def to_db(self) -> tuple[int | None, str, str]:
        return (self.id, self.added_at.isoformat(), self.message)

    def __str__(self):
        return f"Message {self.id} ({self.added_at}):\n{self.message}"


@dataclass
class Task:
    id: int | None
    added_at: date
    last_modified_at: date
    scheduled_for: date | None
    scheduled_for_comment: str | None
    description: str
    status: Literal["pending", "running", "completed", "failed"]
    comment: str
    from_message: int | None = None  # new field added

    @classmethod
    def from_description(cls, description: str, from_message: int | None = None):
        return cls(
            id=None,
            added_at=date.today(),
            last_modified_at=date.today(),
            scheduled_for=None,
            scheduled_for_comment=None,
            description=description,
            status="pending",
            comment="",
            from_message=from_message
        )

    @classmethod
    def from_db(cls, row: sqlite3.Row):
        return cls(
            id=row[0],
            added_at=date.fromisoformat(row[1]),
            last_modified_at=date.fromisoformat(row[2]),
            scheduled_for=date.fromisoformat(row[3]),
            scheduled_for_comment=row[4],
            description=row[5],
            status=row[6],
            comment=row[7],
            from_message=row[8]
        )

    def to_db(self) -> tuple[int | None, str, str, str, str, str, str, str, int | None]:
        return (
            self.id,
            self.added_at.isoformat(),
            self.last_modified_at.isoformat(),
            self.scheduled_for.isoformat() if self.scheduled_for else None,
            self.scheduled_for_comment,
            self.description,
            self.status,
            self.comment,
            self.from_message
        )

    def __str__(self):
        return textwrap.dedent(f"""
            Task {self.id} ({self.added_at.isoformat()}):
            {self.description}
            Status: {self.status}
            Comment: {self.comment}
            Last modified at: {self.last_modified_at.isoformat()}
            Schedule for: {self.scheduled_for.isoformat()}
            Schedule for comment: {self.scheduled_for_comment}
        """)


def create_tables(cur: sqlite3.Cursor):
    """
    Creates the required tables 'messages' and 'tasks' if they don't exist.

    Table: messages
    - id: integer primary key
    - added_at: text (ISO date)
    - message: text

    Table: tasks
    - id: integer primary key
    - added_at: text (ISO date)
    - last_modified_at: text (ISO date)
    - description: text
    - status: text ('pending', 'running', 'completed', 'failed')
    - comment: text
    - from_message: integer (foreign key to messages.id, optional)
    """
    logger.info("Creating tables if they don't exist")
    cur.execute("PRAGMA foreign_keys = ON;")  # Enable foreign keys

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            added_at    TEXT DEFAULT CURRENT_TIMESTAMP,
            message     TEXT
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS tasks
        (
            id                    INTEGER PRIMARY KEY AUTOINCREMENT,
            added_at              TEXT DEFAULT CURRENT_TIMESTAMP,
            last_modified_at      TEXT DEFAULT CURRENT_TIMESTAMP,
            scheduled_for         TEXT,
            scheduled_for_comment TEXT,
            description           TEXT,
            status                TEXT DEFAULT 'pending',
            comment               TEXT,
            from_message          INTEGER,
            FOREIGN KEY (from_message) REFERENCES messages (id)
        )
        """
    )


def insert_message(cur: sqlite3.Cursor, message: Message) -> None:
    """Inserts a Message instance into the messages table."""
    logger.debug(f"Inserting message {message!r}")
    cur.execute(
        "INSERT INTO messages (id, added_at, message) VALUES (?, ?, ?)",
        message.to_db()
    )


def insert_task(cur: sqlite3.Cursor, task: Task) -> None:
    """Inserts a Task instance into the tasks table."""
    logger.debug(f"Inserting task {task!r}")
    cur.execute(
        """
        INSERT INTO tasks (
            id, added_at, last_modified_at, scheduled_for, scheduled_for_comment, description, status, comment, from_message
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        task.to_db()
    )


def get_message_by_id(cur: sqlite3.Cursor, message_id: int) -> Message | None:
    """Retrieves a Message instance from the messages table by its ID."""
    cur.execute("SELECT * FROM messages WHERE id = ?", (message_id,))
    row = cur.fetchone()
    if row is None:
        return None
    return Message.from_db(row)


def get_task_by_id(cur: sqlite3.Cursor, task_id: int) -> Task | None:
    """Retrieves a Task instance from the tasks table by its ID."""
    cur.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    row = cur.fetchone()
    if row is None:
        return None
    return Task.from_db(row)


def generate_mail_body(messages: list[Message]) -> str:
    """Generates the body of the email by querying the model."""


def main():
    if IS_DEV:
        logger.info("Running in development mode")
    else:
        logger.info("Running in production mode")

    # Initialize API Clients locally
    postmark = PostmarkClient(server_token=POSTMARK_SERVER_API_TOKEN)
    mistral = Mistral(api_key=MISTRAL_API_KEY)

    # Connect to SQLite database
    logger.info(f"Connecting to SQLite database at {MESSAGE_DB_PATH}")
    with sqlite3.connect(MESSAGE_DB_PATH) as conn:
        cur = conn.cursor()

        if IS_DEV:
            # Drop all tables as SQLite never updates them if they were already created
            cur.execute("DROP TABLE IF EXISTS messages;")
            cur.execute("DROP TABLE IF EXISTS tasks;")
        create_tables(cur)

        # Example usage: inserting a fake message
        example_message = Message.from_message("Today I want to fix the car's brakes.")
        insert_message(cur, example_message)

        # Example usage: inserting a fake task based on the message
        example_task = Task.from_description(
            "Fix the car's brakes",
            from_message=1  # Normally you would retrieve this dynamically
        )
        insert_task(cur, example_task)

        conn.commit()  # Commit changes

if __name__ == "__main__":
    main()
