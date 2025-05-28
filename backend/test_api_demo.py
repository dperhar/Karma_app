#!/usr/bin/env python3
"""Simple API test script for digital twin system."""

import asyncio
import json
from datetime import datetime
from services.dependencies import container
from services.domain.user_context_analysis_service import UserContextAnalysisService
from services.repositories.user_repository import UserRepository

async def test_api():
    """Test the digital twin API functionality."""
    
    print("🤖 Digital Twin API Test")
    print("=" * 50)
    
    try:
        # Get services
        user_repository = container.resolve(UserRepository)
        user_context_service = container.resolve(UserContextAnalysisService)
        
        # Find demo user
        demo_user = await user_repository.get_user_by_telegram_id(987654321)
        if not demo_user:
            print("❌ Demo user not found!")
            return
            
        print(f"✅ Found user: {demo_user.first_name} {demo_user.last_name}")
        print(f"📊 User ID: {demo_user.id}")
        print(f"📱 Telegram ID: {demo_user.telegram_id}")
        
        # Show current user state
        print("\n📋 Current User Analysis State:")
        print(f"  • Analysis Status: {demo_user.context_analysis_status or 'Not analyzed'}")
        print(f"  • Last Analysis: {demo_user.last_context_analysis_at or 'Never'}")
        print(f"  • Style Description: {demo_user.persona_style_description or 'None'}")
        
        # Run analysis
        print("\n🔍 Running Context Analysis...")
        analysis_result = await user_context_service.analyze_user_context(None, demo_user.id)
        
        print(f"\n📈 Analysis Results:")
        print(f"  • Status: {analysis_result['status']}")
        
        if analysis_result['status'] == 'completed':
            print(f"  • Style Analysis: {json.dumps(analysis_result.get('style_analysis', {}), indent=4)}")
            print(f"  • Interests: {json.dumps(analysis_result.get('interests_analysis', {}), indent=4)}")
            print(f"  • Style Description: {analysis_result.get('style_description', 'N/A')}")
            print(f"  • System Prompt Generated: {'Yes' if analysis_result.get('system_prompt') else 'No'}")
        else:
            print(f"  • Reason: {analysis_result.get('reason', 'Unknown')}")
            
        # Check updated user
        updated_user = await user_repository.get_user(demo_user.id)
        print(f"\n✨ Updated User State:")
        print(f"  • Analysis Status: {updated_user.context_analysis_status}")
        print(f"  • Style Description: {updated_user.persona_style_description}")
        
        print("\n🎉 Test completed successfully!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_api()) 