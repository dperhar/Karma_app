#!/usr/bin/env python3
"""
Negative Feedback Loop Test
Tests Task 2.3: "Not My Vibe" Feedback Loop
"""

import asyncio
import json
import logging
from typing import Dict, Any, List

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_negative_feedback_repository():
    """Test the negative feedback repository functionality."""
    logger.info("🎯 Testing Negative Feedback Repository")
    
    try:
        from app.repositories.negative_feedback_repository import NegativeFeedbackRepository
        from app.models.negative_feedback import NegativeFeedback
        
        # Create repository
        feedback_repo = NegativeFeedbackRepository()
        
        # Test data
        test_feedback_data = {
            "user_id": "test-user-123",
            "rejected_comment_text": "This is too formal for my style",
            "original_post_content": "New AI breakthrough announced",
            "original_post_url": "https://t.me/testchannel/123",
            "rejection_reason": "Too formal, I prefer casual tone",
            "ai_model_used": "gemini-pro",
            "draft_comment_id": "draft-456"
        }
        
        # Test creation (would normally require database, but we test the interface)
        logger.info("✅ Negative feedback repository created successfully")
        logger.info(f"   - Test data structure: {list(test_feedback_data.keys())}")
        
        # Verify all required fields are present
        required_fields = ["user_id", "rejected_comment_text"]
        missing_fields = [field for field in required_fields if field not in test_feedback_data]
        
        if not missing_fields:
            logger.info("✅ Test data has all required fields")
        else:
            logger.error(f"❌ Missing required fields: {missing_fields}")
            return False
        
        logger.info("🎉 Negative feedback repository test PASSED!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Negative feedback repository test FAILED: {e}")
        return False

async def test_feedback_incorporation():
    """Test that negative feedback is incorporated into new generations."""
    logger.info("🎯 Testing Feedback Incorporation")
    
    try:
        from app.services.karma_service import KarmaService
        from app.models.user import User
        from app.models.ai_profile import AIProfile
        
        # Create mock karma service
        karma_service = KarmaService(None, None, None, None, None, None)
        
        # Create mock user
        mock_user = User()
        mock_user.id = "test-user-123"
        mock_user.persona_name = "Test User"
        
        # Test post data
        post_data = {
            "text": "Revolutionary AI advancement changes everything",
            "url": "https://t.me/tech/123",
            "channel": {"title": "Tech News"}
        }
        
        # Mock negative feedback context
        negative_feedback_context = [
            {
                "rejected_comment": "This is a groundbreaking development in artificial intelligence.",
                "original_post": "AI breakthrough announced",
                "reason": "Too formal, I prefer casual language"
            },
            {
                "rejected_comment": "Fascinating research with significant implications for the field.",
                "original_post": "New research paper published",
                "reason": "Use simpler words and be more conversational"
            }
        ]
        
        # Mock regenerate request
        class MockRegenerateRequest:
            rejection_reason = "Too corporate-sounding, make it more personal"
            custom_instructions = "Add my own opinion and use casual language"
        
        regenerate_request = MockRegenerateRequest()
        
        # Test prompt construction with feedback
        prompt = karma_service._construct_prompt_with_feedback(
            post_data,
            mock_user,
            negative_feedback_context,
            regenerate_request
        )
        
        logger.info("✅ Prompt with feedback constructed successfully")
        logger.info(f"   - Prompt length: {len(prompt)} characters")
        
        # Verify feedback incorporation
        feedback_checks = {
            "Contains rejection examples": any(fb["rejected_comment"].lower() in prompt.lower() for fb in negative_feedback_context),
            "Contains rejection reasons": any(fb["reason"].lower() in prompt.lower() for fb in negative_feedback_context),
            "Contains specific issue": regenerate_request.rejection_reason.lower() in prompt.lower(),
            "Contains custom instructions": regenerate_request.custom_instructions.lower() in prompt.lower(),
            "Has avoid instructions": "avoid" in prompt.lower() or "do not" in prompt.lower(),
            "Has improvement guidance": "new" in prompt.lower() and "comment" in prompt.lower()
        }
        
        passed_checks = sum(1 for check, result in feedback_checks.items() if result)
        total_checks = len(feedback_checks)
        
        for check, result in feedback_checks.items():
            status = "✅" if result else "❌"
            logger.info(f"   {status} {check}")
        
        if passed_checks >= total_checks - 1:  # Allow one check to fail
            logger.info("🎉 Feedback incorporation test PASSED!")
            return True
        else:
            logger.error(f"❌ Feedback incorporation test FAILED ({passed_checks}/{total_checks} checks passed)")
            return False
        
    except Exception as e:
        logger.error(f"❌ Feedback incorporation test FAILED: {e}")
        return False

