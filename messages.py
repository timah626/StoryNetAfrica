from dataclasses import dataclass
from enum import Enum
from typing import Any

class MessageType(Enum):
    REGISTER = "register"
    HEARTBEAT = "heartbeat"
    FILE_CHUNK = "file_chunk"
    TRANSFER_COMPLETE = "transfer_complete"
    CHUNK_LOSS_REPORT = "chunk_loss_report"

@dataclass
class Message:
    type: MessageType
    sender: str
    recipient: str = None
    payload: Any = None
    transfer_id: str = None
