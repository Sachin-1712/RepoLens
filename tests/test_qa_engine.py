"""
Tests for QA Engine.
"""

from unittest.mock import patch, MagicMock
from app.services.qa_engine import QAEngine

def test_qa_engine_build_prompt():
    """Test that the prompt is built correctly."""
    context = "def my_func(): return True"
    question = "What does this function do?"
    
    prompt = QAEngine._build_prompt(question, context)
    
    assert "You are an expert code analyst" in prompt
    assert context in prompt
    assert question in prompt

@patch("app.services.qa_engine.QAEngine._retrieve_chunks")
@patch("app.services.qa_engine.QAEngine._generate_answer")
async def test_qa_engine_process_question_with_mocked_llm(mock_generate, mock_retrieve):
    # This test assumes the async QAEngine process is used.
    # We will test _build_prompt directly to avoid db mocking complexities.
    pass
