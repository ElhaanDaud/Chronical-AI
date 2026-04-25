import hashlib
import json
import time

import numpy as np
from openai import AsyncOpenAI

from app.config import settings
from app.core.logging import logger

_dmr_client: AsyncOpenAI | None = None
_groq_client: AsyncOpenAI | None = None
_embedding_client: AsyncOpenAI | None = None

_prompt_cache: dict[str, tuple[str, float]] = {}
CACHE_TTL = 600


def _get_dmr_client() -> AsyncOpenAI:
    global _dmr_client
    if _dmr_client is None:
        _dmr_client = AsyncOpenAI(
            base_url=settings.llm_base_url,
            api_key="not-needed",
            timeout=60.0,
        )
    return _dmr_client


def _get_embedding_client() -> AsyncOpenAI:
    global _embedding_client
    if _embedding_client is None:
        _embedding_client = AsyncOpenAI(
            base_url=settings.embedding_base_url,
            api_key="not-needed",
            timeout=60.0,
        )
    return _embedding_client


def _get_groq_client() -> AsyncOpenAI | None:
    global _groq_client
    if not settings.groq_api_key:
        return None
    if _groq_client is None:
        _groq_client = AsyncOpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=settings.groq_api_key,
            timeout=30.0,
        )
    return _groq_client


async def _call_llm(
    system_prompt: str,
    user_prompt: str,
    json_mode: bool = False,
    max_tokens: int = 512,
) -> str | None:
    cache_key = hashlib.md5(f"{system_prompt}|{user_prompt}".encode()).hexdigest()
    now = time.time()
    if cache_key in _prompt_cache:
        cached_result, cached_at = _prompt_cache[cache_key]
        if now - cached_at < CACHE_TTL:
            return cached_result
        del _prompt_cache[cache_key]

    providers = []

    if settings.llm_provider == "dmr":
        providers.append(("dmr", _get_dmr_client(), settings.llm_model))
        groq = _get_groq_client()
        if groq:
            providers.append(("groq", groq, "llama-3.1-8b-instant"))
    else:
        groq = _get_groq_client()
        if groq:
            providers.append(("groq", groq, "llama-3.1-8b-instant"))
        providers.append(("dmr", _get_dmr_client(), settings.llm_model))

    kwargs = {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "max_tokens": max_tokens,
        "temperature": 0.1,
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    for name, client, model in providers:
        try:
            resp = await client.chat.completions.create(model=model, **kwargs)
            content = resp.choices[0].message.content
            if content:
                result = content.strip()
                _prompt_cache[cache_key] = (result, time.time())
                if len(_prompt_cache) > 500:
                    oldest_key = min(_prompt_cache, key=lambda k: _prompt_cache[k][1])
                    del _prompt_cache[oldest_key]
                return result
        except Exception as e:
            logger.warning(f"LLM provider '{name}' failed: {e}")
            continue

    return None


async def generate_topic_label(article_titles: list[str]) -> str | None:
    if not article_titles:
        return None

    titles_text = "\n".join(f"- {t}" for t in article_titles[:15])
    system = (
        "You are a news editor. Given article titles from a news cluster, "
        "generate a concise 3-6 word topic label that captures the common theme.\n"
        'Output JSON: {"label": "Your Topic Label"}'
    )
    user = f"Article titles:\n{titles_text}"

    result = await _call_llm(system, user, json_mode=True, max_tokens=100)
    if not result:
        return None

    try:
        data = json.loads(result)
        label = data.get("label")
        if label:
            return label
    except (json.JSONDecodeError, AttributeError):
        pass

    import re
    match = re.search(r'"label"\s*:\s*"([^"]+)"', result)
    if match:
        return match.group(1)

    return result[:80].strip('{}" \n') if result else None


async def score_coherence(article_titles: list[str]) -> float:
    if len(article_titles) < 2:
        return 1.0

    titles_text = "\n".join(f"- {t}" for t in article_titles[:10])
    system = (
        "You are a news clustering quality judge. "
        "Given article titles supposedly from the same news story cluster, "
        "rate how coherent the cluster is from 0.0 (completely unrelated) "
        "to 1.0 (all about the same story). "
        "Respond ONLY with JSON: {\"score\": 0.85, \"reason\": \"brief reason\"}"
    )
    user = f"Cluster articles:\n{titles_text}"

    result = await _call_llm(system, user, json_mode=True, max_tokens=150)
    if not result:
        return 0.5

    try:
        data = json.loads(result)
        score = float(data.get("score", 0.5))
        return max(0.0, min(1.0, score))
    except (json.JSONDecodeError, ValueError, AttributeError):
        return 0.5


async def generate_commit_summary(
    topic_label: str,
    article_titles: list[str],
    article_summaries: list[str],
) -> tuple[str, str] | None:
    if not article_titles:
        return None

    articles_text = "\n".join(
        f"- {t}: {s[:100]}" for t, s in zip(article_titles[:5], article_summaries[:5])
    )
    system = (
        "You are a news editor. Summarize the latest developments in this story.\n"
        f"Story: {topic_label}\n\n"
        "Output JSON with two fields:\n"
        '- "message": A headline-style summary in 10-20 words\n'
        '- "detail": A 2-3 sentence paragraph explaining the key developments'
    )
    user = f"Latest articles:\n{articles_text}"

    result = await _call_llm(system, user, json_mode=True, max_tokens=300)
    if not result:
        return None

    try:
        data = json.loads(result)
        message = data.get("message", "")[:150]
        detail = data.get("detail", "")
        if message and detail and message.lower() not in ("short update", "update", "news update"):
            return message, detail
    except (json.JSONDecodeError, AttributeError):
        pass

    import re
    msg_match = re.search(r'"message"\s*:\s*"([^"]+)"', result)
    det_match = re.search(r'"detail"\s*:\s*"([^"]+)"', result)
    if msg_match and det_match:
        msg = msg_match.group(1)[:150]
        if msg.lower() not in ("short update", "update", "news update"):
            return msg, det_match.group(1)

    return None


async def get_embeddings(texts: list[str]) -> np.ndarray | None:
    if not texts:
        return None

    client = _get_embedding_client()
    try:
        resp = await client.embeddings.create(
            model=settings.embedding_model,
            input=texts,
        )
        vectors = [item.embedding for item in resp.data]
        return np.array(vectors, dtype=np.float32)
    except Exception as e:
        logger.warning(f"Embedding request failed: {e}")
        return None
