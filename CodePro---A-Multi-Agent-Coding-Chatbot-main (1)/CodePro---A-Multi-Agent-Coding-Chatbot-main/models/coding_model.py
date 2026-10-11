from pydantic import BaseModel,Field
from typing import  Optional,TypedDict,Literal


class CodeRequest(BaseModel):
    user_id:str
    user_query:str 
    session_id:Optional[str] = None


class APIResponse(BaseModel):
    message:str 
    status_code:int
    data:dict | str

class ResponseModel(BaseModel):
    """
    The structured output schema for the Research Agent.
    
    This model ensures that the agent from the qualitative analysis and findings (research context).
    """
    research_context: Optional[str] = Field(
        default=None,
        description=(
            "A comprehensive summary of the research findings. This should include "
            "key insights, explanations of concepts, and synthesized information "
            "retrieved by the tools."
        )
    )



class ReviewResponseModel(BaseModel):
    """
    Results of a PEP8 code format analysis. This model captures the 
    outcome of the 'format_code' tool and categorizes the code's 
    adherence to Python style guidelines.
    """

    error: Optional[str] = Field(
        default=None,
        description=(
            "Contains the traceback or error message if the tool failed to run "
            "(e.g., due to a SyntaxError). Should be null if the analysis finished."
        )
    )

    code: Optional[str] = Field(
        default=None,
        description=(
            "The specific PEP8 violation code (e.g., 'E401', 'W293') or a summary "
            "of the rule broken. Should be null if the status is 'passed'."
        )
    )

    review_status: Optional[Literal["passed", "failed"]] = Field(
        default=None,
        description=(
            "The final result of the PEP8 check. Use 'passed' if the code fully "
            "conforms to PEP8 or was successfully auto-formatted. Use 'failed' "
            "if the code contains unresolvable style issues or syntax errors."
        )
    )

class CommonState(TypedDict):
    message:str
    type:str 
    code:str
    error:str
    issues_detected:str
    review_status:str 
    research_context:str
    retry_attempts:str
    current_node:str


