#!/usr/bin/env python3
"""Test script for analyzing the demo user's context."""

import asyncio
import logging
import os
from datetime import datetime

from dotenv import load_dotenv

from services.dependencies import container
from services.domain.user_context_analysis_service import UserContextAnalysisService
from services.repositories.user_repository import UserRepository

# Load environment variables from project root
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(env_path)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_demo_user_analysis():
    """Test the complete digital twin system with demo user."""
    logger.info("Starting demo user context analysis...")
    
    try:
        # Get services
        user_repository = container.resolve(UserRepository)
        user_context_service = container.resolve(UserContextAnalysisService)
        
        # Find demo user
        demo_user = await user_repository.get_user_by_telegram_id(987654321)
        if not demo_user:
            logger.error("Demo user not found! Please ensure test data is created.")
            return
            
        logger.info(f"Found demo user: {demo_user.first_name} {demo_user.last_name}")
        
        # Analyze user context
        logger.info("Analyzing user context...")
        analysis_result = await user_context_service.analyze_user_context(None, demo_user.id)
        
        logger.info("=== ANALYSIS RESULTS ===")
        logger.info(f"Status: {analysis_result['status']}")
        
        if analysis_result['status'] == 'completed':
            logger.info(f"Style Description: {analysis_result.get('style_description', 'N/A')}")
            logger.info(f"Interests Analysis: {analysis_result.get('interests_analysis', 'N/A')}")
            logger.info(f"Style Analysis: {analysis_result.get('style_analysis', 'N/A')}")
            logger.info(f"System Prompt Generated: {'Yes' if analysis_result.get('system_prompt') else 'No'}")
            
            # Check updated user data
            updated_user = await user_repository.get_by_id(demo_user.id)
            logger.info(f"Context Analysis Status: {updated_user.context_analysis_status}")
            logger.info(f"Last Analysis At: {updated_user.last_context_analysis_at}")
            
        else:
            logger.warning(f"Analysis failed: {analysis_result.get('reason', 'Unknown error')}")
            
    except Exception as e:
        logger.error(f"Error during analysis: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_demo_user_analysis()) 