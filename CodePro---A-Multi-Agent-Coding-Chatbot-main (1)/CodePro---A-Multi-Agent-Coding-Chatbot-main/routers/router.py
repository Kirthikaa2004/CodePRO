from fastapi import APIRouter,Depends
from src.services.coding_service import CodingService,get_coding_service
from src.models.coding_model import CodeRequest
from src.utils.custom_app_exception import CustomAppException
from src.repositories.error_repository import ErrorRepository,get_err_repo
from fastapi import Request
from fastapi.responses import JSONResponse
from src.utils.helper import logger

router = APIRouter(prefix="/api")

@router.post("/chat")
async def generate_code(api_request:Request, request:CodeRequest,err_repo:ErrorRepository = Depends(get_err_repo),service:CodingService = Depends(get_coding_service)):
    try:
        logger.info('generate_code triggered....')
        response = await service.coding_service(message=request.user_query,user_id = request.user_id,session_id=request.session_id,app = api_request.app)

        return JSONResponse(
            content = response.model_dump(),
            status_code=200
        )
    except CustomAppException:
        raise
    except Exception as e:
        print(e)
        await err_repo.add_error(
            file_name="router.py",
            function_name="generate_code",
            message=f"Router err at generate_code : {str(e)}"
        )
        raise CustomAppException(
            message=f"Router err at generate_code : {str(e)}",
            status_code=500,
            err_code="ROUTER_ERR"
        )