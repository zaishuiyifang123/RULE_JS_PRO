from pydantic import BaseModel, Field


class HistoryMessage(BaseModel):
    role: str = Field(..., description="消息角色")
    content: str = Field(..., description="消息内容")


class ChatIntentRequest(BaseModel):
    session_id: str | None = Field(default=None, description="会话ID，首次可为空")
    message: str = Field(..., min_length=1, description="当前用户问题")
    history: list[HistoryMessage] | None = Field(default=None, description="可选历史消息")
    model_name: str | None = Field(default=None, description="可选模型名覆盖")


class ChatIntentData(BaseModel):
    session_id: str = Field(..., description="会话ID")
    intent: str = Field(..., description="意图：chat/business_query")
    is_followup: bool = Field(..., description="是否追问")
    confidence: float = Field(..., ge=0.0, le=1.0, description="意图置信度")
    merged_query: str = Field(..., description="合并后的查询文本")
    rewritten_query: str = Field(..., description="最终查询文本（当前等于merged_query）")
    threshold: float = Field(..., description="意图阈值")


class ChatIntentResponse(BaseModel):
    code: int = 0
    message: str = "ok"
    data: ChatIntentData