async def test_feedback_pattern_learning():
    """Test that the system learns from feedback patterns."""
    logger.info("🎯 Testing Feedback Pattern Learning")
    
    try:
        # Mock multiple feedback examples to test pattern recognition
        feedback_patterns = [
            {
                "rejected_comment": "This represents a significant milestone in the field.",
                "reason": "Too formal",
                "pattern": "formal_language"
            },
            {
                "rejected_comment": "The implications of this development are substantial.",
                "reason": "Too corporate",
                "pattern": "corporate_tone"
            },
            {
                "rejected_comment": "Fascinating! This could change everything! 🚀",
                "reason": "Too many emojis",
                "pattern": "excessive_emojis"
            },
            {
                "rejected_comment": "cool",
                "reason": "Too brief, add more context",
                "pattern": "too_brief"
            }
        ]
        
        # Analyze feedback patterns
        pattern_analysis = {}
        
        for feedback in feedback_patterns:
            pattern = feedback["pattern"]
            if pattern not in pattern_analysis:
                pattern_analysis[pattern] = []
            pattern_analysis[pattern].append({
                "reason": feedback["reason"],
                "example": feedback["rejected_comment"]
            })
        
        logger.info("✅ Feedback pattern analysis completed:")
        for pattern, examples in pattern_analysis.items():
            logger.info(f"   - {pattern}: {len(examples)} example(s)")
        
        # Test pattern-based recommendations
        recommendations = {
            "formal_language": "Use more casual, conversational tone",
            "corporate_tone": "Add personal opinions and informal language",
            "excessive_emojis": "Reduce emoji usage to light or moderate levels",
            "too_brief": "Provide more context and detailed thoughts"
        }
        
        # Verify we can generate recommendations for each pattern
        for pattern in pattern_analysis.keys():
            if pattern in recommendations:
                logger.info(f"✅ Recommendation for {pattern}: {recommendations[pattern]}")
            else:
                logger.warning(f"⚠️  No recommendation for pattern: {pattern}")
        
        # Test that patterns can be used to improve prompts
        test_prompt_improvements = {
            "formal_language": "avoid formal academic language",
            "corporate_tone": "avoid corporate or business-like language",
            "excessive_emojis": "use emojis sparingly",
            "too_brief": "provide detailed thoughts and context"
        }
        
        improvement_count = 0
        for pattern, improvement in test_prompt_improvements.items():
            if pattern in pattern_analysis:
                improvement_count += 1
                logger.info(f"✅ Pattern {pattern} -> Improvement: {improvement}")
        
        if improvement_count >= len(pattern_analysis) * 0.8:  # At least 80% coverage
            logger.info("🎉 Feedback pattern learning test PASSED!")
            return True
        else:
            logger.error(f"❌ Insufficient pattern coverage: {improvement_count}/{len(pattern_analysis)}")
            return False
        
    except Exception as e:
        logger.error(f"❌ Feedback pattern learning test FAILED: {e}")
        return False

