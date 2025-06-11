import json
import os
from datetime import date
import textwrap
from typing import Literal, Self
from dataclasses import dataclass
import sqlite3
import logging

from postmarker.core import PostmarkClient
from mistralai import Mistral

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("asyncio").setLevel(logging.WARNING)

def load_dotenv():
    try:
        import dotenv
    except ImportError:
        logger.info(
            "The python-dotenv package is required to automatically load "
            "environment variables from a .env file. Now, it's your "
            "responsibility to load the .env file manually."
        )
    else:
        logger.debug("Loading environment variables from .env file")
        dotenv.load_dotenv()

load_dotenv()

IS_DEV: bool = os.getenv("ENV", "").lower() == "dev"

RECEIVER_MAIL: str = os.getenv("RECEIVER_MAIL")
POSTMARK_SERVER_API_TOKEN: str = os.getenv("POSTMARK_SERVER_API_TOKEN")

MISTRAL_API_KEY: str = os.getenv("MISTRAL_API_KEY")
MISTRAL_MODEL: str = os.getenv("MISTRAL_MODEL")

MESSAGE_DB_PATH: str = os.getenv("MESSAGE_DB_PATH")

@dataclass
class Message:
    id: int | None
    added_at: date
    message: str

    @classmethod
    def from_db(cls, row: sqlite3.Row) -> Self:
        """Create Message instance from SQLite Row"""
        return cls(
            id=row["id"],
            added_at=date.fromisoformat(row["added_at"]),
            message=row["message"],
        )

    def to_db(self) -> tuple:
        """Convert Message instance to tuple for DB insertion (excluding id)"""
        return (self.added_at.isoformat(), self.message)

    @classmethod
    def from_message(cls, message: str) -> Self:
        return cls(
            id=None,
            added_at=date.today(),
            message=message,
        )

    def __str__(self):
        return f"Message {self.id} ({self.added_at}):\n{self.message}"


type TaskStatus = Literal["pending", "running", "completed", "failed"]


