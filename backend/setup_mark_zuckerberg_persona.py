#!/usr/bin/env python3
"""Setup Mark Zuckerberg persona for a user."""

import asyncio
import json
import sys
import os

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.repositories.user_repository import UserRepository


async def setup_mark_zuckerberg_persona():
    """Setup Mark Zuckerberg persona for a user."""
    
    user_repo = UserRepository()
    
    try:
        print("🔄 Setting up Mark Zuckerberg persona...")
        
        # Get user by telegram_id (you can change this to the actual user's telegram_id)
        existing_user = await user_repo.get_user_by_telegram_id(118672216)
        if not existing_user:
            print("❌ User not found. Please create a user first.")
            return
        
        # Mark Zuckerberg persona data
        mark_zuckerberg_persona = {
            "persona_name": "Mark Zuckerberg",
            "persona_style_description": "Visionary tech leader who speaks with passion about connecting people and building the future. Uses accessible language to explain complex concepts. Optimistic about technology's potential while acknowledging challenges. Focuses on long-term thinking and metaverse/VR innovations.",
            "persona_interests_json": json.dumps([
                "Metaverse",
                "Virtual Reality", 
                "VR",
                "AR",
                "Augmented Reality",
                "AI",
                "Artificial Intelligence",
                "Machine Learning",
                "Web3",
                "Blockchain",
                "NFT",
                "Social Networks",
                "Facebook",
                "Meta",
                "Instagram",
                "WhatsApp",
                "Future of Work",
                "Remote Work",
                "Digital Transformation",
                "Privacy",
                "Technology",
                "Innovation",
                "Startup",
                "Entrepreneurship",
                "Social Impact",
                "Connecting People",
                "Community Building",
                "Open Source",
                "Developer Tools",
                "Platform Economy",
                "Digital Economy"
            ])
        }
        
        # Update user with persona
        updated_user = await user_repo.update_user(existing_user.id, **mark_zuckerberg_persona)
        
        if updated_user:
            print(f"✅ Mark Zuckerberg persona set up successfully for user: {updated_user.id}")
            print(f"   User: {updated_user.first_name} {updated_user.last_name} (@{updated_user.username})")
            print(f"   Persona: {updated_user.persona_name}")
            print(f"   Style: {updated_user.persona_style_description[:100]}...")
            print(f"   Interests: {len(json.loads(updated_user.persona_interests_json))} keywords")
        else:
            print("❌ Failed to update user with persona")
            
    except Exception as e:
        print(f"❌ Error setting up persona: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(setup_mark_zuckerberg_persona()) 