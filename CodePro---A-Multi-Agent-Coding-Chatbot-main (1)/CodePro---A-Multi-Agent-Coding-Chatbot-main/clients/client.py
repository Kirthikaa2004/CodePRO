from langchain_mcp_adapters.client import MultiServerMCPClient
from src.utils.custom_app_exception import CustomAppException
from src.utils.helper import logger

def create_client(client_url:str,server_name:str):
    try: 
        logger.info("create_client triggered...")
        client_config =        {
            server_name:{
                "transport":"streamable_http",
                "url":client_url
            }
        }
        client = MultiServerMCPClient(client_config)
        return client
    except CustomAppException:
        raise
    except Exception as e:
        logger.info("Error in MCPClient  initialization ...")
        raise CustomAppException(
            message=f"MCPClient create initialization err: {str(e)}",
            status_code=500,
            err_code="MCP_CLIENT_INIT_ERROR"
        )