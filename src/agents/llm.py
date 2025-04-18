import os
from typing import Optional
from src.utils import bedrock
from src.utils.bedrock import bedrock_info, bedrock_model
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler

from langchain_openai import ChatOpenAI
from langchain_deepseek import ChatDeepSeek

from src.config import (
    REASONING_MODEL,
    REASONING_BASE_URL,
    REASONING_API_KEY,
    BASIC_MODEL,
    BASIC_BASE_URL,
    BASIC_API_KEY,
    VL_MODEL,
    VL_BASE_URL,
    VL_API_KEY,
)
from src.config.agents import LLMType

from textwrap import dedent
from src.utils.bedrock import bedrock_utils, bedrock_chain

class llm_call():

    def __init__(self, **kwargs):

        self.llm=kwargs["llm"]
        self.verbose = kwargs.get("verbose", False)
        self.chain = bedrock_chain(bedrock_utils.converse_api) | bedrock_chain(bedrock_utils.outputparser)

        self.origin_max_tokens = self.llm.inference_config["maxTokens"]
        self.origin_temperature = self.llm.inference_config["temperature"]
            
    def invoke(self, **kwargs):

        system_prompts = kwargs.get("system_prompts", None)
        messages = kwargs["messages"]
        enable_reasoning = kwargs.get("enable_reasoning", False)
        reasoning_budget_tokens = kwargs.get("reasoning_budget_tokens", 1024)
        tool_config = kwargs.get("tool_config", None)
        
        print ("enable_reasoning", enable_reasoning)
        
        if enable_reasoning:
            reasoning_config = {
                "thinking": {
                    "type": "enabled",
                    "budget_tokens": reasoning_budget_tokens
                }
            }

            # Ensure maxTokens is greater than reasoning_budget
            if self.llm.inference_config["maxTokens"] <= reasoning_budget_tokens:
                # Make it just one token more than the reasoning budget
                adjusted_max_tokens = reasoning_budget_tokens + 1
                print(f'Info: Extended Thinking enabled increasing maxTokens from {self.llm.inference_config["maxTokens"]} to {adjusted_max_tokens} to exceed reasoning budget')
                self.llm.inference_config["maxTokens"] = adjusted_max_tokens

            self.llm.additional_model_request_fields = reasoning_config
            self.llm.inference_config["temperature"] = 1.0

        print ("self.llm.additional_model_request_fields", self.llm.additional_model_request_fields)
        print ("self.llm.inference_config", self.llm.inference_config)
           
        response, ai_message = self.chain( ## pipeline의 제일 처음 func의 argument를 입력으로 한다. 여기서는 converse_api의 arg를 쓴다.
            llm=self.llm,
            system_prompts=system_prompts,
            messages=messages,
            tool_config=tool_config,
            verbose=self.verbose
        )
        
        #ai_message = self._message_format(role="assistant", message=response["text"])
        #messages.append(ai_message)

        # Reset
        if enable_reasoning:
            self.llm.additional_model_request_fields = None
            self.llm.inference_config["maxTokens"] = self.origin_max_tokens
            self.llm.inference_config["temperature"] = self.origin_temperature
            
        return response, ai_message

def create_openai_llm(
    model: str,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    temperature: float = 0.0,
    **kwargs,
) -> ChatOpenAI:
    """
    Create a ChatOpenAI instance with the specified configuration
    """
    # Only include base_url in the arguments if it's not None or empty
    llm_kwargs = {"model": model, "temperature": temperature, **kwargs}

    if base_url:  # This will handle None or empty string
        llm_kwargs["base_url"] = base_url

    if api_key:  # This will handle None or empty string
        llm_kwargs["api_key"] = api_key

    return ChatOpenAI(**llm_kwargs)


def create_deepseek_llm(
    model: str,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    temperature: float = 0.0,
    **kwargs,
) -> ChatDeepSeek:
    """
    Create a ChatDeepSeek instance with the specified configuration
    """
    # Only include base_url in the arguments if it's not None or empty
    llm_kwargs = {"model": model, "temperature": temperature, **kwargs}

    if base_url:  # This will handle None or empty string
        llm_kwargs["api_base"] = base_url

    if api_key:  # This will handle None or empty string
        llm_kwargs["api_key"] = api_key

    return ChatDeepSeek(**llm_kwargs)


# Cache for LLM instances
#_llm_cache: dict[LLMType, ChatOpenAI | ChatDeepSeek] = {}


def get_llm_by_type(llm_type: LLMType) -> ChatOpenAI | ChatDeepSeek:
    """
    Get LLM instance by type. Returns cached instance if available.
    """
    #if llm_type in _llm_cache:
    #    return _llm_cache[llm_type]
    
    boto3_bedrock = bedrock.get_bedrock_client(
        assumed_role=os.environ.get("BEDROCK_ASSUME_ROLE", None),
        endpoint_url=os.environ.get("BEDROCK_ENDPOINT_URL", None),
        region=os.environ.get("AWS_DEFAULT_REGION", None),
    )

    if llm_type == "reasoning":
        llm = bedrock_model(
            model_id=bedrock_info.get_model_id(model_name="Claude-V3-7-Sonnet-CRI"),
            bedrock_client=boto3_bedrock,
            stream=True,
            callbacks=[StreamingStdOutCallbackHandler()],
            inference_config={
                'maxTokens': 8192*3,
                #'stopSequences': ["\n\nHuman"],
                'temperature': 0.01,
            }
        )
        
    elif llm_type == "basic":
        llm = bedrock_model(
            #model_id=bedrock_info.get_model_id(model_name="Claude-V3-7-Sonnet-CRI"),
            model_id=bedrock_info.get_model_id(model_name="Claude-V3-5-V-2-Sonnet-CRI"),
            bedrock_client=boto3_bedrock,
            stream=True,
            callbacks=[StreamingStdOutCallbackHandler()],
            inference_config={
                'maxTokens': 8192,
                #'stopSequences': ["\n\nHuman"],
                'temperature': 0.01,
            }
        )
    elif llm_type == "vision":
        llm = bedrock_model(
            #model_id=bedrock_info.get_model_id(model_name="Claude-V3-7-Sonnet-CRI"),
            model_id=bedrock_info.get_model_id(model_name="Claude-V3-5-V-2-Sonnet-CRI"),
            bedrock_client=boto3_bedrock,
            stream=True,
            callbacks=[StreamingStdOutCallbackHandler()],
            inference_config={
                'maxTokens': 8192,
                #'stopSequences': ["\n\nHuman"],
                'temperature': 0.01,
            }
        )
    else:
        raise ValueError(f"Unknown LLM type: {llm_type}")

    #_llm_cache[llm_type] = llm
    return llm


# Initialize LLMs for different purposes - now these will be cached
reasoning_llm = get_llm_by_type("reasoning")
basic_llm = get_llm_by_type("basic")
vl_llm = get_llm_by_type("vision")


if __name__ == "__main__":
    stream = reasoning_llm.stream("what is mcp?")
    full_response = ""
    for chunk in stream:
        full_response += chunk.content
    print(full_response)

    basic_llm.invoke("Hello")
    vl_llm.invoke("Hello")
