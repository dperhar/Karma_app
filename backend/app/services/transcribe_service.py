import logging
import os
import tempfile

import groq
from fastapi import HTTPException, UploadFile

from app.core.config import settings # GROQ_API_KEY
from app.services.base_service import BaseService

logger = logging.getLogger(__name__)


class TranscribeService(BaseService):
    """Service for transcribing audio files using Groq API."""

    def __init__(self):
        """Initialize TranscribeService."""
        super().__init__()

    async def transcribe_audio(
        self,
        file: UploadFile,
    ) -> dict:
        """Transcribe audio file using Groq API."""
        try:
            # Save the uploaded file temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix=".m4a") as temp_file:
                content = await file.read()
                temp_file.write(content)
                temp_file_path = temp_file.name

            try:
                # Initialize Groq client with API key from environment
                groq_client = groq.Groq(api_key=GROQ_API_KEY)

                # Transcribe the audio - synchronous call
                with open(temp_file_path, "rb") as audio_file:
                    transcription = groq_client.audio.transcriptions.create(
                        file=audio_file,
                        model="whisper-large-v3-turbo",
                        response_format="verbose_json",
                    )

                # Extract text from transcription response
                if hasattr(transcription, "text"):
                    return transcription.text
                elif isinstance(transcription, dict) and "text" in transcription:
                    return transcription["text"]
                else:
                    raise HTTPException(
                        status_code=500,
                        detail="Unexpected transcription response format",
                    )

            finally:
                # Clean up the temporary file
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)

        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Transcription error: {e!s}"
            ) from e