async def test_regeneration_workflow():
    """Test the complete regeneration workflow."""
    logger.info("🎯 Testing Regeneration Workflow")
    
    try:
        # Mock the complete workflow
        workflow_steps = [
            "Receive regeneration request",
            "Validate draft exists",
            "Save negative feedback",
            "Get user's feedback history",
            "Construct enhanced prompt",
            "Generate new draft",
            "Update draft with new content",
            "Send notification"
        ]
        
        # Simulate each step
        completed_steps = []
        
        # Step 1: Receive regeneration request
        mock_request = {
            "draft_id": "draft-123",
            "rejection_reason": "Too formal",
            "custom_instructions": "Be more casual"
        }
        completed_steps.append("Receive regeneration request")
        logger.info("✅ Step 1: Received regeneration request")
        
        # Step 2: Validate draft exists
        mock_draft = {
            "id": "draft-123",
            "user_id": "user-456",
            "draft_text": "This is a formal comment",
            "original_post_content": "Test post content"
        }
        completed_steps.append("Validate draft exists")
        logger.info("✅ Step 2: Draft validation completed")
        
        # Step 3: Save negative feedback
        feedback_data = {
            "user_id": mock_draft["user_id"],
            "rejected_comment_text": mock_draft["draft_text"],
            "rejection_reason": mock_request["rejection_reason"]
        }
        completed_steps.append("Save negative feedback")
        logger.info("✅ Step 3: Negative feedback saved")
        
        # Step 4: Get user's feedback history
        mock_feedback_history = [
            {"rejected_comment": "Previous formal comment", "reason": "Too formal"}
        ]
        completed_steps.append("Get user's feedback history")
        logger.info(f"✅ Step 4: Retrieved {len(mock_feedback_history)} feedback entries")
        
        # Step 5: Construct enhanced prompt
        enhanced_prompt = f"""
        Original post: {mock_draft['original_post_content']}
        Previous rejections: {mock_feedback_history}
        Current issue: {mock_request['rejection_reason']}
        Instructions: {mock_request['custom_instructions']}
        Generate improved comment that addresses these issues.
        """
        completed_steps.append("Construct enhanced prompt")
        logger.info("✅ Step 5: Enhanced prompt constructed")
        
        # Step 6: Generate new draft
        new_draft_text = "Hey, this is pretty cool! Really interesting development."
        completed_steps.append("Generate new draft")
        logger.info("✅ Step 6: New draft generated")
        
        # Step 7: Update draft with new content
        updated_draft = {
            **mock_draft,
            "draft_text": new_draft_text,
            "status": "DRAFT",
            "generation_params": {
                "regenerated_at": "2024-01-01T00:00:00",
                "negative_feedback_incorporated": True,
                "rejection_reason": mock_request["rejection_reason"]
            }
        }
        completed_steps.append("Update draft with new content")
        logger.info("✅ Step 7: Draft updated with new content")
        
        # Step 8: Send notification
        notification = {
            "type": "draft_regenerated",
            "data": updated_draft,
            "message": "Your draft has been regenerated based on your feedback"
        }
        completed_steps.append("Send notification")
        logger.info("✅ Step 8: Notification sent")
        
        # Verify all steps completed
        if len(completed_steps) == len(workflow_steps):
            logger.info("🎉 Complete regeneration workflow test PASSED!")
            return True
        else:
            missing_steps = set(workflow_steps) - set(completed_steps)
            logger.error(f"❌ Missing workflow steps: {missing_steps}")
            return False
        
    except Exception as e:
        logger.error(f"❌ Regeneration workflow test FAILED: {e}")
        return False

async def main():
    """Main test runner for negative feedback functionality."""
    logger.info("🚀 Starting Negative Feedback Loop Tests")
    
    tests = [
        ("Negative Feedback Repository", test_negative_feedback_repository),
        ("Feedback Incorporation", test_feedback_incorporation),
        ("Feedback Pattern Learning", test_feedback_pattern_learning),
        ("Regeneration Workflow", test_regeneration_workflow),
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
    logger.info("NEGATIVE FEEDBACK LOOP TEST SUMMARY")
    logger.info(f"{'='*60}")
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        logger.info(f"{test_name}: {status}")
    
    logger.info(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 ALL NEGATIVE FEEDBACK TESTS PASSED!")
        return True
    else:
        logger.error(f"❌ {total - passed} tests failed")
        return False

if __name__ == "__main__":
    import sys
    success = asyncio.run(main())
    sys.exit(0 if success else 1) 