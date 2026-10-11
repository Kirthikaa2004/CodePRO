from src.utils.helper import get_llm
from src.utils.custom_app_exception import CustomAppException
from langchain.agents import create_agent
from src.prompts.coding_agent_prompt import SYSTEM_PROMPT
from langchain_core.messages import SystemMessage,HumanMessage
from src.clients.client import create_client
from settings import config
import re
from src.utils.helper import get_llm
from src.utils.helper import logger

class CodingAgent:
    def __init__(self):
            self.tools = []
            self.client = None
            self.system_prompt = SYSTEM_PROMPT
            self.llm = None
            
    
    # async def load_tools(self):
    #     try:
    #         context7_headers = {re
    #               "CONTEXT7_API_KEY":config.context7_api_key
    #          }
    #         context7_client = await create_client(client_url=config.context7_server_url,server_name="context7",headers=context7_headers)

    #         context7_tools = await context7_client.get_tools()
    #         self.tools.append(context7_tools)

    #         pep8_client = await create_client(client_url=config.pep8_server_url,server_name="pep8")
    #         pep8_tools = await pep8_client.get_tools()
    #         self.tools.append(pep8_tools)

    #     except CustomAppException:
    #           raise
    #     except Exception as e:
    #          raise CustomAppException(
    #               message=f"Failed to load tools: {str(e)}",
    #               status_code=500,
    #               err_code="LOAD_TOOL_ERR"
    #          )
         
    async def create_agent(self):
          try:
                logger.info("create_agent in coding_agent is triggered...")
                llm = await get_llm()
                agent = create_agent(
                    
                    model = llm,
                    tools = self.tools,
                    system_prompt=SystemMessage(self.system_prompt)

                )
                self.agent = agent
                return agent
          except CustomAppException:
            raise
          except Exception as e:
               raise CustomAppException(
                    message=f"Failed to create agent : {str(e)}",
                    status_code=500,
                    err_code="CREATE_AGENT_ERR"
               )
          
    async def run_agent(self,user_message:str):
        try:
             logger.info("create_agent in coding_agent is triggered...")
             agent_response = await self.agent.ainvoke(
                  {
                       "messages":[HumanMessage(content=user_message)]
                  }
             )

             print(agent_response['messages'][-1],' coding agent response')
             response = agent_response['messages'][-1].content

             if response.startswith("```"):
                response = re.sub(r'^```[a-z]*\n|```$', '', response, flags=re.MULTILINE)
             return response

        except CustomAppException:
            raise
        except Exception as e:
               raise CustomAppException(
                    message=f"Failed to run agent : {str(e)}",
                    status_code=500,
                    err_code="RUN_AGENT_ERR"
               )
         
def get_coding_agent():
     return CodingAgent()