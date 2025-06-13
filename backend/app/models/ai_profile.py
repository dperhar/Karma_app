"""AI Profile models for user vibe analysis."""

import enum
import logging
from uuid import uuid4
from datetime import datetime

from sqlalchemy import Column, String, JSON, DateTime, ForeignKey, Enum as SQLEnum, Text
from sqlalchemy.orm import relationship

from app.models.db_base import DBBase
from app.models.timestamp_mixin import TimestampMixin

logger = logging.getLogger(__name__)


class AnalysisStatus(str, enum.Enum):
    """Status of vibe profile analysis."""
    PENDING = "PENDING"
    ANALYZING = "ANALYZING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    OUTDATED = "OUTDATED"  # Needs re-analysis


class AIProfile(TimestampMixin, DBBase):
    """Model representing a user's AI-generated vibe profile."""

    __tablename__ = "ai_profiles"

    id = Column(String, primary_key=True, default=lambda: uuid4().hex)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, unique=True)

    # Persona fields moved from User model
    persona_name = Column(String, nullable=True, comment="User-defined or AI-suggested persona name")
    user_system_prompt = Column(Text, nullable=True, comment="AI system prompt derived from the user's topics/interests")
    
    # Vibe Profile JSON structure: 
    # {
    #   "tone": "casual/formal/sarcastic/etc",
    #   "verbosity": "brief/moderate/verbose",
    #   "emoji_usage": "none/light/heavy",
    #   "common_phrases": ["phrase1", "phrase2"],
    #   "topics_of_interest": ["tech", "crypto", "politics"],
    #   "communication_patterns": {...}
    # }
    vibe_profile_json = Column(JSON, nullable=True, comment="Structured vibe profile data")
    
    # Analysis metadata
    analysis_status = Column(SQLEnum(AnalysisStatus), default=AnalysisStatus.PENDING, nullable=False)
    last_analyzed_at = Column(DateTime, nullable=True, comment="When the analysis was last completed")
    messages_analyzed_count = Column(String, nullable=True, comment="Number of messages used for analysis")
    
    # AI model information
    ai_model_used = Column(String, nullable=True, comment="AI model used for analysis (e.g., 'gemini-pro')")
    analysis_version = Column(String, nullable=True, default="1.0", comment="Version of analysis algorithm")
    
    # Error tracking
    last_error_message = Column(String, nullable=True, comment="Last error message if analysis failed")
    retry_count = Column(String, nullable=True, default="0", comment="Number of analysis retries")
    
    # Relationships
    user = relationship("User")

    def mark_analysis_started(self, ai_model: str = None):
        """Mark analysis as started."""
        self.analysis_status = AnalysisStatus.ANALYZING
        self.ai_model_used = ai_model
        self.last_error_message = None

    def mark_analysis_completed(self, vibe_profile: dict, messages_count: int = 0):
        """Mark analysis as completed with results."""
        self.analysis_status = AnalysisStatus.COMPLETED
        self.vibe_profile_json = vibe_profile
        self.last_analyzed_at = datetime.utcnow()
        self.messages_analyzed_count = str(messages_count)
        self.last_error_message = None

    def mark_analysis_failed(self, error_message: str):
        """Mark analysis as failed with error message."""
        self.analysis_status = AnalysisStatus.FAILED
        self.last_error_message = error_message
        self.retry_count = str(int(self.retry_count or "0") + 1)

    def needs_analysis(self) -> bool:
        """Check if profile needs (re)analysis."""
        return self.analysis_status in [AnalysisStatus.PENDING, AnalysisStatus.FAILED, AnalysisStatus.OUTDATED]

    def get_topics_of_interest(self) -> list:
        """Extract topics of interest from vibe profile."""
        if not self.vibe_profile_json:
            return []
        return self.vibe_profile_json.get("topics_of_interest", []) 