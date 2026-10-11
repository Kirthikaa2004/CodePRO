from langgraph.graph import StateGraph, END
from src.models.coding_model import CommonState
from src.utils.helper import get_llm
from fastapi import Depends
from langchain_core.messages import SystemMessage,HumanMessage
from src.prompts.decision_node_prompt import DECISION_PROMPT
from src.agents.coding_agent import CodingAgent,get_coding_agent
from src.agents.review_agent import ReviewAgent,get_review_agent
from src.agents.research_agent import ResearchAgent,get_research_agent
from src.utils.custom_app_exception import CustomAppException
from typing import Literal
from src.utils.helper import logger
import json

class GraphService:

    def __init__(self):
        self.coding_agent = CodingAgent()
        self.review_agent = ReviewAgent()
        self.research_agent =  ResearchAgent()

    async def decision_node(self,state:CommonState):
        logger.info("decision_node  is triggered ...")
        user_message = state.get("message")
        
        llm = await get_llm()
        messages = [
       SystemMessage(DECISION_PROMPT),
       HumanMessage(user_message)
        ]

        ai_msg = llm.invoke(messages)
        response = json.loads(ai_msg.content)
        print(response,'response')
        
        state_response = {}
        if 'response' in  response:
            state_response = {
                "type": response['intent'],
                "code": response['response'],
                "current_node":"decision_node",
                "review_status" : "NONE"
            }
        else:
            state_response  = {
                "type": response['intent'],
                "current_node":"decision_node",
                "review_status" : "NONE"
            }
        
        print(state_response,'state')
        return state_response
        
        


    
    async def coding_agent_node(self,state:CommonState):
        try:
            
            logger.info("coding_agent_node  is triggered ...")

            user_message = state['message']
            

            
            if 'issues_detected' in state or 'error' in state:

                issues = ''

                for issue in state['issues_detected']:
                    issues+=issue
                    
                user_message = "errors: " + "\n" + state['error'] +"\n" + "issues_detected: "  + issues + "\n" + "code: " + state['code']

            await self.coding_agent.create_agent()
            agent_response = await self.coding_agent.run_agent(user_message=user_message)
            response = json.loads(agent_response)
            
            print(response,'code')
            return {"code": response['code'], "current_node": "coding_node"}
        except CustomAppException:
            raise
        except Exception as e:
            logger.info("Error in coding_agent_node ...")
            raise CustomAppException(
                message=f"Err at coding_agent_node : {str(e)}",
                status_code=500,
                err_code="NODE_INIT_ERR"
            )

    async def review_agent_node(self,state:CommonState):
        try:
            logger.info(" review_agent_node is triggered ...") 
            # await self.review_agent.load_tools()
            await self.review_agent.create_agent()

            if 'code' in state:    
                code = state['code']
                message = "Here is the code you have to revie : " + "\n" + code
            else:
                message = state['message']
            
            agent_response = await self.review_agent.run_agent(user_message=message)
            
            response = json.loads(agent_response)
            print('response review' , response)

            return {
                "error":response['error'] if 'error' in response else '',
                "issues_detected" : response['issues_detected'] if 'issues_detected' in response else '',
                "review_status":response['status'],
                "current_node":"review_node",
                "code":state['code'] if 'code' in state else state['message']
            }
        except CustomAppException:
            raise
        except Exception as e:
            logger.info("Error in review_agent_node ...")
            raise CustomAppException(
                message=f"Err at review_agent_node : {str(e)}",
                status_code=500,
                err_code="NODE_INIT_ERR"
            )

    async def research_agent_node(self,state:CommonState):
        try:
            
            logger.info(" research_agent_node is triggered ...")
            await self.research_agent.load_tools()
            await self.research_agent.create_agent()

            if 'code' in state:
                message = "code : "  + state['code'] + "\n" + "error: " + state['error']  + "\n" + 'issues_detected:' + state['issues_detected']
            else:
                message = state['message']

            
            agent_response = await self.research_agent.run_agent(user_message=message)
            response = json.loads(agent_response)
            print(response,'response')
            return {
                "research_context":response['research_context'],
                "current_node":"research_node"
            }
        except CustomAppException:
            raise
        except Exception as e:
            logger.info("Error in research_agent_node ...")
            raise CustomAppException(
                message=f"Err at research_agent_node : {str(e)}",
                status_code=500,
                err_code="NODE_INIT_ERR"
            )
    
    async def decision_router(self,state:CommonState) -> Literal["decision_node","coding_node","review_node","research_node","END"]:
        try:

            logger.info("decision_router  is triggered ...")
            current_node = state["current_node"]
            type = state["type"]
            status = state["review_status"]
            
            decision_map = {
                "coding" : "coding_node",
                "review":"review_node",
                "research":"research_node",
                "research_and_code":"research_node",
                "off_context":"END"

            }
            

            print(type,'  : type',current_node,'  : current_node')
            if current_node == "research_node" and (type =="research_and_code" or type == "review"):
                return "coding_node"
            elif current_node == "research_node" and type =="research":
                return "END"
            elif current_node == "review_node" and status == "FAILED":
                print('came in mf')
                return "coding_node"
            elif current_node == "review_node":
                return "END"
            else:
                return decision_map[type]

        except CustomAppException:
            raise
        except Exception as e:
            logger.info("Error in decision_router ...")
            raise CustomAppException(
                message=f"Err at decision_router : {str(e)}",
                status_code=500,
                err_code="DECISION_ROUTER_ERR"
            )

    
    async def compile_graph(self):
        try:

            logger.info("compile_graph  is triggered ...")
            graph = StateGraph(CommonState)
            graph.add_node('decision_node',self.decision_node)
            graph.add_node('coding_node',self.coding_agent_node)
            graph.add_node('review_node',self.review_agent_node)
            graph.add_node('research_node',self.research_agent_node)

            logger.info("nodes are added to graph ...")
            

            
            graph.set_entry_point("decision_node")
            graph.add_conditional_edges(
                "decision_node",
                self.decision_router,
                {
                    "coding_node":"coding_node",
                    "review_node":"review_node",
                    "research_node":"research_node",
                    "END":END
                }
            )

            graph.add_edge("coding_node","review_node")
            graph.add_conditional_edges(
                "review_node",
                self.decision_router,
                {
                   "coding_node":"coding_node",
                   "END":END
                })
            graph.add_conditional_edges(     
                "research_node",
                self.decision_router,
                {
                    "coding_node":"coding_node",
                    "END":END
                })
            logger.info("edges are added and graph is compiled...")
            return graph

            
        except CustomAppException:
            raise
        except Exception as e:
            logger.info("Error in compiling graph ...")
            raise CustomAppException(
                message=f"Err at compiling graph : {str(e)}",
                status_code=500,
                err_code="COMPILE_GRAPH_ERR"
            )
        
    async def invoke_graph(self,user_message:str,session_id:str,app):
        try:
            logger.info("invoke_graph  is triggered ...")
            graph = app.state.graph
            session_config = {
                "configurable":{
                    "thread_id":str(session_id)
                }
            }
            result = await graph.ainvoke(
                {
                "message":user_message},
                config = session_config)
            

            print(f"\n--- History for Session: {session_id} ---")
        

            async for state in graph.aget_state_history(session_config):

                node_name = state.metadata.get("source")
                step = state.metadata.get("step")
                checkpoint_id = state.config["configurable"].get("checkpoint_id")
                

                current_values = state.values 
                
                print(f"Step {step} | Node: {node_name}")
                print(f"Checkpoint ID: {checkpoint_id}")
                print(f"Current State: {current_values}")
                print("-" * 30)


            print(result , 'result')
            return result
        except CustomAppException:
            raise
        except Exception as e:
            logger.info("Error in invoking graph ...")
            raise CustomAppException(
                message=f"Err at invoking graph : {str(e)}",
                status_code=500,
                err_code="invoke_graph_ERR"
            )


def get_graph_service():
    return GraphService()