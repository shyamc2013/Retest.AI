"""Stateful Streamlit interface for Retest.AI."""
from __future__ import annotations

from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from config import DOCS_DIR
from document_loader import load_combined_text
from feedback_store import save_feedback
from grading_agent import build_fallback_feedback, build_feedback, score_answers
from models import AnswerValue, Question
from question_generator import generate_questions

load_dotenv()
st.set_page_config(page_title="Retest.AI", page_icon="📝", layout="wide")


def _initialize_state() -> None:
    defaults = {"questions": None, "answers": {}, "feedback": None, "generation_error": None, "feedback_notice": None}
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def _new_test() -> None:
    try:
        with st.spinner("Reading your sources and building a fresh test…"):
            text = load_combined_text()
            questions = generate_questions(text)
        st.session_state.questions = questions
        st.session_state.answers = {}
        st.session_state.feedback = None
        st.session_state.feedback_notice = None
        st.session_state.generation_error = None
        # Widget state outlives a rerun, so remove the previous test's answers too.
        for key in list(st.session_state):
            if key.startswith("answer_"):
                del st.session_state[key]
    except Exception as error:
        st.session_state.generation_error = str(error)


def _answer_key(question: Question) -> str:
    return f"answer_{question.id}"


_initialize_state()

st.title("Retest.AI")
st.caption("Generate source-grounded practice tests, learn from feedback, and target weak areas next time.")

with st.sidebar:
    st.header("Test controls")
    if st.button("Generate Test" if st.session_state.questions is None else "Retake Test", use_container_width=True):
        _new_test()
        st.rerun()
    st.caption(f"Source folder: `{Path(DOCS_DIR).name}/`")

if st.session_state.generation_error:
    st.error(st.session_state.generation_error)

questions: list[Question] | None = st.session_state.questions
if questions is None:
    st.info("Add your PDF, DOCX, and/or PPTX learning materials to `docs/`, then choose **Generate Test**.")
    st.stop()

if st.session_state.feedback is not None:
    report = st.session_state.feedback
    if st.session_state.feedback_notice:
        st.warning(st.session_state.feedback_notice)
    st.success(f"Score: {report.score}")
    st.subheader("Weak-area summary")
    st.write(report.weak_topics_summary)
    st.subheader("Question feedback")
    for item in report.questions:
        icon = "✅" if item.is_correct else "❌"
        with st.expander(f"{icon} Question {item.id}", expanded=not item.is_correct):
            st.write(item.question_text)
            st.write(f"**Your answer:** {item.your_answer or 'No answer'}")
            st.write(f"**Correct answer:** {item.correct_answer}")
            st.write(item.explanation)
    st.stop()

st.write("Answer every question, then submit once at the bottom.")
with st.form("test_form", clear_on_submit=False):
    current_answers: dict[int, AnswerValue] = {}
    for question in questions:
        st.markdown(f"### {question.id}. {question.question_text}")
        key = _answer_key(question)
        prior = st.session_state.answers.get(question.id, [] if question.type == "mcq_multiple" else "")
        if question.type == "mcq_single":
            options = ["", *question.options]
            index = options.index(prior) if prior in options else 0
            value = st.radio("Choose one", options, index=index, key=key, format_func=lambda option: "Select an answer" if not option else option)
        elif question.type == "mcq_multiple":
            value = st.multiselect("Select all that apply", question.options, default=prior if isinstance(prior, list) else [], key=key)
        elif question.type == "true_false":
            options = ["", "True", "False"]
            index = options.index(prior) if prior in options else 0
            value = st.radio("Choose one", options, index=index, key=key, horizontal=True, format_func=lambda option: "Select an answer" if not option else option)
        else:
            value = st.text_input("Your answer", value=prior, key=key)
        current_answers[question.id] = value
        st.divider()
    submitted = st.form_submit_button("Submit Test", type="primary", use_container_width=True)

if submitted:
    st.session_state.answers = current_answers
    scoring = score_answers(questions, current_answers)
    try:
        with st.spinner("Scoring your answers and preparing feedback…"):
            document_text = load_combined_text()
            report = build_feedback(questions, current_answers, scoring, document_text)
            save_feedback(report)
        st.session_state.feedback = report
        st.rerun()
    except Exception as error:
        # A provider outage, quota limit, or malformed model response should never
        # strand a completed attempt. Deterministic scores remain authoritative.
        report = build_fallback_feedback(questions, scoring)
        save_feedback(report)
        st.session_state.feedback = report
        st.session_state.feedback_notice = (
            "Groq explanations were unavailable, so this attempt uses concise "
            f"deterministic feedback instead. Provider detail: {error}"
        )
        st.rerun()
