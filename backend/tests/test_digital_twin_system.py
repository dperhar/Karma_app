#!/usr/bin/env python3
"""Test script for the complete digital twin system implementation."""

import asyncio
import json
import logging
from datetime import datetime, timedelta

from app.core.dependencies import container
from app.services.user_context_analysis_service import UserContextAnalysisService
from app.services.karma_service import KarmaService
from app.repositories.user_repository import UserRepository

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_digital_twin_system():
    """Test the complete digital twin system."""
    logger.info("Starting digital twin system test...")
    
    try:
        # Get services
        user_repository = container.resolve(UserRepository)
        user_context_service = container.resolve(UserContextAnalysisService)
        karma_service = container.resolve(KarmaService)
        
        # Test user ID
        test_user_id = "test-user-123"
        
        # 1. Check if test user exists
        user = await user_repository.get_user(test_user_id)
        if not user:
            logger.error(f"Test user {test_user_id} not found!")
            return False
        
        logger.info(f"Found test user: {user.username} ({user.id})")
        
        # 2. Test context analysis (mock without actual Telegram client)
        logger.info("Testing user context analysis...")
        
        # Mock analysis data
        mock_analysis_result = {
            "status": "completed",
            "style_analysis": {
                "emoji_usage": {"frequency": 1.2, "total_count": 24, "variety": 8},
                "message_length": {"avg_length": 85, "median_length": 60},
                "slang_and_informal": {"contractions_frequency": 0.8, "slang_frequency": 0.2}
            },
            "interests_analysis": {
                "interests": ["technology", "artificial intelligence", "programming", "startups", "machine learning"],
                "topics": ["technology", "business", "science"],
                "keywords": ["ai", "python", "coding", "startup", "innovation", "tech", "development"]
            }
        }
        
        # Update user with mock context analysis results
        style_description = "Communication style is casual and conversational, occasionally uses emojis, concise and to-the-point."
        system_prompt = "You are knowledgeable about technology, artificial intelligence, programming and actively follow developments in these areas."
        
        await user_repository.update_user(
            test_user_id,
            persona_style_description=style_description,
            persona_interests_json=json.dumps(mock_analysis_result["interests_analysis"]["interests"]),
            user_system_prompt=system_prompt,
            context_analysis_status="COMPLETED",
            last_context_analysis_at=datetime.utcnow()
        )
        
        logger.info("✅ User context analysis completed successfully")
        
        # 3. Test karma service comment generation
        logger.info("Testing AI comment generation with user's digital twin...")
        
        # Mock post data
        mock_post_data = {
            "text": "OpenAI just released GPT-5 with revolutionary multimodal capabilities and 10x performance improvements!",
            "channel": {"title": "AI News Channel"},
            "telegram_id": 12345,
            "date": datetime.now()
        }
        
        # Generate comment using user's digital twin
        draft_comment = await karma_service.generate_draft_comment(
            original_message_id="mock-message-123",
            user_id=test_user_id,
            post_data=mock_post_data
        )
        
        if draft_comment:
            logger.info("✅ AI comment generation successful!")
            logger.info(f"Generated comment: {draft_comment.draft_text}")
            logger.info(f"Persona used: {draft_comment.persona_name}")
            logger.info(f"AI model: {draft_comment.ai_model_used}")
        else:
            logger.error("❌ AI comment generation failed")
            return False
        
        # 4. Verify user data was updated correctly
        updated_user = await user_repository.get_user(test_user_id)
        
        logger.info("Checking updated user data...")
        logger.info(f"Context analysis status: {updated_user.context_analysis_status}")
        logger.info(f"Last analysis at: {updated_user.last_context_analysis_at}")
        logger.info(f"System prompt: {updated_user.user_system_prompt[:100]}...")
        logger.info(f"Style description: {updated_user.persona_style_description}")
        
        if updated_user.persona_interests_json:
            interests = json.loads(updated_user.persona_interests_json)
            logger.info(f"User interests: {interests}")
        
        # 5. Test post relevance filtering
        logger.info("Testing post relevance filtering...")
        
        # Relevant post
        relevant_post = {
            "text": "New breakthrough in machine learning algorithms for natural language processing",
            "channel": {"title": "Tech News"}
        }
        
        is_relevant = karma_service._is_post_relevant(relevant_post, updated_user)
        logger.info(f"✅ Relevant post detection: {is_relevant}")
        
        # Irrelevant post
        irrelevant_post = {
            "text": "Latest fashion trends for summer 2024",
            "channel": {"title": "Fashion Magazine"}
        }
        
        is_irrelevant = karma_service._is_post_relevant(irrelevant_post, updated_user)
        logger.info(f"✅ Irrelevant post detection: {not is_irrelevant}")
        
        logger.info("🎉 Digital twin system test completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed with error: {e}", exc_info=True)
        return False


async def test_context_analysis_service():
    """Test the UserContextAnalysisService with mock data."""
    logger.info("Testing UserContextAnalysisService...")
    
    try:
        service = container.resolve(UserContextAnalysisService)
        
        # Test style analysis with mock data
        mock_messages = [
            {"text": "Hey! This is amazing 😍 Can't wait to try it out!!!"},
            {"text": "I'm really excited about this new tech. It's gonna be huge!"},
            {"text": "LOL that's so cool! 🚀 We should definitely look into this"},
            {"text": "Awesome work on the AI implementation. Very impressive stuff."},
            {"text": "OMG this is exactly what we needed! 💯"}
        ]
        
        style_analysis = await service._analyze_communication_style(mock_messages)
        logger.info("Style analysis results:")
        logger.info(f"  Emoji frequency: {style_analysis['emoji_usage']['frequency']:.2f}")
        logger.info(f"  Avg message length: {style_analysis['message_length']['avg_length']:.1f}")
        logger.info(f"  Contractions frequency: {style_analysis['slang_and_informal']['contractions_frequency']:.2f}")
        
        # Test interest extraction
        mock_content = [
            {"text": "Latest developments in artificial intelligence and machine learning are fascinating"},
            {"text": "Python programming best practices for data science applications"},
            {"text": "Startup funding trends in the tech industry this quarter"},
            {"text": "New breakthrough in neural network architectures for computer vision"}
        ]
        
        interests_analysis = await service._extract_interests_and_topics(mock_content)
        logger.info("Interest analysis results:")
        logger.info(f"  Detected topics: {interests_analysis['topics']}")
        logger.info(f"  Key interests: {interests_analysis['interests'][:10]}")
        
        logger.info("✅ UserContextAnalysisService test completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ UserContextAnalysisService test failed: {e}", exc_info=True)
        return False


async def main():
    """Run all tests."""
    logger.info("=" * 60)
    logger.info("DIGITAL TWIN SYSTEM COMPREHENSIVE TEST")
    logger.info("=" * 60)
    
    # Test 1: Context Analysis Service
    test1_result = await test_context_analysis_service()
    
    print("\n" + "=" * 60)
    
    # Test 2: Complete System
    test2_result = await test_digital_twin_system()
    
    print("\n" + "=" * 60)
    print("FINAL RESULTS:")
    print(f"Context Analysis Service: {'✅ PASS' if test1_result else '❌ FAIL'}")
    print(f"Complete Digital Twin System: {'✅ PASS' if test2_result else '❌ FAIL'}")
    print("=" * 60)
    
    if test1_result and test2_result:
        print("🎉 ALL TESTS PASSED! Digital twin system is working correctly!")
    else:
        print("❌ Some tests failed. Check the logs above for details.")


if __name__ == "__main__":
    asyncio.run(main()) 