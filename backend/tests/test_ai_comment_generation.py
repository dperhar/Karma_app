#!/usr/bin/env python3
"""Test AI comment generation with Mark Zuckerberg persona."""

import asyncio
import json
import sys
import os

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.dependencies import container
from app.services.karma_service import KarmaService
from app.repositories.user_repository import UserRepository


async def test_ai_comment_generation():
    """Test AI comment generation."""
    
    try:
        print("🔄 Testing AI comment generation...")
        
        # Get services
        user_repo = UserRepository()
        karma_service = container.resolve(KarmaService)
        
        # Get user with Mark Zuckerberg persona
        user = await user_repo.get_user_by_telegram_id(118672216)
        if not user:
            print("❌ User not found")
            return
            
        print(f"✅ Found user: {user.persona_name} (@{user.username})")
        
        # Test post data about AI/VR (should be relevant to Mark Zuckerberg's interests)
        test_post_data = {
            'id': 'test_123',
            'telegram_id': 123,
            'text': 'Apple released new Vision Pro updates with improved spatial computing capabilities. The AR/VR market is growing rapidly and changing how we interact with digital content.',
            'channel': {
                'title': 'Tech News Channel',
                'username': 'tech_news'
            },
            'date': '2024-01-15T10:00:00',
            'views': 1000,
            'reactions': []
        }
        
        print("📝 Test post:")
        print(f"   Text: {test_post_data['text']}")
        print(f"   Channel: {test_post_data['channel']['title']}")
        
        # Generate draft comment
        print("\n🤖 Generating AI comment...")
        draft = await karma_service.generate_draft_comment(
            original_message_id="test_message_123",
            user_id=user.id,
            post_data=test_post_data
        )
        
        if draft:
            print("✅ AI comment generated successfully!")
            print(f"   Draft ID: {draft.id}")
            print(f"   Persona: {draft.persona_name}")
            print(f"   AI Model: {draft.ai_model_used}")
            print(f"   Generated Comment: {draft.draft_text}")
            print(f"   Status: {draft.status}")
        else:
            print("❌ Failed to generate AI comment")
            
        # Test with irrelevant post (should be skipped)
        print("\n" + "="*50)
        print("Testing with irrelevant post...")
        
        irrelevant_post_data = {
            'id': 'test_456',
            'telegram_id': 456,
            'text': 'Best recipe for chocolate cake! Mix flour, eggs, and cocoa powder. Bake for 30 minutes at 180°C.',
            'channel': {
                'title': 'Cooking Channel',
                'username': 'cooking_tips'
            },
            'date': '2024-01-15T11:00:00',
            'views': 500,
            'reactions': []
        }
        
        print("📝 Irrelevant post:")
        print(f"   Text: {irrelevant_post_data['text']}")
        print(f"   Channel: {irrelevant_post_data['channel']['title']}")
        
        # This should return None because it's not relevant to tech interests
        print("\n🤖 Generating AI comment...")
        irrelevant_draft = await karma_service.generate_draft_comment(
            original_message_id="test_message_456",
            user_id=user.id,
            post_data=irrelevant_post_data
        )
        
        if irrelevant_draft:
            print("⚠️ AI comment generated for irrelevant post (unexpected):")
            print(f"   Generated Comment: {irrelevant_draft.draft_text}")
        else:
            print("✅ Correctly skipped irrelevant post")
            
    except Exception as e:
        print(f"❌ Error testing AI comment generation: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_ai_comment_generation()) 