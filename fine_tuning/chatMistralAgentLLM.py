# in your fine_tuning/2_generate_cypher_synthetic_data.py (or a separate file you import):
import os
from typing import List, Optional, Any
from langchain.chat_models.base import BaseChatModel
from langchain.schema import (
    AIMessage,
    HumanMessage,
    SystemMessage,
    ChatResult,
    ChatGeneration
)
from mistralai import Mistral

# ag:3f458655:20250127:finetune-codestral-on-rulac-data:6b7c8e5c

class ChatMistralAgent(BaseChatModel):
    def __init__(self, agent_id: str, temperature: float = 0.0, max_retries: int = 2):
        super().__init__()
        self.agent_id = agent_id
        self.temperature = temperature
        self.max_retries = max_retries
        self._client = Mistral(api_key=os.environ["MISTRAL_API_KEY"])

    def _generate(
        self,
        messages: List[Any],  # List of langchain.schema.BaseMessage
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any,
    ) -> ChatResult:
        # Convert LangChain messages to Mistral "messages" format
        mistral_messages = []
        for msg in messages:
            if isinstance(msg, HumanMessage):
                role = "user"
            elif isinstance(msg, SystemMessage):
                role = "system"
            elif isinstance(msg, AIMessage):
                role = "assistant"
            else:
                # fallback for unknown message type
                role = "user"
            mistral_messages.append({"role": role, "content": msg.content})

        # Send request to Mistral Agent
        # If your agent supports temperature, top_p, etc. you can pass them in "options"
        response = self._client.agents.complete(
            agent_id=self.agent_id,
            messages=mistral_messages,
            options={
                "temperature": self.temperature
                # add other decoding params here if your agent supports them
            },
        )

        # Extract the assistant response
        content = response.choices[0].message.content
        
        # Build a ChatResult for LangChain
        ai_message = AIMessage(content=content)
        return ChatResult(
            generations=[ChatGeneration(message=ai_message)],
            llm_output={"token_usage": {}}  # or other usage info if available
        )
