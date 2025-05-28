"""API routes for audio transcription."""

from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel

from models.base.schemas import APIResponse
from models.user.schemas import UserTelegramResponse
from routes.dependencies import get_current_user, logger
from services.dependencies import get_transcribe_service
from services.external.transcribe_service import TranscribeService

router = APIRouter(prefix="/transcribe", tags=["transcribe"])


class TranscribeResponse(BaseModel):
    """Schema for transcribe response."""

    text: str
    """Transcribed text from the audio file"""


@router.post("", response_model=APIResponse[TranscribeResponse])
async def transcribe_audio(
    file: UploadFile = File(...),
    current_user: Optional[UserTelegramResponse] = Depends(get_current_user),
    transcribe_service: TranscribeService = Depends(get_transcribe_service),
) -> APIResponse[TranscribeResponse]:
    """Transcribe audio file to text."""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )

    if not file.content_type or not file.content_type.startswith("audio/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be an audio file",
        )

    try:
        transcribed_text = await transcribe_service.transcribe_audio(file)
        return APIResponse(
            success=True,
            data=TranscribeResponse(text=transcribed_text),
            message="Audio transcribed successfully",
        )
    except Exception as e:
        logger.error(f"Error transcribing audio: {e!s}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error transcribing audio",
        ) from e
