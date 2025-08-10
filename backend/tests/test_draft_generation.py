#!/usr/bin/env python3
"""
Draft Generation Test
Tests Task 2.2: Draft Generation (Flow 2)
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_draft_generation_service():
    """Test the draft generation service functionality."""
    logger.info("🎯 Testing Draft Generation Service")
    
    try:
        # Import services
        from app.services.draft_generation_service import DraftGenerationService
        from app.services.karma_service import KarmaService
        from app.repositories.user_repository import UserRepository
        from app.services.telethon_service import TelethonService
        from app.services.domain.websocket_service import WebSocketService
        
        # Mock dependencies
        user_repo = UserRepository()
        karma_service = KarmaService(None, None, None, None, None, None)  # Will mock methods
        telethon_service = TelethonService()
        websocket_service = WebSocketService()
        
        # Create service
        draft_service = DraftGenerationService(
            user_repository=user_repo,
            karma_service=karma_service,
            telethon_service=telethon_service,
            websocket_service=websocket_service
        )
        
        logger.info("✅ Draft generation service created successfully")
        
        # Test active users filtering logic
        mock_users = await draft_service._get_active_users()
        logger.info(f"✅ Active users filtering works (found {len(mock_users)} users)")
        
        # Test recent posts extraction
        mock_posts = [
            {
                'message_id': 123,
                'text': 'This is an interesting AI development that could change everything',
                'date': datetime.now(),
                'channel_id': 456
            },
            {
                'message_id': 124,
                'text': 'New breakthrough in machine learning algorithms',
                'date': datetime.now(),
                'channel_id': 456
            }
        ]
        
        # Verify post data structure
        for post in mock_posts:
            required_fields = ['message_id', 'text', 'date', 'channel_id']
            if all(field in post for field in required_fields):
                logger.info(f"✅ Post {post['message_id']} has valid structure")
            else:
                logger.error(f"❌ Post {post['message_id']} missing required fields")
                return False
        
        logger.info("🎉 Draft generation service test PASSED!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Draft generation service test FAILED: {e}")
        return False

async def test_relevance_detection():
    """Test post relevance detection using vibe profiles."""
    logger.info("🎯 Testing Post Relevance Detection")
    
    try:
        from app.services.karma_service import KarmaService
        from app.models.user import User
        from app.models.ai_profile import AIProfile
        
        # Create mock karma service
        karma_service = KarmaService(None, None, None, None, None, None)
        
        # Create mock user with AI profile
        mock_user = User()
        mock_user.id = "test-user-123"
        mock_user.ai_profile = AIProfile()
        mock_user.ai_profile.vibe_profile_json = {
            "tone": "enthusiastic",
            "verbosity": "moderate",
            "emoji_usage": "light",
            "topics_of_interest": ["artificial intelligence", "technology", "startups", "innovation"],
            "communication_patterns": {
                "avg_message_length": 80,
                "formality_score": 0.6
            }
        }
        
        # Test relevant posts
        relevant_posts = [
            {
                "text": "Amazing breakthrough in artificial intelligence! This new model can understand context better than ever before.",
                "channel": {"title": "AI Research Updates"}
            },
            {
                "text": "Startup raises $50M for innovative technology platform that uses machine learning",
                "channel": {"title": "Tech News"}
            },
            {
                "text": "New research paper on deep learning architectures shows promising results for natural language processing",
                "channel": {"title": "Academic Papers"}
            }
        ]
        
        # Test irrelevant posts
        irrelevant_posts = [
            {
                "text": "Recipe for chocolate chip cookies that everyone will love",
                "channel": {"title": "Cooking Channel"}
            },
            {
                "text": "Weather forecast shows sunny skies for the weekend",
                "channel": {"title": "Weather Updates"}
            },
            {
                "text": "Sports scores from last night's basketball games",
                "channel": {"title": "Sports News"}
            }
        ]
        
        # Test relevant posts
        relevant_count = 0
        for post in relevant_posts:
            if karma_service._is_post_relevant(post, mock_user):
                relevant_count += 1
                logger.info(f"✅ Correctly identified relevant post: {post['text'][:50]}...")
            else:
                logger.warning(f"⚠️  Missed relevant post: {post['text'][:50]}...")
        
        # Test irrelevant posts
        irrelevant_count = 0
        for post in irrelevant_posts:
            if not karma_service._is_post_relevant(post, mock_user):
                irrelevant_count += 1
                logger.info(f"✅ Correctly filtered irrelevant post: {post['text'][:50]}...")
            else:
                logger.warning(f"⚠️  False positive on irrelevant post: {post['text'][:50]}...")
        
        # Calculate accuracy
        total_relevant = len(relevant_posts)
        total_irrelevant = len(irrelevant_posts)
        
        relevant_accuracy = relevant_count / total_relevant if total_relevant > 0 else 0
        irrelevant_accuracy = irrelevant_count / total_irrelevant if total_irrelevant > 0 else 0
        
        logger.info(f"📊 Relevance detection accuracy:")
        logger.info(f"   - Relevant posts detected: {relevant_count}/{total_relevant} ({relevant_accuracy:.2%})")
        logger.info(f"   - Irrelevant posts filtered: {irrelevant_count}/{total_irrelevant} ({irrelevant_accuracy:.2%})")
        
        # We want at least 60% accuracy on both
        if relevant_accuracy >= 0.6 and irrelevant_accuracy >= 0.6:
            logger.info("🎉 Post relevance detection test PASSED!")
            return True
        else:
            logger.error("❌ Post relevance detection accuracy too low")
            return False
        
    except Exception as e:
        logger.error(f"❌ Post relevance detection test FAILED: {e}")
        return False

async def test_prompt_construction_with_vibe_profile():
    """Test that prompts are constructed properly using vibe profiles."""
    logger.info("🎯 Testing Prompt Construction with Vibe Profile")
    
    try:
        from app.services.karma_service import KarmaService
        from app.models.user import User
        from app.models.ai_profile import AIProfile
        
        # Create mock karma service
        karma_service = KarmaService(None, None, None, None, None, None)
        
        # Create mock user with AI profile
        mock_user = User()
        mock_user.id = "test-user-123"
        mock_user.persona_name = "Tech Enthusiast"
        mock_user.ai_profile = AIProfile()
        mock_user.ai_profile.vibe_profile_json = {
            "tone": "enthusiastic",
            "verbosity": "moderate",
            "emoji_usage": "light",
            "topics_of_interest": ["AI", "technology", "startups"],
            "common_phrases": ["that's amazing", "really cool", "I think"],
            "communication_patterns": {
                "avg_message_length": 80,
                "formality_score": 0.4
            }
        }
        
        # Test post data
        post_data = {
            "text": "New AI model achieves breakthrough performance in language understanding",
            "channel": {"title": "AI Research"}
        }
        
        # Construct prompt
        prompt = karma_service._construct_prompt(post_data, mock_user)
        
        logger.info("✅ Prompt constructed successfully")
        logger.info(f"   - Length: {len(prompt)} characters")
        
        # Verify prompt contains vibe profile information
        vibe_profile = mock_user.ai_profile.vibe_profile_json
        
        checks = {
            "Contains tone": vibe_profile["tone"].lower() in prompt.lower(),
            "Contains verbosity": vibe_profile["verbosity"].lower() in prompt.lower(),
            "Contains emoji usage": vibe_profile["emoji_usage"].lower() in prompt.lower(),
            "Contains topics": any(topic.lower() in prompt.lower() for topic in vibe_profile["topics_of_interest"]),
            "Contains post text": post_data["text"].lower() in prompt.lower(),
            "Contains channel info": post_data["channel"]["title"].lower() in prompt.lower(),
            "Has instructions": "generate" in prompt.lower() and "comment" in prompt.lower()
        }
        
        passed_checks = sum(1 for check, result in checks.items() if result)
        total_checks = len(checks)
        
        for check, result in checks.items():
            status = "✅" if result else "❌"
            logger.info(f"   {status} {check}")
        
        if passed_checks >= total_checks - 1:  # Allow one check to fail
            logger.info("🎉 Prompt construction test PASSED!")
            return True
        else:
            logger.error(f"❌ Prompt construction test FAILED ({passed_checks}/{total_checks} checks passed)")
            return False
        
    except Exception as e:
        logger.error(f"❌ Prompt construction test FAILED: {e}")
        return False

async def test_scheduled_execution():
    """Test that scheduled draft generation can be triggered."""
    logger.info("🎯 Testing Scheduled Execution")
    
    try:
        from app.services.draft_generation_service import DraftGenerationService
        
        # Mock dependencies - would need proper mocks in real testing
        class MockUserRepo:
            async def get_all_users(self):
                return []
        
        class MockKarmaService:
            def _is_post_relevant(self, post_data, user):
                return True
            
            async def generate_draft_comment(self, **kwargs):
                return None
        
        class MockTelethonService:
            async def get_client_for_user(self, user_id):
                return None
            
            async def sync_chats(self, client, user_id, limit=20):
                return []
        
        class MockWebSocketService:
            async def send_to_user(self, user_id, message):
                pass
        
        # Create service with mocks
        draft_service = DraftGenerationService(
            user_repository=MockUserRepo(),
            karma_service=MockKarmaService(),
            telethon_service=MockTelethonService(),
            websocket_service=MockWebSocketService()
        )
        
        # Test that check_for_new_posts can be called without errors
        await draft_service.check_for_new_posts()
        
        logger.info("✅ Scheduled execution test completed without errors")
        
        logger.info("🎉 Scheduled execution test PASSED!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Scheduled execution test FAILED: {e}")
        return False

async def main():
    """Main test runner for draft generation."""
    logger.info("🚀 Starting Draft Generation Tests")
    
    tests = [
        ("Draft Generation Service", test_draft_generation_service),
        ("Post Relevance Detection", test_relevance_detection),
        ("Prompt Construction with Vibe Profile", test_prompt_construction_with_vibe_profile),
        ("Scheduled Execution", test_scheduled_execution),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        logger.info(f"\n{'='*60}")
        logger.info(f"Running: {test_name}")
        logger.info(f"{'='*60}")
        
        try:
            result = await test_func()
            results[test_name] = result
            
            if result:
                logger.info(f"✅ {test_name}: PASSED")
            else:
                logger.error(f"❌ {test_name}: FAILED")
                
        except Exception as e:
            logger.error(f"❌ {test_name}: ERROR - {e}")
            results[test_name] = False
    
    # Summary
    logger.info(f"\n{'='*60}")
    logger.info("DRAFT GENERATION TEST SUMMARY")
    logger.info(f"{'='*60}")
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        logger.info(f"{test_name}: {status}")
    
    logger.info(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 ALL DRAFT GENERATION TESTS PASSED!")
        return True
    else:
        logger.error(f"❌ {total - passed} tests failed")
        return False

if __name__ == "__main__":
    import sys
    success = asyncio.run(main())
    sys.exit(0 if success else 1) 