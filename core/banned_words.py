import sys
import os
import json
import re
import asyncio
from functools import lru_cache

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from variables.settings import BANNED_WORDS_FILE

DEFAULT_BIAS_WEIGHT = -10.0

# Strict pattern for 'not X, [it's] Y' or 'not A; B' contrast structures
ANTITHESIS_PATTERN = re.compile(
    r"\b(?:it's|that's|this\s+is)\s+not\s+[^;,.!?]+[;,]?\s*(?:it's|it\s+is|you're|there's)\b"
    r"|\bnot\s+a\s+[^;,.!?]+[;,]\s*(?:it's|it\s+is|this\s+is)\b",
    re.IGNORECASE
)

@lru_cache(maxsize=1)
def load_banned_words() -> list[str]:
    """Loads and caches banned words from file."""
    if not os.path.exists(BANNED_WORDS_FILE):
        return []
    try:
        with open(BANNED_WORDS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            banned = data.get("banned_words", [])
            if isinstance(banned, dict):
                return list(banned.keys())
            return list(banned)
    except Exception as e:
        print(f"[BANNED WORDS] Error loading {BANNED_WORDS_FILE}: {e}")
        return []

@lru_cache(maxsize=1)
def get_banned_words_regex() -> re.Pattern | None:
    """Builds pre-compiled regular expression for banned words."""
    words = load_banned_words()
    if not words:
        return None
    pattern = r"\b(?:" + "|".join(map(re.escape, words)) + r")\b"
    return re.compile(pattern, re.IGNORECASE)

def generate_llama_cli_args(gguf_path: str, bias_weight: float = None) -> list[str]:
    """Generates CLI flags for llama-server logit bias."""
    if bias_weight is None:
        bias_weight = DEFAULT_BIAS_WEIGHT
        
    words = load_banned_words()
    if not words or not os.path.isfile(gguf_path):
        return []

    token_ids = set()
    try:
        from llama_cpp import Llama
        llm = Llama(model_path=gguf_path, vocab_only=True, verbose=False)
        for word in words:
            clean_word = word.strip()
            if not clean_word:
                continue
            variants = [clean_word, f" {clean_word}", clean_word.capitalize(), f" {clean_word.capitalize()}"]
            for variant in variants:
                ids = llm.tokenize(variant.encode("utf-8"), add_bos=False)
                for t_id in ids:
                    token_ids.add(int(t_id))
        del llm
    except Exception as e:
        print(f"[BANNED WORDS] Notice: Tokenization skipped ({e}).", flush=True)
        return []

    if not token_ids:
        return []

    sign_str = "" if bias_weight < 0 else "+"
    bias_str = ",".join(f"{t_id}{sign_str}{bias_weight}" for t_id in token_ids)
    return ["--logit-bias", bias_str]

def match_case(target: str, source: str) -> str:
    """Preserves source word casing pattern on target word."""
    if source.isupper():
        return target.upper()
    if source.istitle():
        return target.capitalize()
    return target.lower()

def sanitize_text(text: str) -> str:
    """Performs deterministic case-matched banned word replacement."""
    if not text:
        return text
    banned_regex = get_banned_words_regex()
    if not banned_regex:
        return text
    return banned_regex.sub("[redacted]", text)

def get_banned_words_directive() -> str:
    """Constructs prompt directive restricting forbidden vocabulary."""
    words = load_banned_words()
    if not words:
        return ""
    words_list = ", ".join(f'"{w}"' for w in words)
    return f"\n- FORBIDDEN VOCABULARY: Do NOT use any of these words: {words_list}."
