"""Discord bot interface for the Grug assistant server."""

import discord
import discord.utils
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langgraph.graph.graph import CompiledGraph


class DiscordMessageClient:
    """Discord message client for the Grug assistant server."""

    def __init__(self, discord_client: discord.Client, react_agent: CompiledGraph):
        self.discord_client = discord_client
        self.react_agent = react_agent

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

        # get the agent config based on the current message
        agent_config = {
            "configurable": {
                "thread_id": str(message.channel.id),
                "user_id": f"{str(message.guild.id) + '-' if message.guild else ''}{message.author.id}",
            }
        }

        # Respond if message is @mention or DM or should_respond is True
        is_direct_message = isinstance(message.channel, discord.DMChannel)
        is_at_message = channel_is_text_or_thread and self.discord_client.user in message.mentions
        if is_direct_message or is_at_message:
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
