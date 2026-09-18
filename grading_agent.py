"""Deterministic scoring plus source-grounded feedback from Groq GPT-OSS."""
from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone

from config import FEEDBACK_MAX_OUTPUT_TOKENS
from groq_client import complete_json
from models import (
    AnswerValue,
    FeedbackNarrative,
    FeedbackReport,
    GradedQuestion,
    Question,
    ScoredAnswer,
    TopicStat,
)


def score_answers(questions: list[Question], answers: dict[int, AnswerValue]) -> list[ScoredAnswer]:
    scored: list[ScoredAnswer] = []
    for question in questions:
        answer = answers.get(question.id, [] if question.type == "mcq_multiple" else "")
        if question.type == "mcq_multiple":
            correct = isinstance(answer, list) and isinstance(question.correct_answer, list) and set(answer) == set(question.correct_answer)
        elif question.type == "fill_blank":
            assert isinstance(answer, str) and isinstance(question.correct_answer, str)
            # Intentional v1 exact matching; a future version could use fuzzy/semantic matching.
            correct = answer.strip().casefold() == question.correct_answer.strip().casefold()
        else:
            correct = answer == question.correct_answer
        scored.append(ScoredAnswer(question_id=question.id, your_answer=answer, is_correct=correct))
    return scored


def _display_answer(answer: AnswerValue) -> str:
    return ", ".join(answer) if isinstance(answer, list) else answer


def _canonical_topics(questions: list[Question], scored: list[ScoredAnswer]) -> dict[str, TopicStat]:
    counts: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    results = {item.question_id: item.is_correct for item in scored}
    for question in questions:
        counts[question.topic][1] += 1
        counts[question.topic][0] += int(results[question.id])
    return {
        topic: TopicStat(correct=correct, total=total, status="strong" if correct / total >= 0.7 else "weak")
        for topic, (correct, total) in counts.items()
    }


def build_fallback_feedback(questions: list[Question], scored: list[ScoredAnswer]) -> FeedbackReport:
    """Produce useful, saved feedback if the explanatory provider call is unavailable."""
    verdicts = {item.question_id: item for item in scored}
    topics = _canonical_topics(questions, scored)
    weak_topics = [topic for topic, stat in topics.items() if stat.status == "weak"]
    summary = (
        "Focus your next study session on: " + ", ".join(weak_topics) + "."
        if weak_topics
        else "Strong result across the assessed topics. Keep practicing to retain the material."
    )
    return FeedbackReport(
        timestamp=datetime.now(timezone.utc).isoformat(),
        score=f"{sum(item.is_correct for item in scored)}/{len(scored)}",
        topics=topics,
        questions=[
            GradedQuestion(
                id=question.id,
                question_text=question.question_text,
                your_answer=_display_answer(verdicts[question.id].your_answer),
                correct_answer=_display_answer(question.correct_answer),
                is_correct=verdicts[question.id].is_correct,
                explanation="Correct." if verdicts[question.id].is_correct else f"The correct answer is: {question.correct_answer}.",
            )
            for question in questions
        ],
        weak_topics_summary=summary,
    )


def build_feedback(questions: list[Question], answers: dict[int, AnswerValue], scored: list[ScoredAnswer], document_text: str) -> FeedbackReport:
    verdicts = {item.question_id: item for item in scored}
    score = f"{sum(item.is_correct for item in scored)}/{len(questions)}"
    payload = {
        "questions": [question.model_dump() for question in questions],
        "answers": answers,
        "verdicts": [item.model_dump() for item in scored],
        "score": score,
    }
    prompt = f"""Create learner feedback from this deterministically scored attempt. Return one concise, source-grounded explanation for each supplied question ID, especially clarifying missed answers. Also return a weak-area summary based on the supplied verdicts. Do not introduce, omit, or renumber questions. The score, topic counts, answers, and correctness verdicts are calculated by the application and must not be returned.

Attempt data: {json.dumps(payload)}

Source material:
{document_text}"""

    errors: list[str] = []
    response: FeedbackNarrative | None = None
    for _ in range(2):
        try:
            raw_response = complete_json(
                prompt=prompt,
                response_model=FeedbackNarrative,
                schema_name="feedback_narrative",
                temperature=0.2,
                max_tokens=FEEDBACK_MAX_OUTPUT_TOKENS,
                reasoning_effort="low",
            )
            response = FeedbackNarrative.model_validate_json(raw_response)
            break
        except Exception as error:
            errors.append(f"{type(error).__name__}: {error}")
    if response is None:
        raise RuntimeError("Feedback generation failed after two Groq attempts. " + " | ".join(errors))

    generated = {item.id: item.explanation for item in response.questions}
    canonical_questions = [
        GradedQuestion(
            id=question.id,
            question_text=question.question_text,
            your_answer=_display_answer(verdicts[question.id].your_answer),
            correct_answer=_display_answer(question.correct_answer),
            is_correct=verdicts[question.id].is_correct,
            explanation=generated.get(question.id, "No explanation returned."),
        )
        for question in questions
    ]
    return FeedbackReport(
        timestamp=datetime.now(timezone.utc).isoformat(),
        score=score,
        topics=_canonical_topics(questions, scored),
        questions=canonical_questions,
        weak_topics_summary=response.weak_topics_summary,
    )
