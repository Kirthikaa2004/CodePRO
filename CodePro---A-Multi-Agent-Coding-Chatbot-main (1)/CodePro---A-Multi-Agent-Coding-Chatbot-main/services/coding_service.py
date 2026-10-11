from fastapi import Depends
from src.repositories.coding_repository import CodingRepository,get_coding_repo
from src.repositories.error_repository import ErrorRepository,get_err_repo
from src.utils.custom_app_exception import CustomAppException
from src.services.graph_service import get_graph_service,GraphService
from fastapi import Depends
from src.utils.helper import logger
from src.models.coding_model import APIResponse
import uuid


class CodingService:
    def __init__(self,service,err_repo,coding_repo):
        self.graph_service = service 
        self.err_repo = err_repo
        self.coding_repo = coding_repo
        

    async def coding_service(self,message:str,user_id:str,app,session_id : str):
        try:
            
          
            logger.info("coding_service triggered successfully...")
            user = await self.coding_repo.check_user(user_id=user_id)

            if not user:
                logger.info("user not found...")
                raise CustomAppException(
                    message=f"User Not Found ",
                    status_code=404,
                    err_code="USER_NOT_FOUND"
                )
            
            user_thread = await self.coding_repo.check_thread(user_id=user_id,thread_id=session_id)
            print(user_thread,'user thread')
            if not user_thread:
                logger.info("creating new session id....")
                session_id = uuid.uuid4()
                await self.coding_repo.add_user_thread(user_id = user_id,thread_id = session_id)
            
            graph_response = await self.graph_service.invoke_graph(user_message = message,session_id = session_id,app = app)
            
            response = {}
            print(graph_response)
            if 'code' in graph_response:
                response = graph_response['code']
            elif 'research_context' in graph_response:
                response = graph_response['research_context']
           
            return APIResponse(
                data = response ,
                message="Code generated Successfully",
                status_code=200
            )
        
            
        except CustomAppException:
            raise
        except Exception as e:
            print(e)
            await self.err_repo.add_error(
                file_name="coding_service",
                function_name="coding_service",
                message=f"Service err at CodingService: {str(e)}"
            )

            raise CustomAppException(
                 message=f"Service err at CodingService: {str(e)}",
                 status_code=500,
                 err_code="SERVICE_ERR"
            )
        
def get_coding_service(service:GraphService = Depends(get_graph_service),err_repo:ErrorRepository = Depends(get_err_repo),coding_repo:CodingRepository = Depends(get_coding_repo)):
    return CodingService(service,err_repo,coding_repo)