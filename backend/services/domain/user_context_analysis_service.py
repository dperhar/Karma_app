"""Service for analyzing user's Telegram activity to build personalized AI context."""

import json
import logging
import re
from collections import Counter
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from models.user.user import User
from services.base.base_service import BaseService
from services.external.gemini_service import GeminiService
from services.external.telethon_service import TelethonService
from services.repositories.user_repository import UserRepository
# Remove circular imports - these will be imported within functions
# from services.repositories.ai_profile_repository import AIProfileRepository
# from services.dependencies import container
# from models.ai.ai_profile import AnalysisStatus


class UserContextAnalysisService(BaseService):
    """Service for analyzing user's Telegram data to create personalized AI context."""

    def __init__(
        self,
        user_repository: UserRepository,
        telethon_service: TelethonService,
        gemini_service: GeminiService,
    ):
        super().__init__()
        self.user_repository = user_repository
        self.telethon_service = telethon_service
        self.gemini_service = gemini_service

    async def analyze_user_context(self, client: Any, user_id: str) -> Dict[str, Any]:
        """
        Analyze user's Telegram activity to build their vibe profile.
        
        Args:
            client: TelegramClient instance
            user_id: User ID
            
        Returns:
            Dict with analysis results and status
        """
        try:
            # Import here to avoid circular imports
            from services.repositories.ai_profile_repository import AIProfileRepository
            from services.dependencies import container
            from models.ai.ai_profile import AnalysisStatus
            
            ai_profile_repo = container.resolve(AIProfileRepository)
            
            # Get or create AI profile
            ai_profile = await ai_profile_repo.get_ai_profile_by_user(user_id)
            if not ai_profile:
                ai_profile = await ai_profile_repo.create_ai_profile(user_id=user_id)
            
            # Mark analysis as started
            await ai_profile_repo.update_ai_profile(
                ai_profile.id,
                analysis_status=AnalysisStatus.ANALYZING,
                ai_model_used="gemini-pro"
            )

            self.logger.info(f"Starting vibe profile analysis for user {user_id}")
            user = await self.user_repository.get_user(user_id)
            if not user:
                self.logger.error(f"User {user_id} not found for context analysis.")
                await ai_profile_repo.update_ai_profile(
                    ai_profile.id,
                    analysis_status=AnalysisStatus.FAILED,
                    last_error_message="User not found"
                )
                return {"status": "failed", "reason": "User not found"}

            # Step 1: Fetch user's own sent messages for style analysis
            user_sent_messages = await self._fetch_user_sent_messages_for_style(client, user_id)
            
            # Step 2: Fetch general content for topic/interest analysis
            general_content_data = await self._fetch_content_for_topic_analysis(client, user_id)

            if not user_sent_messages and not general_content_data.get("texts"):
                self.logger.warning(f"No sufficient data found for user {user_id} for analysis.")
                await ai_profile_repo.update_ai_profile(
                    ai_profile.id,
                    analysis_status=AnalysisStatus.FAILED,
                    last_error_message="Insufficient data for analysis"
                )
                return {"status": "failed", "reason": "Insufficient data for analysis"}

            # Step 3: Analyze communication style from user's sent messages
            style_analysis = await self._analyze_communication_style(user_sent_messages)
            
            # Step 4: Extract topics and interests from general content
            interests_analysis = await self._extract_interests_and_topics(
                general_content_data.get("texts", [])
            )
            
            # Step 5: Generate structured vibe profile
            vibe_profile = await self._generate_vibe_profile(style_analysis, interests_analysis, user_sent_messages)
            
            # Step 6: Update AI profile with vibe profile
            await ai_profile_repo.update_ai_profile(
                ai_profile.id,
                vibe_profile_json=vibe_profile,
                analysis_status=AnalysisStatus.COMPLETED,
                messages_analyzed_count=str(len(user_sent_messages)),
                last_analyzed_at=datetime.now()
            )

            self.logger.info(f"Vibe profile analysis completed for user {user_id}")
            
            return {
                "status": "completed",
                "vibe_profile": vibe_profile,
                "messages_analyzed": len(user_sent_messages)
            }

        except Exception as e:
            self.logger.error(f"Error analyzing user vibe profile: {e}", exc_info=True)
            try:
                if 'ai_profile' in locals() and ai_profile:
                    await ai_profile_repo.update_ai_profile(
                        ai_profile.id,
                        analysis_status=AnalysisStatus.FAILED,
                        last_error_message=str(e)
                    )
            except:
                pass
            return {"status": "failed", "reason": str(e)}

    async def _fetch_content_for_topic_analysis(self, client: Any, user_id: str) -> Dict[str, List[str]]:
        """
        Fetch general content from user's chats and channels for topic/interest analysis.
        (e.g., last 200 posts from their channels, last 500 messages from their group chats)
        Args:
            client: TelegramClient instance
            user_id: User ID
            
        Returns:
            Dict with extracted text content for analysis
        """
        # This is a simplified representation. Actual implementation would involve:
        # - Iterating through user's dialogs (chats and channels).
        # - For channels, fetching last N posts.
        # - For group chats, fetching last M messages.
        # - Aggregating text content.
        try:
            user = await self.user_repository.get_user(user_id)
            if not user or not user.telegram_id:
                return {"texts": []}

            all_texts: List[str] = []
            # Fetch posts from channels (limit to ~10 channels, 20 posts each = 200 posts)
            # Fetch messages from group chats (limit to ~5-10 active group chats, 50-100 messages each = 250-1000 messages)
            
            # Example: Fetching from a few dialogs (channels/supergroups)
            chats = await self.telethon_service.sync_chats(client, user_id, limit=50)
            fetched_channel_posts = 0
            fetched_chat_messages = 0

            for chat in chats:
                if chat.is_channel and fetched_channel_posts < 200:
                    # Fetch last 20 posts from this channel
                    try:
                        channel_entity = await client.get_entity(chat.id)
                        async for message in client.iter_messages(channel_entity, limit=20):
                            if message.text:
                                all_texts.append(message.text)
                                fetched_channel_posts += 1
                            if fetched_channel_posts >= 200:
                                break
                    except Exception as e:
                        self.logger.error(f"Error fetching channel posts: {e}")
                        continue
                elif chat.is_group and fetched_chat_messages < 500:
                    # Fetch last 50 messages from this group
                    try:
                        group_entity = await client.get_entity(chat.id)
                        async for message in client.iter_messages(group_entity, limit=50):
                            if message.text:
                                all_texts.append(message.text)
                                fetched_chat_messages += 1
                            if fetched_chat_messages >= 500:
                                break
                    except Exception as e:
                        self.logger.error(f"Error fetching group messages: {e}")
                        continue
                
                if fetched_channel_posts >= 200 and fetched_chat_messages >= 500:
                    break

            self.logger.info(f"Fetched {len(all_texts)} texts for topic/interest analysis for user {user_id}")
            return {"texts": all_texts}

        except Exception as e:
            self.logger.error(f"Error fetching content for topic analysis (user {user_id}): {e}", exc_info=True)
            return {"texts": []}

    async def _fetch_user_sent_messages_for_style(self, client: Any, user_id: str) -> List[Dict]:
        """
        Fetch user's *own* sent messages from DMs, group chats, and channel comments for style analysis.
        Limit to a reasonable number (e.g., last 500-1000 messages).
        """
        # This is a placeholder. Actual implementation would be complex:
        # - Iterate through all user's dialogs.
        # - For DMs, fetch messages sent by the user.
        # - For group chats, fetch messages sent by the user.
        # - For channels, try to fetch comments made by the user (if API allows).
        # - Collect up to N recent messages.
        user_messages: List[Dict] = []
        try:
            user = await self.user_repository.get_user(user_id)
            if not user or not user.telegram_id:
                return []

            # Example: Iterate dialogs and fetch messages if sender is the user
            chats = await self.telethon_service.sync_chats(client, user_id, limit=50)
            
            for chat in chats:
                try:
                    if chat.is_user or chat.is_group:  # DMs and group chats
                        # Fetch messages sent by the user from this chat
                        chat_messages = await self.telethon_service.sync_chat_messages(
                            client, chat.telegram_id, limit=100
                        )
                        
                        # Filter messages sent by the user
                        for message in chat_messages:
                            if message.get("sender_telegram_id") == user.telegram_id and message.get("text"):
                                user_messages.append({"text": message.get("text"), "date": message.get("date")})
                            if len(user_messages) >= 500:  # Overall limit for style analysis
                                break
                        
                        if len(user_messages) >= 500:
                            break
                except Exception as e:
                    self.logger.error(f"Error fetching user messages from chat {chat.telegram_id}: {e}")
                    continue
                    
            self.logger.info(f"Fetched {len(user_messages)} sent messages for style analysis for user {user_id}")
        except Exception as e:
            self.logger.error(f"Error fetching user sent messages for style analysis (user {user_id}): {e}", exc_info=True)
        return user_messages[:500]  # Ensure limit

    async def _analyze_communication_style(self, messages: List[Dict]) -> Dict[str, Any]:
        """
        Analyze user's communication style from their messages.
        This will involve detailed analysis based on the V categories provided in User Task.
        
        Args:
            messages: List of user's messages (dictionaries with "text" and "date" keys)
            
        Returns:
            Dict with style analysis metrics
        """
        if not messages:
            return self._get_default_style_analysis()

        texts = [msg.get("text", "") for msg in messages if msg.get("text")]
        if not texts:
            return self._get_default_style_analysis()

        # Placeholder for detailed V-category analysis.
        # Each of these would be a complex function.
        analysis = {
            "lexical_parameters": self._analyze_lexical_params(texts),
            "syntactic_parameters": self._analyze_syntactic_params(texts),
            "punctuation_and_orthography": self._analyze_punctuation_orthography(texts),
            "stylistic_and_semantic_parameters": self._analyze_stylistic_semantic_params(texts),
            "digital_communication_parameters": self._analyze_digital_comm_params(texts),
            # Simplified analysis from previous implementation for now
            "emoji_usage": self._analyze_emoji_usage(texts),
            "punctuation_patterns": self._analyze_punctuation(texts),
            "sentence_structure": self._analyze_sentence_structure(texts),
            "tone_indicators": self._analyze_tone_indicators(texts),
            "message_length": self._analyze_message_length(texts),
            "slang_and_informal": self._analyze_informal_language(texts)
        }
        
        return analysis

    # Placeholder methods for detailed V-category analysis
    def _analyze_lexical_params(self, texts: List[str]) -> Dict[str, Any]:
        # I. Лексические параметры (Словарный запас и выбор слов)
        # - Частотный словарь, Уникальный/редкий словарь, Предпочтения в синонимах,
        # - Специфическая лексика (жаргонизмы, профессионализмы, архаизмы, неологизмы),
        # - Слова-паразиты, Оценочная лексика, Заимствования, Степень формальности.
        # This would involve NLP libraries, frequency analysis, POS tagging, etc.
        return {"status": "placeholder", "comment": "Lexical analysis not fully implemented"}

    def _analyze_syntactic_params(self, texts: List[str]) -> Dict[str, Any]:
        # II. Синтаксические параметры (Структура предложений и фраз)
        # - Средняя длина предложения, Типы предложений (простые/сложные, типы сложных),
        # - Вопросительные/восклицательные/повествовательные, Порядок слов, Залог,
        # - Эллиптические конструкции, Причастные/деепричастные обороты, Способы связи, Риторические фигуры.
        return {"status": "placeholder", "comment": "Syntactic analysis not fully implemented"}

    def _analyze_punctuation_orthography(self, texts: List[str]) -> Dict[str, Any]:
        # III. Пунктуационные и орфографические параметры
        # - Характерные ошибки (орфографические, пунктуационные), Использование тире/дефиса,
        # - Предпочтение кавычек, Специфические знаки (многоточия, !!!, ???, скобки),
        # - Написание отдельных слов ("что то" vs "что-то").
        # This would involve spell checkers, punctuation rules analysis.
        return {"status": "placeholder", "comment": "Punctuation/Orthography analysis not fully implemented"}

    def _analyze_stylistic_semantic_params(self, texts: List[str]) -> Dict[str, Any]:
        # IV. Стилистические и семантические параметры
        # - Общая тональность, Тропы и фигуры речи (метафоры, сравнения, ирония),
        # - Логика изложения, Степень экспрессивности, Способы аргументации,
        # - Предпочитаемые темы, Степень персонализации.
        # This would involve sentiment analysis, topic modeling, rhetorical analysis.
        return {"status": "placeholder", "comment": "Stylistic/Semantic analysis not fully implemented"}

    def _analyze_digital_comm_params(self, texts: List[str]) -> Dict[str, Any]:
        # V. Параметры, специфичные для цифровой коммуникации
        # - Эмодзи/смайлики (частота, типы, расположение), CAPS LOCK, Сокращения,
        # - Форматирование (абзацы, пустые строки), Отсутствие знаков препинания в конце,
        # - Скорость ответа (косвенно), Оформление ссылок, Стикеры/GIF (не из текста),
        # - Способ исправления опечаток, Хештеги, Приветствия/прощания, Обращения, Псевдографика, Мемы.
        # Some of these require more than just text (e.g., stickers, GIFs, edit history).
        return {
            "status": "placeholder", 
            "comment": "Digital communication parameters analysis not fully implemented",
            "emoji_usage": self._analyze_emoji_usage(texts)  # Example, already partially done
        }

    def _analyze_emoji_usage(self, texts: List[str]) -> Dict[str, Any]:
        """Analyze emoji usage patterns."""
        emoji_pattern = re.compile(
            r'[\U0001F600-\U0001F64F]|'  # emoticons
            r'[\U0001F300-\U0001F5FF]|'  # symbols & pictographs
            r'[\U0001F680-\U0001F6FF]|'  # transport & map
            r'[\U0001F1E0-\U0001F1FF]'   # flags
        )
        
        total_emojis = 0
        emoji_types = Counter()
        
        for text in texts:
            emojis = emoji_pattern.findall(text)
            total_emojis += len(emojis)
            emoji_types.update(emojis)
        
        emoji_frequency = total_emojis / len(texts) if texts else 0
        
        return {
            "frequency": emoji_frequency,
            "total_count": total_emojis,
            "variety": len(emoji_types),
            "most_common": emoji_types.most_common(5)
        }

    def _analyze_punctuation(self, texts: List[str]) -> Dict[str, Any]:
        """Analyze punctuation usage patterns."""
        punctuation_chars = "!?.,;:"
        punct_counts = Counter()
        
        for text in texts:
            for char in punctuation_chars:
                punct_counts[char] += text.count(char)
        
        total_chars = sum(len(text) for text in texts)
        
        return {
            "exclamation_frequency": punct_counts["!"] / len(texts) if texts else 0,
            "question_frequency": punct_counts["?"] / len(texts) if texts else 0,
            "ellipsis_usage": sum(text.count("...") for text in texts) / len(texts) if texts else 0,
            "multiple_punctuation": sum(text.count("!!") + text.count("??") for text in texts) / len(texts) if texts else 0
        }

    def _analyze_sentence_structure(self, texts: List[str]) -> Dict[str, Any]:
        """Analyze sentence structure patterns."""
        total_sentences = 0
        total_words = 0
        
        for text in texts:
            sentences = re.split(r'[.!?]+', text)
            sentences = [s.strip() for s in sentences if s.strip()]
            total_sentences += len(sentences)
            
            words = text.split()
            total_words += len(words)
        
        avg_words_per_sentence = total_words / total_sentences if total_sentences > 0 else 0
        avg_sentence_per_message = total_sentences / len(texts) if texts else 0
        
        return {
            "avg_words_per_sentence": avg_words_per_sentence,
            "avg_sentences_per_message": avg_sentence_per_message,
            "total_sentences": total_sentences,
            "total_words": total_words
        }

    def _analyze_tone_indicators(self, texts: List[str]) -> Dict[str, Any]:
        """Analyze tone and sentiment indicators."""
        positive_words = {"great", "good", "awesome", "amazing", "love", "like", "happy", "excited"}
        negative_words = {"bad", "terrible", "hate", "dislike", "sad", "angry", "frustrated"}
        
        positive_count = 0
        negative_count = 0
        caps_usage = 0
        
        for text in texts:
            text_lower = text.lower()
            words = text_lower.split()
            
            positive_count += sum(1 for word in words if word in positive_words)
            negative_count += sum(1 for word in words if word in negative_words)
            caps_usage += sum(1 for char in text if char.isupper())
        
        return {
            "positive_sentiment_indicators": positive_count / len(texts) if texts else 0,
            "negative_sentiment_indicators": negative_count / len(texts) if texts else 0,
            "caps_usage_frequency": caps_usage / sum(len(text) for text in texts) if texts else 0
        }

    def _analyze_message_length(self, texts: List[str]) -> Dict[str, Any]:
        """Analyze message length patterns."""
        lengths = [len(text) for text in texts]
        
        if not lengths:
            return {"avg_length": 0, "median_length": 0, "max_length": 0}
        
        avg_length = sum(lengths) / len(lengths)
        sorted_lengths = sorted(lengths)
        median_length = sorted_lengths[len(sorted_lengths) // 2]
        
        return {
            "avg_length": avg_length,
            "median_length": median_length,
            "max_length": max(lengths),
            "short_messages_ratio": sum(1 for l in lengths if l < 50) / len(lengths)
        }

    def _analyze_informal_language(self, texts: List[str]) -> Dict[str, Any]:
        """Analyze informal language and slang usage."""
        informal_patterns = {
            "contractions": [r"don't", r"can't", r"won't", r"it's", r"I'm", r"you're"],
            "internet_slang": [r"\blol\b", r"\bomg\b", r"\bbrb\b", r"\bttyl\b", r"\bbtw\b"],
            "repeated_chars": r'(.)\1{2,}',  # like "yesss" or "nooo"
        }
        
        contraction_count = 0
        slang_count = 0
        repeated_chars_count = 0
        
        for text in texts:
            text_lower = text.lower()
            
            # Count contractions
            for pattern in informal_patterns["contractions"]:
                contraction_count += len(re.findall(pattern, text_lower))
            
            # Count internet slang
            for pattern in informal_patterns["internet_slang"]:
                slang_count += len(re.findall(pattern, text_lower))
            
            # Count repeated characters
            repeated_chars_count += len(re.findall(informal_patterns["repeated_chars"], text_lower))
        
        return {
            "contractions_frequency": contraction_count / len(texts) if texts else 0,
            "slang_frequency": slang_count / len(texts) if texts else 0,
            "repeated_chars_frequency": repeated_chars_count / len(texts) if texts else 0
        }

    async def _extract_interests_and_topics(self, content_texts: List[str]) -> Dict[str, Any]:
        """
        Extract user's interests and topics from their content (channel posts, general chat messages).
        
        Args:
            content_texts: List of texts from channels/chats user engages with.
            
        Returns:
            Dict with extracted interests and topics
        """
        if not content_texts:
            return {"interests": [], "topics": [], "keywords": []}

        # Simple keyword extraction (can be enhanced with NLP)
        keywords = self._extract_keywords(content_texts)
        
        # Topic categorization (can be enhanced with ML or LLM)
        topics = self._categorize_topics(keywords, content_texts)
        
        # Interest extraction (can be enhanced with LLM)
        interests = self._extract_interests(keywords, topics)
        
        # Use LLM to refine interests/topics if available
        if self.gemini_service:
            try:
                combined_text_sample = " ".join(content_texts[:20])  # Sample of content
                prompt = f"""
                Analyze the following text samples to identify key interests and topics for a user.
                Provide a list of up to 15 distinct interests/topics.
                Text samples: "{combined_text_sample[:2000]}"
                Interests/Topics (comma-separated list):
                """
                response = await self.gemini_service.generate_content(prompt)
                if response and response.get('content'):
                    llm_interests = [i.strip() for i in response.get('content').split(',') if i.strip()]
                    # Combine with rule-based and deduplicate
                    interests = list(dict.fromkeys(interests + llm_interests))
            except Exception as e:
                self.logger.error(f"LLM refinement of interests failed: {e}")

        return {
            "interests": interests[:20],  # Top 20 interests
            "topics": topics,
            "keywords": keywords[:50]  # Top 50 keywords
        }

    def _extract_keywords(self, texts: List[str]) -> List[str]:
        """Extract important keywords from texts."""
        # Combine all texts
        combined_text = " ".join(texts).lower()
        
        # Remove common stop words
        stop_words = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by",
            "is", "are", "was", "were", "be", "been", "being", "have", "has", "had", "do", "does", "did",
            "will", "would", "could", "should", "may", "might", "can", "must", "i", "you", "he", "she",
            "it", "we", "they", "me", "him", "her", "us", "them", "this", "that", "these", "those"
        }
        
        # Extract words
        words = re.findall(r'\b[a-zA-Z]{3,}\b', combined_text)
        words = [word for word in words if word not in stop_words]
        
        # Count frequency
        word_counts = Counter(words)
        
        # Return most common words
        return [word for word, count in word_counts.most_common(100) if count > 1]

    def _categorize_topics(self, keywords: List[str], texts: List[str]) -> List[str]:
        """Categorize content into topic areas."""
        topic_keywords = {
            "technology": ["tech", "ai", "software", "programming", "code", "development", "app", "digital", "crypto", "blockchain"],
            "business": ["business", "startup", "company", "market", "sales", "finance", "investment", "entrepreneur"],
            "social": ["people", "community", "social", "friends", "family", "relationship", "network"],
            "entertainment": ["movie", "music", "game", "sport", "entertainment", "fun", "video", "show"],
            "science": ["science", "research", "study", "data", "analysis", "experiment", "discovery"],
            "politics": ["politics", "government", "policy", "election", "vote", "political"],
            "health": ["health", "medical", "doctor", "medicine", "fitness", "exercise", "wellness"],
            "education": ["education", "learning", "school", "university", "course", "study", "knowledge"]
        }
        
        user_topics = []
        
        for topic, topic_words in topic_keywords.items():
            # Check if user has keywords related to this topic
            topic_score = sum(1 for keyword in keywords if keyword in topic_words)
            
            # Also check direct mentions in texts
            combined_text = " ".join(texts).lower()
            mention_score = sum(combined_text.count(word) for word in topic_words)
            
            if topic_score > 0 or mention_score > 2:
                user_topics.append(topic)
        
        return user_topics

    def _extract_interests(self, keywords: List[str], topics: List[str]) -> List[str]:
        """Extract specific interests from keywords and topics."""
        interests = []
        
        # Add topics as interests
        interests.extend(topics)
        
        # Add specific keywords that might be interests
        interest_keywords = [
            keyword for keyword in keywords[:30]
            if len(keyword) > 3 and keyword not in {"that", "this", "with", "from", "they", "have", "been"}
        ]
        
        interests.extend(interest_keywords)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_interests = []
        for interest in interests:
            if interest not in seen:
                seen.add(interest)
                unique_interests.append(interest)
        
        return unique_interests

    async def _generate_vibe_profile(
        self, 
        style_analysis: Dict[str, Any], 
        interests_analysis: Dict[str, Any],
        user_messages: List[Dict]
    ) -> Dict[str, Any]:
        """Generate structured vibe profile matching the vision document structure."""
        try:
            # Extract style characteristics
            emoji_freq = style_analysis.get("emoji_usage", {}).get("frequency", 0)
            avg_length = style_analysis.get("message_length", {}).get("avg_length", 0)
            informal_score = style_analysis.get("slang_and_informal", {})
            contraction_freq = informal_score.get("contractions_frequency", 0)
            excl_freq = style_analysis.get("punctuation_patterns", {}).get("exclamation_frequency", 0)
            
            # Determine tone
            tone = "formal"
            if contraction_freq > 0.5:
                tone = "casual"
            elif excl_freq > 0.5:
                tone = "enthusiastic"
            elif style_analysis.get("tone_indicators", {}).get("positive_sentiment_indicators", 0) > 0.3:
                tone = "friendly"
                
            # Determine verbosity
            verbosity = "brief"
            if avg_length > 200:
                verbosity = "verbose"
            elif avg_length > 100:
                verbosity = "moderate"
                
            # Determine emoji usage
            emoji_usage = "none"
            if emoji_freq > 1.5:
                emoji_usage = "heavy"
            elif emoji_freq > 0.5:
                emoji_usage = "light"
                
            # Extract common phrases (simplified - would need more sophisticated NLP)
            common_phrases = await self._extract_common_phrases(user_messages)
            
            # Build vibe profile
            vibe_profile = {
                "tone": tone,
                "verbosity": verbosity,
                "emoji_usage": emoji_usage,
                "common_phrases": common_phrases[:10],  # Limit to top 10
                "topics_of_interest": interests_analysis.get("topics", [])[:10],
                "communication_patterns": {
                    "avg_message_length": avg_length,
                    "contraction_frequency": contraction_freq,
                    "emoji_frequency": emoji_freq,
                    "exclamation_frequency": excl_freq,
                    "formality_score": 1.0 - contraction_freq  # Inverse relationship
                }
            }
            
            return vibe_profile
            
        except Exception as e:
            self.logger.error(f"Error generating vibe profile: {e}", exc_info=True)
            # Return default vibe profile
            return {
                "tone": "neutral",
                "verbosity": "moderate", 
                "emoji_usage": "light",
                "common_phrases": [],
                "topics_of_interest": interests_analysis.get("topics", [])[:5],
                "communication_patterns": {
                    "avg_message_length": 50,
                    "contraction_frequency": 0.3,
                    "emoji_frequency": 0.2,
                    "exclamation_frequency": 0.1,
                    "formality_score": 0.7
                }
            }

    async def _extract_common_phrases(self, user_messages: List[Dict]) -> List[str]:
        """Extract common phrases and expressions from user messages."""
        try:
            if not user_messages:
                return []
                
            # Extract text from messages
            texts = [msg.get('text', '') for msg in user_messages if msg.get('text')]
            combined_text = ' '.join(texts).lower()
            
            # Simple phrase extraction (would be enhanced with proper NLP)
            import re
            from collections import Counter
            
            # Find repeated multi-word expressions
            phrases = []
            
            # Extract 2-4 word phrases
            for phrase_length in [2, 3, 4]:
                words = combined_text.split()
                for i in range(len(words) - phrase_length + 1):
                    phrase = ' '.join(words[i:i + phrase_length])
                    # Filter meaningful phrases
                    if (len(phrase) > 8 and 
                        not re.match(r'^(the|and|but|or|so|if|when|where|what|how)', phrase) and
                        not re.match(r'.*[0-9].*', phrase)):
                        phrases.append(phrase)
            
            # Count and return most common
            phrase_counts = Counter(phrases)
            common_phrases = [phrase for phrase, count in phrase_counts.most_common(20) if count > 1]
            
            return common_phrases
            
        except Exception as e:
            self.logger.error(f"Error extracting common phrases: {e}", exc_info=True)
            return []

    def _get_default_style_analysis(self) -> Dict[str, Any]:
        """Return default style analysis when no data is available."""
        return {
            "emoji_usage": {"frequency": 0, "total_count": 0, "variety": 0, "most_common": []},
            "punctuation_patterns": {"exclamation_frequency": 0, "question_frequency": 0, "ellipsis_usage": 0, "multiple_punctuation": 0},
            "sentence_structure": {"avg_words_per_sentence": 10, "avg_sentences_per_message": 1, "total_sentences": 0, "total_words": 0},
            "tone_indicators": {"positive_sentiment_indicators": 0, "negative_sentiment_indicators": 0, "caps_usage_frequency": 0},
            "message_length": {"avg_length": 50, "median_length": 40, "max_length": 100, "short_messages_ratio": 0.5},
            "slang_and_informal": {"contractions_frequency": 0, "slang_frequency": 0, "repeated_chars_frequency": 0}
        } 