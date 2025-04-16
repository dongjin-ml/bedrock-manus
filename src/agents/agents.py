#from langgraph.prebuilt import create_react_agent

#from src.prompts import apply_prompt_template
# from src.tools import (
#     bash_tool,
#     browser_tool,
#     crawl_tool,
#     python_repl_tool,
#     tavily_tool,
# )

from .llm import get_llm_by_type
from src.config.agents import AGENT_LLM_MAP
from src.prompts.template import apply_prompt_template
from src.agents.llm import get_llm_by_type, llm_call
from src.tools.research_tools import research_tool_config, process_search_tool

class create_react_agent():

    def __init__(self, **kwargs):

        self.agent_name = kwargs["agent_name"]
        self.llm = get_llm_by_type(AGENT_LLM_MAP[self.agent_name])
        self.llm.stream = True
        self.llm_caller = llm_call(llm=self.llm, verbose=False, tracking=False)
        
        # 반복 대화 처리를 위한 설정
        self.MAX_TURNS = 15  # 무한 루프 방지용 최대 턴 수
        self.turn = 0
        self.final_response = False
        
    def invoke(self, **kwargs):

        state = kwargs.get("state", None)
        system_prompts, messages = apply_prompt_template(self.agent_name, state)
        
        # 도구 사용이 종료될 때까지 반복
        while not self.final_response and self.turn < self.MAX_TURNS:
            self.turn += 1
            print(f"\n--- 대화 턴 {self.turn} ---")

            response, ai_message = self.llm_caller.invoke(
                messages=messages,
                system_prompts=system_prompts,
                tool_config=research_tool_config,
                enable_reasoning=False,
                reasoning_budget_tokens=8192
            )
            messages.append(ai_message)    

            print ("======")
            #print (messages)
            print(f"응답 상태: {response['stop_reason']}")

            # 도구 사용 요청 확인
            if response["stop_reason"] == "tool_use":
                print("모델이 도구 사용을 요청했습니다.")

                tool_requests_found = False

                # 응답에서 모든 도구 사용 요청 처리
                for content in ai_message['content']:
                    if 'toolUse' in content:
                        tool = content['toolUse']
                        tool_requests_found = True

                        print(f"요청된 도구: {tool['name']}")
                        print(f"입력 데이터: {tool['input']}")

                        tool_result_message = process_search_tool(tool)

                        # 결과 메시지를 대화에 추가
                        messages.append(tool_result_message)
                        print(f"도구 실행 결과를 대화에 추가했습니다.")

                # 도구 요청이 없으면 루프 종료
                if not tool_requests_found:
                    print("도구 요청을 찾을 수 없습니다.")
                    self.final_response = True
            else:
                # 도구 사용이 요청되지 않았으면 최종 응답으로 간주
                self.final_response = True
                print("최종 응답을 받았습니다.")

        print("\n=== 대화 완료 ===")
        print("최종 응답:", response)
        print("메시지:", ai_message)
        
        return ai_message

        
        

# Create agents using configured LLM types
# research_agent = create_react_agent(
#     get_llm_by_type(AGENT_LLM_MAP["researcher"]),
#     tools=[tavily_tool, crawl_tool],
#     prompt=lambda state: apply_prompt_template("researcher", state),
# )

research_agent = create_react_agent(agent_name="researcher")


# coder_agent = create_react_agent(
#     get_llm_by_type(AGENT_LLM_MAP["coder"]),
#     #tools=[python_repl_tool, bash_tool],
#     prompt=lambda state: apply_prompt_template("coder", state),
# )

coder_agent = None

# browser_agent = create_react_agent(
#     get_llm_by_type(AGENT_LLM_MAP["browser"]),
#     #tools=[browser_tool],
#     prompt=lambda state: apply_prompt_template("browser", state),
# )

browser_agent = None
