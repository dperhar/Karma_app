#!/usr/bin/env python3
"""
Test script for the new LLM-based vibe profile generation functionality.
This script will test the updated UserContextAnalysisService.
"""

import asyncio
import json
from datetime import datetime

# Test the new LLM-based vibe profile generation
async def test_vibe_profile_generation():
    """Test the new _create_vibe_from_messages_llm method."""
    
    # Mock sample messages for testing
    sample_messages = [
        {"text": "Hey man, that's wild! 😄", "date": datetime.now()},
        {"text": "lol yeah makes sense", "date": datetime.now()},
        {"text": "Definitely agree with your point about AI startups", "date": datetime.now()},
        {"text": "That's exactly what I was thinking!", "date": datetime.now()},
        {"text": "No way, really? That's insane 🔥", "date": datetime.now()},
        {"text": "I've been working on some ML projects lately", "date": datetime.now()},
        {"text": "crypto market is wild these days", "date": datetime.now()},
        {"text": "bro that's actually genius", "date": datetime.now()},
        {"text": "Yeah I saw that news about OpenAI", "date": datetime.now()},
        {"text": "Makes total sense, good point", "date": datetime.now()},
    ]
    
    print("🧪 Testing Vibe Profile Generation...")
    print(f"📝 Sample messages: {len(sample_messages)}")
    
    # Test the Gemini service mock response
    from app.services.gemini_service import GeminiService
    
    gemini_service = GeminiService()
    print(f"🤖 Gemini service mock mode: {gemini_service.mock_mode}")
    
    # Test the generate_content method
    test_prompt = """
    Analyze the following collection of a user's sent Telegram messages to create a "Vibe Profile".
    Test messages: Hey man, that's wild! 😄
    """
    
    response = await gemini_service.generate_content(test_prompt)
    print(f"✅ Gemini response: {response}")
    
    # Test the full vibe profile creation
    from app.services.user_context_analysis_service import UserContextAnalysisService
    from app.repositories.user_repository import UserRepository
    from app.services.telethon_service import TelethonService
    
    # Create service instances (without database dependencies for this test)
    user_repo = None  # We'll mock this for the test
    telethon_service = TelethonService()
    
    analysis_service = UserContextAnalysisService(
        user_repository=user_repo,
        telethon_service=telethon_service,
        gemini_service=gemini_service
    )
    
    # Test the vibe profile creation method directly
    vibe_profile = await analysis_service._create_vibe_from_messages_llm(sample_messages)
    
    print(f"🎯 Generated vibe profile:")
    print(json.dumps(vibe_profile, indent=2))
    
    # Verify the structure
    if vibe_profile:
        expected_keys = ["tone", "verbosity", "emoji_usage", "common_phrases", "topics_of_interest"]
        missing_keys = [key for key in expected_keys if key not in vibe_profile]
        
        if not missing_keys:
            print("✅ Vibe profile structure is correct!")
        else:
            print(f"❌ Missing keys in vibe profile: {missing_keys}")
            
        # Print details about each field
        print("\n📊 Vibe Profile Analysis:")
        for key, value in vibe_profile.items():
            print(f"  {key}: {value}")
            
    else:
        print("❌ Vibe profile generation failed!")

if __name__ == "__main__":
    print("🚀 Starting Vibe Profile Test...")
    asyncio.run(test_vibe_profile_generation())
    print("🏁 Test completed!") 