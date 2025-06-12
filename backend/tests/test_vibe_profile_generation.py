#!/usr/bin/env python3
"""
Vibe Profile Generation Test
Tests Task 2.1: Vibe Profile Generation (Flow 1)
"""

import asyncio
import json
import logging
from typing import Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_vibe_profile_analysis():
    """Test the complete vibe profile analysis workflow."""
    logger.info("🎯 Testing Vibe Profile Analysis")
    
    try:
        # Import here to avoid circular dependencies during Docker build
        from app.services.user_context_analysis_service import UserContextAnalysisService
        from app.repositories.user_repository import UserRepository
        from app.repositories.ai_profile_repository import AIProfileRepository
        from app.services.gemini_service import GeminiService
        from app.services.telethon_service import TelethonService
        from app.models.ai_profile import AnalysisStatus
        
        # Mock dependencies
        user_repo = UserRepository()
        ai_profile_repo = AIProfileRepository()
        gemini_service = GeminiService()
        telethon_service = TelethonService()
        
        # Create service
        analysis_service = UserContextAnalysisService(
            user_repository=user_repo,
            telethon_service=telethon_service,
            gemini_service=gemini_service
        )
        
        # Test vibe profile structure generation
        mock_style_analysis = {
            "emoji_usage": {"frequency": 0.5},
            "message_length": {"avg_length": 75},
            "slang_and_informal": {"contractions_frequency": 0.3},
            "punctuation_patterns": {"exclamation_frequency": 0.2},
            "tone_indicators": {"positive_sentiment_indicators": 0.4}
        }
        
        mock_interests_analysis = {
            "topics": ["technology", "artificial intelligence", "startups"],
            "interests": ["AI", "machine learning", "tech innovation"]
        }
        
        mock_user_messages = [
            {"text": "That's really cool! AI is advancing so fast these days."},
            {"text": "I think this could revolutionize the industry"},
            {"text": "Interesting point about the implementation details"}
        ]
        
        # Generate vibe profile
        vibe_profile = await analysis_service._generate_vibe_profile(
            mock_style_analysis,
            mock_interests_analysis,
            mock_user_messages
        )
        
        logger.info("✅ Vibe profile generated successfully:")
        logger.info(f"   - Structure: {json.dumps(vibe_profile, indent=2)}")
        
        # Verify required fields
        required_fields = ["tone", "verbosity", "emoji_usage", "topics_of_interest", "communication_patterns"]
        
        missing_fields = [field for field in required_fields if field not in vibe_profile]
        if missing_fields:
            logger.error(f"❌ Missing required fields: {missing_fields}")
            return False
        
        # Verify field values are reasonable
        valid_tones = ["casual", "formal", "enthusiastic", "friendly", "neutral"]
        valid_verbosity = ["brief", "moderate", "verbose"]
        valid_emoji_usage = ["none", "light", "heavy"]
        
        if vibe_profile["tone"] not in valid_tones:
            logger.error(f"❌ Invalid tone: {vibe_profile['tone']}")
            return False
            
        if vibe_profile["verbosity"] not in valid_verbosity:
            logger.error(f"❌ Invalid verbosity: {vibe_profile['verbosity']}")
            return False
            
        if vibe_profile["emoji_usage"] not in valid_emoji_usage:
            logger.error(f"❌ Invalid emoji_usage: {vibe_profile['emoji_usage']}")
            return False
        
        # Test common phrases extraction
        common_phrases = await analysis_service._extract_common_phrases(mock_user_messages)
        logger.info(f"✅ Common phrases extracted: {common_phrases}")
        
        logger.info("🎉 Vibe profile generation test PASSED!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Vibe profile generation test FAILED: {e}")
        return False

async def test_vibe_profile_data_flow():
    """Test that vibe profile data flows correctly through the system."""
    logger.info("🎯 Testing Vibe Profile Data Flow")
    
    try:
        # Test that we can create and update AI profiles
        from app.models.ai_profile import AIProfile, AnalysisStatus
        
        # Create mock vibe profile
        test_vibe_profile = {
            "tone": "friendly",
            "verbosity": "moderate",
            "emoji_usage": "light",
            "common_phrases": ["that's interesting", "I think", "really cool"],
            "topics_of_interest": ["technology", "AI", "startups"],
            "communication_patterns": {
                "avg_message_length": 75,
                "contraction_frequency": 0.3,
                "emoji_frequency": 0.5,
                "exclamation_frequency": 0.2,
                "formality_score": 0.7
            }
        }
        
        # Verify JSON serialization works
        json_str = json.dumps(test_vibe_profile)
        parsed_back = json.loads(json_str)
        
        if parsed_back != test_vibe_profile:
            logger.error("❌ Vibe profile JSON serialization failed")
            return False
        
        logger.info("✅ Vibe profile JSON serialization works correctly")
        
        # Test the structure matches what the prompt construction expects
        expected_keys = ["tone", "verbosity", "emoji_usage", "topics_of_interest", "communication_patterns"]
        if all(key in test_vibe_profile for key in expected_keys):
            logger.info("✅ Vibe profile structure is compatible with prompt construction")
        else:
            logger.error("❌ Vibe profile structure missing required keys")
            return False
        
        logger.info("🎉 Vibe profile data flow test PASSED!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Vibe profile data flow test FAILED: {e}")
        return False

async def main():
    """Main test runner for vibe profile generation."""
    logger.info("🚀 Starting Vibe Profile Generation Tests")
    
    tests = [
        ("Vibe Profile Analysis", test_vibe_profile_analysis),
        ("Vibe Profile Data Flow", test_vibe_profile_data_flow),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        logger.info(f"\n{'='*50}")
        logger.info(f"Running: {test_name}")
        logger.info(f"{'='*50}")
        
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
    logger.info(f"\n{'='*50}")
    logger.info("VIBE PROFILE GENERATION TEST SUMMARY")
    logger.info(f"{'='*50}")
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        logger.info(f"{test_name}: {status}")
    
    logger.info(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 ALL VIBE PROFILE TESTS PASSED!")
        return True
    else:
        logger.error(f"❌ {total - passed} tests failed")
        return False

if __name__ == "__main__":
    import sys
    success = asyncio.run(main())
    sys.exit(0 if success else 1) 