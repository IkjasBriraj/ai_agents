import operator
import time
import logging
import traceback
from typing import TypedDict, Annotated, List, Dict, Any, Optional
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, BaseMessage, ToolMessage
from langgraph.graph import StateGraph, START, END

logger = logging.getLogger(__name__)

class ToolCallingState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]
    step_count: int
    max_steps: int
    final_response: Optional[str]
    tools_executed: List[str]
    token_usage: Dict[str, int]
    callbacks: Optional[List[Any]]

class ToolCallingLoop:
    def __init__(self, llm, tools: List, system_prompt: str, max_steps: int = 15, max_execution_time: int = 300):
        self.llm = llm
        self.tools = tools
        self.system_prompt = system_prompt
        self.max_steps = max_steps
        self.max_execution_time = max_execution_time
        
        self.tool_map = {tool.name: tool for tool in tools}
        
        self.supports_tool_calling = True
        try:
            if hasattr(llm, "bind_tools"):
                self.tool_llm = llm.bind_tools(tools)
            else:
                self.supports_tool_calling = False
                self.tool_llm = llm
        except Exception as e:
            logger.warning(f"LLM does not support bind_tools: {e}")
            self.supports_tool_calling = False
            self.tool_llm = llm

        builder = StateGraph(ToolCallingState)
        builder.add_node("invoke_llm", self._invoke_llm)
        builder.add_node("execute_tools", self._execute_tools)
        
        builder.add_edge(START, "invoke_llm")
        builder.add_conditional_edges(
            "invoke_llm",
            self._should_continue,
            {
                "execute_tools": "execute_tools",
                "end": END
            }
        )
        builder.add_edge("execute_tools", "invoke_llm")
        
        self.graph = builder.compile()

    def _format_tool_error(self, tool_name: str, error: Exception) -> str:
        return f"Error executing tool {tool_name}: {str(error)}\nTraceback: {traceback.format_exc()}"

    def _invoke_llm(self, state: ToolCallingState) -> dict:
        step_count = state.get("step_count", 0)
        max_steps = state.get("max_steps", self.max_steps)
        messages = state.get("messages", [])
        
        if step_count >= max_steps:
            return {
                "final_response": "Max steps exceeded. Forcing exit.",
                "step_count": step_count
            }
            
        sys_msg = SystemMessage(content=self.system_prompt)
        full_messages = [sys_msg] + messages
        
        try:
            response = self.tool_llm.invoke(full_messages)
        except Exception as e:
            logger.error(f"Error invoking LLM: {e}")
            return {
                "final_response": f"Error during generation: {e}",
                "step_count": step_count + 1
            }
            
        token_usage = state.get("token_usage", {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}).copy()
        if hasattr(response, "response_metadata") and "token_usage" in response.response_metadata:
            usage = response.response_metadata["token_usage"]
            token_usage["prompt_tokens"] += usage.get("prompt_tokens", 0)
            token_usage["completion_tokens"] += usage.get("completion_tokens", 0)
            token_usage["total_tokens"] += usage.get("total_tokens", 0)

        return {
            "messages": [response],
            "step_count": step_count + 1,
            "token_usage": token_usage
        }

    def _execute_tools(self, state: ToolCallingState) -> dict:
        messages = state.get("messages", [])
        last_msg = messages[-1]
        
        if not isinstance(last_msg, AIMessage) or not last_msg.tool_calls:
            return {}
            
        tools_executed = state.get("tools_executed", []).copy()
        tool_messages = []
        callbacks = state.get("callbacks", [])
        
        for tool_call in last_msg.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]
            tool_id = tool_call["id"]
            
            if tool_name not in self.tool_map:
                error_msg = f"Tool {tool_name} not found."
                tool_messages.append(ToolMessage(content=error_msg, tool_call_id=tool_id, name=tool_name))
                continue
                
            tool = self.tool_map[tool_name]
            tools_executed.append(tool_name)
            
            try:
                if callbacks:
                    for cb in callbacks:
                        if hasattr(cb, 'on_tool_start'):
                            cb.on_tool_start({"name": tool_name}, tool_args)
                            
                result = tool.invoke(tool_args)
                
                if callbacks:
                    for cb in callbacks:
                        if hasattr(cb, 'on_tool_end'):
                            cb.on_tool_end(result)
                            
                tool_messages.append(ToolMessage(content=str(result), tool_call_id=tool_id, name=tool_name))
            except Exception as e:
                error_str = self._format_tool_error(tool_name, e)
                if callbacks:
                    for cb in callbacks:
                        if hasattr(cb, 'on_tool_error'):
                            cb.on_tool_error(e)
                tool_messages.append(ToolMessage(content=error_str, tool_call_id=tool_id, name=tool_name))
                
        return {
            "messages": tool_messages,
            "tools_executed": tools_executed
        }

    def _should_continue(self, state: ToolCallingState) -> str:
        if state.get("final_response"):
            return "end"
            
        step_count = state.get("step_count", 0)
        if step_count >= state.get("max_steps", self.max_steps):
            return "end"
            
        messages = state.get("messages", [])
        if not messages:
            return "end"
            
        last_msg = messages[-1]
        
        if isinstance(last_msg, AIMessage) and getattr(last_msg, 'tool_calls', None):
            ai_msgs = [m for m in messages if isinstance(m, AIMessage) and getattr(m, 'tool_calls', None)]
            if len(ai_msgs) >= 3:
                last_3 = ai_msgs[-3:]
                if last_3[0].tool_calls == last_3[1].tool_calls == last_3[2].tool_calls:
                    logger.warning("Detected duplicate tool calls in 3 consecutive iterations. Forcing end.")
                    return "end"
            return "execute_tools"
            
        return "end"

    def invoke(self, task: str, chat_history: str = '', callbacks: Optional[List] = None, context: Optional[Dict] = None) -> str:
        messages = []
        if chat_history:
            messages.append(SystemMessage(content=f"Chat History:\n{chat_history}"))
            
        messages.append(HumanMessage(content=task))
        
        initial_state = {
            "messages": messages,
            "step_count": 0,
            "max_steps": self.max_steps,
            "final_response": None,
            "tools_executed": [],
            "token_usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            "callbacks": callbacks or []
        }
        
        try:
            result_state = self.graph.invoke(initial_state)
            
            if result_state.get("final_response"):
                return result_state["final_response"]
                
            messages_out = result_state.get("messages", [])
            if messages_out:
                last_msg = messages_out[-1]
                if isinstance(last_msg, AIMessage):
                    return last_msg.content or "Empty final message."
            return "No response generated."
            
        except Exception as e:
            logger.error(f"Error in execution loop: {e}")
            return f"Execution failed: {str(e)}"
            
    def supports_native_tools(self) -> bool:
        return self.supports_tool_calling
