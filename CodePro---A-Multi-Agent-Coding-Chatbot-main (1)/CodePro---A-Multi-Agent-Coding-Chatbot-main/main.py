from fastapi import FastAPI
from fastapi.responses import JSONResponse
from src.migrations.create_tables import create_tables
from src.routers.router import router
from src.utils.custom_app_exception import CustomAppException
from contextlib import asynccontextmanager
from src.repositories.database import Database
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg_pool import AsyncConnectionPool
from src.services.graph_service import GraphService
from settings import config
from src.utils.helper import logger

@asynccontextmanager
async def lifespan(app:FastAPI):
    try:
        db = Database()
        graph_service = GraphService()
        await create_tables(db.engine)
        logger.info("----- Tables Created Successfully -----")
        DATABASE_URL = (
                    f"postgresql://{config.db_username}:{config.db_password}"
                    f"@{config.db_host}:{config.db_port}/{config.db_name}"
                    )
        async with AsyncConnectionPool(conninfo=DATABASE_URL, max_size=20, kwargs={"autocommit": True}) as conn:
            checkpointer = AsyncPostgresSaver(conn)
            await checkpointer.setup()
            graph = await graph_service.compile_graph()
            app.state.graph =  graph.compile(checkpointer = checkpointer)
            logger.info('Graph Compiled Successfully.....')

            yield

            logger.info("Shutting down: Closing Pool...")
    except Exception as e:
        logger.info(f"Error in lifespan: {str(e)}")

app = FastAPI(
    title="CodePro - A Multi Agent Coding Chatbot",
    description="Multi Agent Coding Chatbot uses multiple use case agents",
    version="1.0.0",
    lifespan=lifespan
)

app.include_router(router)


@app.exception_handler(CustomAppException)
async def custom_app_exception_handler(request, exc: CustomAppException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "message": exc.message,
            "status_code": exc.status_code,
            "err_code": exc.err_code,
        },
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8001, reload=True)
