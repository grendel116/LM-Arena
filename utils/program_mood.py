"""
Utility module for mapping emotional state styles in the UI.
Fast static resolver for LM-Arena (no extra network calls).
"""

def analyze_sentiment_with_llm(text: str) -> dict:
    """Returns static neutral/calm mood details without triggering secondary LLM queries."""
    return {
        "name": "calm",
        "color": "#ef4444",
        "glow": "rgba(239, 68, 68, 0.4)",
        "speed": "1.8s",
        "intensity": 0.5
    }

def extract_and_strip_mood(text: str) -> tuple[str, dict]:
    return text, analyze_sentiment_with_llm(text)

def analyze_emotional_state(text: str) -> dict:
    return analyze_sentiment_with_llm(text)
