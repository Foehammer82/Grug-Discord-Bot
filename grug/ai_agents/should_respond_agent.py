from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from grug.settings import settings


class EvaluationOutput(BaseModel):
    relevance_score: int = Field(
        ...,
        description="Relevance score (1-10) for how appropriate it is for the agent to respond.",
    )
    confidence_score: int = Field(
        ...,
        description="Confidence score (1-10) on how well the agent can provide a useful response.",
    )


class EvaluationAgent:
    def __init__(self):
        self.llm = ChatOpenAI(
            model_name="gpt-4o-mini",
            openai_api_key=settings.openai_api_key,
        ).with_structured_output(EvaluationOutput)

    async def evaluate_message(self, message: str, conversation_history: list[str]) -> EvaluationOutput:
        response = await self.llm.ainvoke(
            [
                SystemMessage(
                    content=f"""
                You are an evaluator AI that determines if the agent '{settings.ai_name}' should respond to a given message.
                Your job is to assess the message within the context of the conversation and provide:

                1. A relevance score (1-10): How appropriate is it for '{settings.ai_name}' to respond?
                   Specifically, what is the likelihood that the user wanted `{settings.ai_name}` to respond?
                2. A confidence score (1-10): How confident would '{settings.ai_name}' be in providing a helpful response?
            """
                ),
                HumanMessage(content=f"Conversation history:\n{conversation_history}\n\nNew message:\n{message}"),
            ]
        )
        return response
