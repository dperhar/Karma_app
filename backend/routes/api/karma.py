from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Any
from pydantic import BaseModel
from datetime import datetime

from services.external.gemini_service import GeminiService
from services.external.mock_service import MockService
from services.action_logger import ActionLogger, ActionType
from routes.dependencies import get_current_user

router = APIRouter(prefix="/api/karma", tags=["karma"])

# Pydantic модели
class Post(BaseModel):
    id: int
    channel_id: int
    content: str
    date: datetime
    reactions: Dict[str, int]

class Channel(BaseModel):
    id: int
    name: str
    type: str

class UserContext(BaseModel):
    interests: List[str]
    writing_style: str
    reaction_history: Dict[str, int]

class CommentRequest(BaseModel):
    post_id: int
    user_context: UserContext

class CommentResponse(BaseModel):
    comment: str
    generated_at: datetime

# Инициализация сервисов
gemini_service = GeminiService()
mock_service = MockService()
action_logger = ActionLogger()

@router.get("/channels", response_model=List[Channel])
async def get_channels(current_user: Dict = Depends(get_current_user)):
    """Получить список каналов"""
    action_logger.log_action(
        ActionType.VIEW_POST,
        current_user["id"],
        {"action": "get_channels"}
    )
    return await mock_service.get_channels()

@router.get("/posts/{channel_id}", response_model=List[Post])
async def get_posts(
    channel_id: int,
    current_user: Dict = Depends(get_current_user)
):
    """Получить посты канала"""
    action_logger.log_action(
        ActionType.VIEW_POST,
        current_user["id"],
        {"channel_id": channel_id}
    )
    return await mock_service.get_posts(channel_id)

@router.post("/generate-comment", response_model=CommentResponse)
async def generate_comment(
    request: CommentRequest,
    current_user: Dict = Depends(get_current_user)
):
    """Сгенерировать комментарий к посту"""
    try:
        # Получаем пост
        posts = await mock_service.get_posts()
        post = next((p for p in posts if p["id"] == request.post_id), None)
        if not post:
            raise HTTPException(
                status_code=404,
                detail=f"Post with id {request.post_id} not found"
            )
            
        # Генерируем комментарий
        comment = await gemini_service.generate_comment(
            post_content=post["content"],
            user_context=request.user_context.dict(),
            channel_context={"name": "Tech Channel"}  # TODO: Получать из БД
        )
        
        action_logger.log_action(
            ActionType.GENERATE_COMMENT,
            current_user["id"],
            {
                "post_id": request.post_id,
                "comment_length": len(comment)
            }
        )
        
        return CommentResponse(
            comment=comment,
            generated_at=datetime.now()
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating comment: {str(e)}"
        )

@router.get("/user-context", response_model=UserContext)
async def get_user_context(current_user: Dict = Depends(get_current_user)):
    """Получить контекст пользователя"""
    return await mock_service.get_user_context()

@router.get("/user-actions")
async def get_user_actions(
    current_user: Dict = Depends(get_current_user),
    action_type: str = None,
    start_date: datetime = None,
    end_date: datetime = None
):
    """Получить историю действий пользователя"""
    return action_logger.get_user_actions(
        user_id=current_user["id"],
        action_type=ActionType(action_type) if action_type else None,
        start_date=start_date,
        end_date=end_date
    ) 