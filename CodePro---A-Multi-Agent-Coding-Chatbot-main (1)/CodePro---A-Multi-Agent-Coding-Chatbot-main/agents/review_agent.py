from src.utils.helper import get_llm
from src.utils.custom_app_exception import CustomAppException
from langchain.agents import create_agent
from src.prompts.review_agent_prompt import SYSTEM_PROMPT
from langchain_core.messages import SystemMessage,HumanMessage
from settings import config
from src.clients.client import create_client
from src.utils.helper import get_llm
from src.tools.tool import detailed_code_review
import re
from src.models.coding_model import ReviewResponseModel
from langchain_mcp_adapters.client import load_mcp_tools
from langchain_mcp_adapters.client import MultiServerMCPClient

class ReviewAgent:
    def __init__(self):
            self.tools = []
            self.client = None
            self.system_prompt = SYSTEM_PROMPT


    async def load_tools(self):
        try:


            pep8_client = create_client(client_url=config.pep8_server_url,server_name="pep8-server")
            pep8_tools = await pep8_client.get_tools()

            self.tools = [tool for tool in pep8_tools if tool.name == "format_code"]

        except CustomAppException:
              raise
        except Exception as e:
             raise CustomAppException(
                  message=f"Failed to load tools: {str(e)}",
                  status_code=500,
                  err_code="LOAD_TOOL_ERR"
             )
        
    async def create_agent(self):
          try:
                llm = await get_llm()
                structured_llm = llm.with_structured_output(ReviewResponseModel)
                agent = create_agent(
                    
                    model = llm,
                    tools = [detailed_code_review],
                    system_prompt=SystemMessage(self.system_prompt)

                )
                self.agent = agent
                
          except CustomAppException:
            raise
          except Exception as e:
               raise CustomAppException(
                    message=f"Failed to create agent : {str(e)}",
                    status_code=500,
                    err_code="REVIEW_CREATE_AGENT_ERR"
               )
          
    async def run_agent(self,user_message:str):
        try:
             agent_response = await self.agent.ainvoke(
                  {
                       "messages":[HumanMessage(content=user_message)]
                  }
             )

             print(agent_response,'agent')
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
                    err_code="REVIEW_RUN_AGENT_ERR"
               )
         
def get_review_agent():
     return ReviewAgent()