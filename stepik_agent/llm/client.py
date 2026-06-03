import json
import logging
from typing import TypeVar

from openai import OpenAI
from pydantic import BaseModel

from stepik_agent.config import AppSettings


T = TypeVar("T", bound=BaseModel)
logger = logging.getLogger("stepik_agent")


class LLMClient:
    """Structured LLM calls via Pydantic response models."""

    def __init__(self, settings: AppSettings) -> None:
        self.settings = settings
        self._client = None
        if settings.openai_api_key and not settings.mock_llm:
            self._client = OpenAI(
                api_key=settings.openai_api_key,
                base_url=settings.openai_base_url,
            )

    def complete_structured(
        self,
        system: str,
        user: str,
        response_model: type[T],
    ) -> T:
        if self.settings.mock_llm or self._client is None:
            return self._mock_response(response_model, user)

        schema = response_model.model_json_schema()
        schema_hint = json.dumps(schema, ensure_ascii=False)
        messages = [
            {
                "role": "system",
                "content": f"{system}\nRespond with JSON only matching schema:\n{schema_hint}",
            },
            {"role": "user", "content": user},
        ]
        response = self._client.chat.completions.create(
            model=self.settings.openai_model,
            messages=messages,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content or "{}"
        logger.info("llm_structured_call model=%s", response_model.__name__)
        data = json.loads(raw)
        if response_model.__name__ == "RankingResult":
            if "summary" not in data:
                data["summary"] = str(data.get("analysis", data.get("rationale", "")))[:2000]
            data.setdefault("ranked", [])
            data.setdefault("rejected", [])
        if response_model.__name__ == "StepikSearchQuerySet" and "queries" not in data:
            data["queries"] = data.get("search_queries", data.get("keywords", []))
        if response_model.__name__ == "StepikSearchQueryRefinement":
            data.setdefault("queries", data.get("search_queries", []))
            data.setdefault("rationale", str(data.get("analysis", ""))[:500])
        if response_model.__name__ == "FreshnessQuerySet" and "queries" not in data:
            data["queries"] = data.get("search_queries", [])
        return response_model.model_validate(data)

    def complete_text(self, system: str, user: str) -> str:
        if self.settings.mock_llm or self._client is None:
            return user[:500]

        response = self._client.chat.completions.create(
            model=self.settings.openai_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return response.choices[0].message.content or ""

    def _mock_response(self, response_model: type[T], user: str) -> T:
        name = response_model.__name__
        if name == "StepikSearchQuerySet":
            base = user.split()[:3]
            word = base[-1] if base else "python"
            return response_model.model_validate(
                {"queries": [word, f"{word} basics", f"{word} course"]}
            )
        if name == "StepikSearchQueryRefinement":
            return response_model.model_validate(
                {
                    "queries": ["python data", "machine learning"],
                    "rationale": "Refined toward data topics.",
                }
            )
        if name == "FreshnessQuerySet":
            return response_model.model_validate(
                {"queries": ["Python relevance 2026", "ML tools 2026"]}
            )
        if name == "RankingResult":
            return response_model.model_validate(
                {
                    "ranked": [],
                    "rejected": [],
                    "summary": "Mock ranking: no LLM key configured.",
                }
            )
        if name == "JudgeVerdict":
            return response_model.model_validate(
                {"passed": True, "score": 0.8, "rationale": "Mock judge pass."}
            )
        return response_model.model_validate({})
