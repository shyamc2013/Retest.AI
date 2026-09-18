"""Pydantic contracts for structured responses and local scoring."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator


QuestionType = Literal["mcq_single", "mcq_multiple", "true_false", "fill_blank"]
AnswerValue = str | list[str]


class Question(BaseModel):
    id: int
    type: QuestionType
    topic: str
    difficulty: Literal["easy", "medium", "hard"]
    question_text: str
    options: list[str] = Field(default_factory=list)
    correct_answer: AnswerValue

    @model_validator(mode="after")
    def validate_options(self) -> "Question":
        # Normalize minor shape mismatches from the model (e.g. a single-item list
        # for mcq_single, or a bare string for mcq_multiple) instead of failing the
        # whole generation over them; only reject answers with no usable content.
        if self.type == "mcq_single":
            if isinstance(self.correct_answer, list):
                if not self.correct_answer:
                    raise ValueError("mcq_single requires a correct answer")
                self.correct_answer = self.correct_answer[0]
            if len(self.options) < 2:
                raise ValueError("mcq_single requires at least two options")
        elif self.type == "mcq_multiple":
            if isinstance(self.correct_answer, str):
                self.correct_answer = [self.correct_answer]
            if len(self.options) < 2 or not self.correct_answer:
                raise ValueError("mcq_multiple requires options and at least one correct answer")
        else:
            if isinstance(self.correct_answer, list):
                self.correct_answer = self.correct_answer[0] if self.correct_answer else ""
            self.options = []
        return self


class QuestionSet(BaseModel):
    """Object wrapper required by providers that disallow array root schemas."""

    questions: list["QuestionDraft"]


class QuestionDraft(BaseModel):
    """Provider-facing question shape that tolerates JSON booleans for true/false."""

    id: int
    type: QuestionType
    topic: str
    difficulty: Literal["easy", "medium", "hard"]
    question_text: str
    options: list[str] = Field(default_factory=list)
    correct_answer: str | list[str] | bool

    def to_question(self) -> Question:
        answer: AnswerValue = self.correct_answer if isinstance(self.correct_answer, list) else str(self.correct_answer)
        if self.type == "true_false":
            normalized = answer.strip().casefold() if isinstance(answer, str) else ""
            if normalized in {"true", "false"}:
                answer = normalized.capitalize()
        return Question(
            id=self.id,
            type=self.type,
            topic=self.topic,
            difficulty=self.difficulty,
            question_text=self.question_text,
            options=self.options,
            correct_answer=answer,
        )


class TopicStat(BaseModel):
    correct: int
    total: int
    status: Literal["weak", "strong"]


class GradedQuestion(BaseModel):
    id: int
    question_text: str
    your_answer: str
    correct_answer: str
    is_correct: bool
    explanation: str


class FeedbackReport(BaseModel):
    timestamp: str
    score: str
    topics: dict[str, TopicStat]
    questions: list[GradedQuestion]
    weak_topics_summary: str


class FeedbackExplanation(BaseModel):
    """Narrative-only model output; topic statistics are calculated locally."""

    id: int
    explanation: str


class FeedbackNarrative(BaseModel):
    """The portion of feedback that requires the model's source-grounded reasoning."""

    questions: list[FeedbackExplanation]
    weak_topics_summary: str


class ScoredAnswer(BaseModel):
    question_id: int
    your_answer: AnswerValue
    is_correct: bool
