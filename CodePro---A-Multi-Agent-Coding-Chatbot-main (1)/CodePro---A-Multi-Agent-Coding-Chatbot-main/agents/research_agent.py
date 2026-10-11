from src.utils.helper import get_llm
from src.utils.custom_app_exception import CustomAppException
from src.prompts.research_agent_prompt import SYSTEM_PROMPT
from langchain.agents import create_agent
from langchain_core.messages import SystemMessage,HumanMessage
from settings import config
from src.models.coding_model import ResponseModel
import re
from src.clients.client import create_client
from src.utils.helper import logger
from langchain_core.callbacks import AsyncCallbackHandler

from langchain_core.messages import HumanMessage, AIMessage
from src.utils.helper import logger

class AgentDebugLog(AsyncCallbackHandler):
    async def on_chat_model_start(self, serialized, messages, **kwargs):
        """Runs BEFORE the model is invoked (Captures User Message)"""
        for msg_list in messages:
            for msg in msg_list:
                if isinstance(msg, HumanMessage):
                    print(f"\n[BEFORE MODEL] User Input: {msg.content}")

    async def on_llm_end(self, response, **kwargs):
        """Runs AFTER the model responds (Captures Tool Calls)"""
        for generation in response.generations:
            for res in generation:
                message = res.message
                if isinstance(message, AIMessage):
                    if message.tool_calls:
                        print(f"[AFTER MODEL] Tool Calls Found: {len(message.tool_calls)}")
                        for tool in message.tool_calls:
                            print(f"  -> Tool: {tool['name']} | Args: {tool['args']}")
                    else:
                        print("[AFTER MODEL] No Tool Calls. Model responded with text only.")
# --- Usage in your create_agent function ---


class ResearchAgent:
    def __init__(self):
            self.tools = []
            self.client = None
            self.system_prompt = SYSTEM_PROMPT


    async def load_tools(self):
        try:

            logger.info("load_tools in research_agent is triggered...")
            duckduckgo_client = create_client(client_url=config.duckduckgo_mcp_server_url,server_name="duckduckgo_server")
            duckduckgo_tools = await duckduckgo_client.get_tools()
            for tool in duckduckgo_tools:
                 print(tool , 'tool')
            self.tools = duckduckgo_tools
            print(self.tools , 'tools' , duckduckgo_tools,'toooools.......')


        except CustomAppException:
              raise
        except Exception as e:
             logger.info("Error in load_tools of research_agent ...")
             raise CustomAppException(
                  message=f"Failed to load tools: {str(e)}",
                  status_code=500,
                  err_code="LOAD_TOOL_ERR"
             )
        
    async def create_agent(self):
          try:
                logger.info("create_agent in research_agent is triggered...")
                llm = await get_llm()
                structured_llm = llm.with_structured_output(ResponseModel)
                print('tool load',self.tools)
                agent = create_agent(
                    
                    model = llm,
                    tools = self.tools,
                    system_prompt=SystemMessage(self.system_prompt)

                    # response_format=ResponseModel

                )
                self.agent = agent
                return agent
          except CustomAppException:
            raise
          except Exception as e:
               logger.info("Error in create_agent of research_agent ...")
               raise CustomAppException(
                    message=f"Failed to create agent : {str(e)}",
                    status_code=500,
                    err_code="CREATE_AGENT_ERR"
               )
          
    async def run_agent(self,user_message:str):
        try:
               debug_handler = AgentDebugLog()
               agent_response = await self.agent.ainvoke(
                  {
                       "messages":[HumanMessage(content=user_message)]     
                  },
                  config={"callbacks": [debug_handler]} 
             )
               
               print(agent_response,'research agent response')
               response = agent_response['messages'][-1].content

               if response.startswith("```"):
                  response = re.sub(r'^```[a-z]*\n|```$', '', response, flags=re.MULTILINE)

               print(response,'res')
               return response

        except CustomAppException:
            raise
        except Exception as e:
               logger.info("Error in run_agent of research_agent ...")
               raise CustomAppException(
                    message=f"Failed to run agent : {str(e)}",
                    status_code=500,
                    err_code="RUN_AGENT_ERR"
               )
         
def get_research_agent():
     return ResearchAgent()