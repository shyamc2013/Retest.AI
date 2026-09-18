"""Question-generation agent powered by Groq GPT-OSS."""
from __future__ import annotations

from config import QUESTION_COUNT, QUESTION_MAX_OUTPUT_TOKENS
from feedback_store import feedback_context, weak_topics
from groq_client import complete_json
from models import Question, QuestionSet


def _topic_mix_instruction() -> str:
    weak = weak_topics()
    if not weak:
        return "No prior weak topics are recorded, so distribute questions across the source material's topics broadly."
    half = QUESTION_COUNT // 2
    return (
        f"This is a retest. Exactly {half} of the {QUESTION_COUNT} questions must test these weak topics: "
        f"{', '.join(weak)}. The remaining {QUESTION_COUNT - half} questions must be drawn from the OTHER topics "
        "in the source material (not the weak topics listed above), to keep coverage balanced rather than "
        "concentrated only on past mistakes."
    )


def _prompt(document_text: str) -> str:
    return f"""You are an expert assessment designer. Create exactly {QUESTION_COUNT} fresh questions based only on the source material below.

The quiz MUST include all four question types: `mcq_single`, `mcq_multiple`, `true_false`, and `fill_blank`. Include at least 3 questions of each type; distribute the remaining questions among the four types based on what the material best supports. Do not repeat questions from a prior attempt. `mcq_single` has exactly one correct option: provide option text in `options` and make `correct_answer` that option string. `mcq_multiple` has two or more correct options: provide option text in `options` and make `correct_answer` a list containing every correct option string. For true_false, use `correct_answer` as the JSON string `"True"` or `"False"` (never a JSON boolean) and leave options empty. For fill_blank, leave options empty and make the answer concise. IDs must be unique integers from 1 through {QUESTION_COUNT}.

{_topic_mix_instruction()}

Adaptation context:
{feedback_context()}

Source material:
{document_text}
"""


def generate_questions(document_text: str) -> list[Question]:
    """Generate a complete test, retrying once for a transient provider failure."""
    errors: list[str] = []
    for _ in range(2):
        try:
            response = complete_json(
                prompt=_prompt(document_text),
                response_model=QuestionSet,
                schema_name="question_set",
                temperature=0.7,
                max_tokens=QUESTION_MAX_OUTPUT_TOKENS,
                reasoning_effort="low",
            )
            questions = [draft.to_question() for draft in QuestionSet.model_validate_json(response).questions]
            if len(questions) != QUESTION_COUNT or {item.id for item in questions} != set(range(1, QUESTION_COUNT + 1)):
                raise ValueError(f"Expected exactly {QUESTION_COUNT} uniquely numbered questions.")
            missing_types = {"mcq_single", "mcq_multiple", "true_false", "fill_blank"} - {q.type for q in questions}
            if missing_types:
                raise ValueError(f"Missing required question types: {sorted(missing_types)}")
            weak = {topic.strip().casefold() for topic in weak_topics()}
            if weak:
                weak_count = sum(1 for q in questions if q.topic.strip().casefold() in weak)
                if weak_count == 0 or weak_count == QUESTION_COUNT:
                    raise ValueError(
                        f"Expected a mix of weak-topic and other-topic questions, got {weak_count}/{QUESTION_COUNT} weak-topic questions."
                    )
            return questions
        except Exception as error:
            errors.append(f"{type(error).__name__}: {error}")
    raise RuntimeError("Question generation failed after two Groq attempts. " + " | ".join(errors))
