# TODO: tie into the scheduler to set reminders that can be sent back to the user or group chat
from typing import Annotated

from langchain_core.tools import InjectedToolArg


async def set_reminder(message: str, user_id: Annotated[str, InjectedToolArg]):
    pass
