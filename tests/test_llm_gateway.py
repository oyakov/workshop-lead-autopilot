from __future__ import annotations

import pytest
from app.llm.gateway import chat
from app.config import Settings, get_settings


@pytest.mark.asyncio
async def test_llm_gateway_primary_success(mocker):
    # Mock settings
    mocker.patch(
        "app.llm.gateway.get_settings",
        return_value=Settings(
            llm_provider="openai",
            llm_fallback_provider="gemini"
        )
    )
    
    # Mock OpenAI client response
    mock_openai = mocker.patch("app.llm.openai_compat.chat")
    mock_openai.return_value = "OpenAI response"
    
    mock_gemini = mocker.patch("app.llm.gemini.chat")
    
    result = await chat([{"role": "user", "content": "hi"}])
    
    assert result == "OpenAI response"
    mock_openai.assert_called_once()
    mock_gemini.assert_not_called()


@pytest.mark.asyncio
async def test_llm_gateway_primary_fails_fallback_success(mocker):
    mocker.patch(
        "app.llm.gateway.get_settings",
        return_value=Settings(
            llm_provider="openai",
            llm_fallback_provider="gemini"
        )
    )
    
    mock_openai = mocker.patch("app.llm.openai_compat.chat")
    mock_openai.side_effect = Exception("OpenAI model down")
    
    mock_gemini = mocker.patch("app.llm.gemini.chat")
    mock_gemini.return_value = "Gemini response"
    
    result = await chat([{"role": "user", "content": "hi"}])
    
    assert result == "Gemini response"
    mock_openai.assert_called_once()
    mock_gemini.assert_called_once()


@pytest.mark.asyncio
async def test_llm_gateway_both_fail(mocker):
    mocker.patch(
        "app.llm.gateway.get_settings",
        return_value=Settings(
            llm_provider="openai",
            llm_fallback_provider="gemini"
        )
    )
    
    mock_openai = mocker.patch("app.llm.openai_compat.chat")
    mock_openai.side_effect = Exception("OpenAI model down")
    
    mock_gemini = mocker.patch("app.llm.gemini.chat")
    mock_gemini.side_effect = Exception("Gemini model quota exceeded")
    
    result = await chat([{"role": "user", "content": "hi"}])
    
    assert result == ""
    mock_openai.assert_called_once()
    mock_gemini.assert_called_once()