@dataclass
class Task:
    id: int | None
    added_at: date
    last_modified_at: date
    scheduled_for: date | None
    scheduled_for_comment: str | None
    description: str
    status: TaskStatus
    comment: str
    from_message: int | None = None

    @classmethod
    def from_description(cls, description: str, from_message: int | None = None) -> Self:
        return cls(
            id=None,
            added_at=date.today(),
            last_modified_at=date.today(),
            scheduled_for=None,
            scheduled_for_comment=None,
            description=description,
            status="pending",
            comment="",
            from_message=from_message,
        )

    @classmethod
    def from_llm_tool_call(cls, properties: dict[str, str]) -> Self:
        if not properties.get("description"):
            raise ValueError("description must be provided")
        if not properties.get("status"):
            raise ValueError("status must be provided")
        if properties["status"] not in ["pending", "running", "completed", "failed"]:
            raise ValueError("status must be one of pending, running, completed, failed")

        scheduled_for = date.fromisoformat(properties["scheduled_for"]) if properties.get("scheduled_for") else None
        scheduled_for_comment = properties["scheduled_for_comment"] if properties.get("scheduled_for_comment") else None
        return cls(
            id=None,
            added_at=date.today(),
            last_modified_at=date.today(),
            scheduled_for=scheduled_for,
            scheduled_for_comment=scheduled_for_comment,
            description=properties["description"],
            status=properties["status"],
            comment=properties.get("comment", ""),
            from_message=None,
        )

    @classmethod
    def from_db(cls, row: sqlite3.Row) -> Self:
        """Create Task instance from SQLite Row"""
        return cls(
            id=row["id"],
            added_at=date.fromisoformat(row["added_at"]),
            last_modified_at=date.fromisoformat(row["last_modified_at"]),
            scheduled_for=date.fromisoformat(row["scheduled_for"]) if row["scheduled_for"] else None,
            scheduled_for_comment=row["scheduled_for_comment"],
            description=row["description"],
            status=row["status"],
            comment=row["comment"],
            from_message=row["from_message"],
        )

    def to_db(self) -> tuple[str, str | None, str, str, str, str, str, int | None]:
        """Convert Task instance to tuple for DB insertion (excluding id)"""
        return (
            self.added_at.isoformat(),
            self.last_modified_at.isoformat(),
            self.scheduled_for.isoformat() if self.scheduled_for else None,
            self.scheduled_for_comment,
            self.description,
            self.status,
            self.comment,
            self.from_message,
        )

    def __str__(self):
        scheduled_for_str = self.scheduled_for.isoformat() if self.scheduled_for else "None"
        scheduled_for_comment_str = self.scheduled_for_comment or "None"
        return textwrap.dedent(f"""
            Task {self.id} ({self.added_at.isoformat()}):
            {self.description}
            Status: {self.status}
            Comment: {self.comment}
            Last modified at: {self.last_modified_at.isoformat()}
            Scheduled for: {scheduled_for_str}
            Scheduled for comment: {scheduled_for_comment_str}
        """)


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(MESSAGE_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def create_tables(cur: sqlite3.Cursor):
    logger.info("Creating tables if they don't exist")
    cur.execute("PRAGMA foreign_keys = ON;")  # Enable foreign keys

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS messages
        (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            added_at TEXT,
            message  TEXT
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS tasks
        (
            id                    INTEGER PRIMARY KEY AUTOINCREMENT,
            added_at              TEXT,
            last_modified_at      TEXT,
            scheduled_for         TEXT,
            scheduled_for_comment TEXT,
            description           TEXT,
            status                TEXT,
            comment               TEXT,
            from_message          INTEGER,
            FOREIGN KEY (from_message) REFERENCES messages (id)
        )
        """
    )


def insert_message(cur: sqlite3.Cursor, message: Message) -> int:
    if message.id is not None:
        raise ValueError("Message.id should be None when inserting a new message")

    logger.debug(f"Inserting message {message!r}")
    cur.execute(
        "INSERT INTO messages (added_at, message) VALUES (?, ?)",
        message.to_db(),
    )
    message_id = cur.lastrowid
    message.id = message_id  # also updates instance outside of this scope
    return message_id


def insert_task(cur: sqlite3.Cursor, task: Task) -> int:
    if task.id is not None:
        raise ValueError("Task.id should be None when inserting a new task")

    logger.debug(f"Inserting task {task!r}")
    cur.execute(
        """
        INSERT INTO tasks (
            added_at, last_modified_at, scheduled_for, scheduled_for_comment,
            description, status, comment, from_message
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        task.to_db(),
    )
    task_id = cur.lastrowid
    task.id = task_id  # also updates instance outside of this scope
    return task_id


def get_message_by_id(cur: sqlite3.Cursor, message_id: int) -> Message | None:
    cur.execute("SELECT * FROM messages WHERE id = ?", (message_id,))
    row = cur.fetchone()
    if row is None:
        return None
    return Message.from_db(row)


def get_task_by_id(cur: sqlite3.Cursor, task_id: int) -> Task | None:
    cur.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    row = cur.fetchone()
    if row is None:
        return None
    return Task.from_db(row)

tools = [
    {
        "type": "function",
        "function": {
            "name": "insert_task",
            "description": "Insert a new task into the database",
            "parameters": {
                "type": "object",
                "properties": {
                    "description": {
                        "type": "string",
                        "description": "A concise description of the task."
                    },
                    "comment": {
                        "type": "string",
                        "description": (
                            "An optional comment from about how the task seems "
                            "to be going, if he is interested and everything "
                            "else that did not fit in the other fields. It "
                            "will be passed to you the next time you ask for "
                            "this function."
                        )
                    },
                    "status": {
                        "type": "string",
                        "enum": ["pending", "running", "completed", "failed"],
                        "description": (
                            "The status of the task. Only use the ones "
                            "listed. Don't use percentages or any other "
                            "measure. If you need to supply additional "
                            "information, use the comment field."
                        )
                    },
                    "scheduled_for": {
                        "type": "string",
                        "format": "date",
                        "description": (
                            "The date when the task is scheduled to be "
                            "completed."
                        )
                    },
                    "scheduled_for_comment": {
                        "type": "string",
                        "description": (
                            "An optional comment about the scheduled date. "
                            "Use this when there is either no specific date, "
                            "they talk about a range, or something else that "
                            "is important."
                        )
                    }
                },
                "required": ["description", "status"]
            }
        }
    }
]

def extract_tasks_from_message(mistral: Mistral, message: str) -> list[Task]:
    """Extracts tasks from a message."""
    # Define a prompt for extracting tasks from the message
    prompt = (
        "Extract multiple tasks from the message at the end of this prompt "
        "and insert them into the database using the insert_task function.\n"
        f"Message: {message}"
    )
    response = mistral.chat.complete(
        model=MISTRAL_MODEL,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        tools=tools,
        tool_choice="any",
        parallel_tool_calls=True,
    )
    tasks: list[Task] = []
    for choice in response.choices:
        if choice.finish_reason == "tool_calls":
            for tool_call in choice.message.tool_calls:
                if tool_call.function.name == "insert_task":
                    logger.debug(f"Extracted task: {tool_call.function.arguments}")
                    task_desc = json.loads(tool_call.function.arguments)
                    try:
                        task = Task.from_llm_tool_call(task_desc)
                    except Exception as e:
                        logger.exception(f"The task could not be parsed!", exc_info=e)
                        continue
                    tasks.append(task)
                else:
                    logger.warning(f"Unknown tool call: {tool_call.function.name}")
        else:
            logger.warning(f"Unexpected finish reason: {choice.finish_reason}, {choice=}")
    return tasks



def generate_and_insert_sample_data(mistral: Mistral, cur: sqlite3.Cursor):
    """Ask the Mistral model for a few examples and insert them into the database."""
    logger.info("Generating sample data and inserting it")

    # Define a prompt for generating a sample message containing multiple tasks
    message_prompt = (
        "Generate a message that includes multiple tasks at different stages "
        f"of completion. Today's date is {date.today().isoformat()}."
    )

    # Use the Mistral client to generate a sample message
    messages_response = mistral.chat.complete(
        model=MISTRAL_MODEL,
        messages=[
            {
                "role": "user",
                "content": message_prompt,
            }
        ],
        max_tokens=150,
    )

    # Parse the generated message
    message_text = messages_response.choices[0].message.content.strip()

    # Create and insert the message
    message = Message.from_message(message_text)
    message_id = insert_message(cur, message)

    tasks = extract_tasks_from_message(mistral, message_text)
    for task in tasks:
        insert_task(cur, task)

    logger.info("Sample data generation and insertion completed")


def generate_mail_body(mistral: Mistral, cur: sqlite3.Cursor) -> str:
    """Generates the body of the email by querying the model."""


def main():
    if IS_DEV:
        logger.info("Running in development mode")
    else:
        logger.info("Running in production mode")

    # Initialize API Clients locally
    postmark = PostmarkClient(server_token=POSTMARK_SERVER_API_TOKEN)
    mistral = Mistral(api_key=MISTRAL_API_KEY)

    print(extract_tasks_from_message(mistral, "This is a test message. It does not contain any tasks."))

    logger.info(f"Connecting to SQLite database at {MESSAGE_DB_PATH}")
    with get_connection() as conn:
        cur = conn.cursor()

        if IS_DEV:
            cur.execute("DROP TABLE IF EXISTS messages;")
            cur.execute("DROP TABLE IF EXISTS tasks;")
        create_tables(cur)
        conn.commit()

        generate_and_insert_sample_data(mistral, cur)

if __name__ == "__main__":
    main()
