"""Discord bot interface for the Grug assistant server."""

from datetime import UTC, datetime, timedelta

import discord
import discord.utils
import orjson
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph.graph import CompiledGraph
from loguru import logger
from pydantic import BaseModel, Field

from grug.settings import settings


class ShouldRespondEvaluationOutput(BaseModel):
    relevance_score: int = Field(
        ...,
        description="Relevance score (1-10) for how appropriate it is for the agent to respond.",
    )
    confidence_score: int = Field(
        ...,
        description="Confidence score (1-10) on how well the agent can provide a useful response.",
    )


class DiscordMessageClient:
    """Discord message client for the Grug assistant server."""

    def __init__(self, discord_client: discord.Client, react_agent: CompiledGraph):
        self.discord_client = discord_client
        self.react_agent = react_agent
        self._should_respond_llm = ChatOpenAI(
            model_name="gpt-4o-mini",
            openai_api_key=settings.openai_api_key,
        ).with_structured_output(ShouldRespondEvaluationOutput)

        # Register the on_message event handler
        discord_client.event(self.on_message)

    async def on_message(self, message: discord.Message):
        """on_message event handler for the Discord bot."""

        # TODO: make a tool that can search chat history for a given channel

        # ignore messages from self and all bots
        if message.author == self.discord_client.user or message.author.bot:
            return

        channel_is_text_or_thread = isinstance(message.channel, discord.TextChannel) or isinstance(
            message.channel, discord.Thread
        )

        # Determine if the bot should evaluate if it should respond
        should_respond = False
        if (
            settings.discord_bot_enable_contextual_responses
            and channel_is_text_or_thread
            and self.discord_client.user not in message.mentions
        ):
            # Evaluate the message to determine if the bot should respond
            should_respond = await self.should_respond(message=message)

        # get the agent config based on the current message
        agent_config = {
            "configurable": {
                "thread_id": str(message.channel.id),
                "user_id": f"{str(message.guild.id) + '-' if message.guild else ''}{message.author.id}",
            }
        }

        # Message is @mention or DM or should_respond is True
        if (
            isinstance(message.channel, discord.DMChannel)
            or (channel_is_text_or_thread and self.discord_client.user in message.mentions)
            or should_respond
        ):
            async with message.channel.typing():
                messages: list[BaseMessage] = []

                # Handle replies
                if message_replied_to := message.reference.resolved.content if message.reference else None:
                    messages.append(
                        SystemMessage(
                            f'You previously sent the following message: "{message_replied_to}", assume that that '
                            "you are responding to a reply to that message."
                        )
                    )

                # Add the message that the user sent
                messages.append(HumanMessage(message.content))

                final_state = await self.react_agent.ainvoke(
                    input={"messages": messages},
                    config=agent_config,
                )

                await message.channel.send(
                    content=final_state["messages"][-1].content,
                    reference=message if channel_is_text_or_thread else None,
                )

        # Otherwise, add the message to the conversation history without requesting a response
        else:
            await self.react_agent.aupdate_state(
                config=agent_config,
                values={"messages": [HumanMessage(message.content)]},
            )

    async def should_respond(
        self,
        message: discord.Message,
        message_history_lookback_hours: int = 1,
        relevance_threshold: int = 7,
        confidence_threshold: int = 5,
    ) -> bool:
        conversation_history = orjson.dumps(
            [
                {
                    "author": message.author.display_name,
                    "timestamp": message.created_at.isoformat(),
                    "message_content": message.content,
                }
                async for message in message.channel.history(
                    after=datetime.now(tz=UTC) - timedelta(hours=message_history_lookback_hours)
                )
            ]
        ).decode()

        response = await self._should_respond_llm.ainvoke(
            [
                SystemMessage(
                    content=f"""
                - Your job is to determine if '{settings.ai_name}' should respond to a given message, based on the `chat_history` and the `message` sent.
                - Your job is to assess the message within the context of the conversation and provide:
                    1. A relevance score (1-10): Based on the message sent, how likely is it that the user expected '{settings.ai_name}' to respond?
                    2. A confidence score (1-10): How confident would '{settings.ai_name}' be in providing a helpful response?

                - chat_history: {conversation_history}
            """
                ),
                HumanMessage(
                    content=f"Conversation history:\n{conversation_history}\n\nNew message:\n{message.content}"
                ),
            ]
        )

        logger.info(f"response_eval: {response}")

        # Determine if the bot should respond based on the evaluation scores
        return response.relevance_score > relevance_threshold and response.confidence_score > confidence_threshold
