"""
ai_provider.py - CampusAI Intelligence Provider Module
Supports:
1. LocalCampusEngine: Grounded Campus RAG & reasoning engine querying SQLite notices.
2. BedrockProvider: AWS Amazon Bedrock integration for cloud production deployments.
"""

import os
import re
import json
import logging
from datetime import datetime
from database import get_db_connection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("CampusAI")

# Common English stop words to ignore when matching query keywords against notices
STOP_WORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are",
    "aren't", "as", "at", "be", "because", "been", "before", "being", "below", "between", "both",
    "but", "by", "can", "can't", "cannot", "could", "couldn't", "did", "didn't", "do", "does",
    "doesn't", "doing", "don't", "down", "during", "each", "few", "for", "from", "further",
    "had", "hadn't", "has", "hasn't", "have", "haven't", "having", "he", "her", "here", "hers",
    "herself", "him", "himself", "his", "how", "i", "if", "in", "into", "is", "isn't", "it",
    "its", "itself", "let's", "me", "more", "most", "mustn't", "my", "myself", "no", "nor", "not",
    "of", "off", "on", "once", "only", "or", "other", "ought", "our", "ours", "ourselves", "out",
    "over", "own", "same", "she", "should", "shouldn't", "so", "some", "such", "than", "that",
    "the", "their", "theirs", "them", "themselves", "then", "there", "these", "they", "this",
    "those", "through", "to", "too", "under", "until", "up", "very", "was", "wasn't", "we",
    "were", "weren't", "what", "when", "where", "which", "while", "who", "whom", "why", "with",
    "won't", "would", "wouldn't", "you", "your", "yours", "yourself", "yourselves",
    "tell", "give", "show", "find", "get", "please", "know", "check", "see"
}


def word_match(pattern: str, text: str) -> bool:
    """Checks for whole-word case-insensitive match."""
    return bool(re.search(rf"\b{re.escape(pattern)}\b", text, re.IGNORECASE))


def any_word_match(patterns: list, text: str) -> bool:
    """Checks if any pattern matches as a whole word in text."""
    for p in patterns:
        if word_match(p, text):
            return True
    return False


class CampusAIProvider:
    """Base interface for CampusAI intelligence providers."""
    def ask(self, question: str) -> dict:
        raise NotImplementedError


class LocalCampusEngine(CampusAIProvider):
    """
    Intelligent campus data retrieval & reasoning engine (Local RAG).
    Operates on SQLite notices without requiring external paid API keys.
    Generates grounded, factual answers and strictly avoids hallucination.
    """

    def get_all_notices(self) -> list:
        try:
            conn = get_db_connection()
            rows = conn.execute("""
                SELECT
                    id,
                    title,
                    description,
                    department,
                    category,
                    year,
                    event_date,
                    deadline,
                    venue,
                    priority,
                    registration_url,
                    document_url,
                    created_at
                FROM notices
                ORDER BY id DESC
            """).fetchall()
            conn.close()
            return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"Error fetching notices for AI engine: {e}")
            return []

    def rank_notices(self, question: str, notices: list) -> tuple:
        """
        Ranks notices according to relevance to the question.
        Returns (ranked_notices, intents).
        """
        q_lower = question.lower().strip()
        # Extract meaningful alphanumeric words
        raw_words = re.findall(r"[a-z0-9\-]+", q_lower)
        query_keywords = [w for w in raw_words if len(w) > 1 and w not in STOP_WORDS]

        # Intent detection using whole-word matching
        is_greeting = any_word_match(["hi", "hello", "hey", "greetings", "help"], q_lower) or \
                      "what can you do" in q_lower or "who are you" in q_lower

        wants_all = any(p in q_lower for p in [
            "what notices", "all notices", "show notices", "list notices",
            "available notices", "any notices", "all announcements", "overview"
        ])

        wants_deadlines = any_word_match(["deadline", "deadlines", "due"], q_lower) or \
                          any(p in q_lower for p in ["due date", "last date", "submission date", "when to apply"])

        wants_events = any_word_match([
            "event", "events", "workshop", "workshops", "hackathon", "hackathons",
            "seminar", "seminars", "webinar", "webinars", "bootcamp", "competition", "fest"
        ], q_lower)

        wants_exams = any_word_match([
            "exam", "exams", "examination", "examinations", "mid-sem", "midsem", "cce", "timetable", "schedule"
        ], q_lower) or "mid semester" in q_lower

        wants_placements = any_word_match([
            "placement", "placements", "job", "jobs", "internship", "internships", "career", "interview", "recruitment"
        ], q_lower)

        wants_scholarships = any_word_match([
            "scholarship", "scholarships", "fee", "grant"
        ], q_lower) or "financial aid" in q_lower

        wants_latest = any_word_match([
            "latest", "new", "newest", "recent"
        ], q_lower) or "campus announcement" in q_lower or "announcements" in q_lower

        wants_registration = any_word_match(["register", "registration", "apply", "signup"], q_lower) or \
                             "how to register" in q_lower or "how do i register" in q_lower

        # Department detection
        target_depts = []
        if any(d in q_lower for d in ["computer science", "computer", "cse"]):
            target_depts.extend(["computer", "computer science", "all departments"])
        if any(d in q_lower for d in ["artificial intelligence", "ai", "aiml"]):
            target_depts.extend(["artificial intelligence", "ai", "all departments"])
        if "data science" in q_lower:
            target_depts.extend(["data science", "all departments"])
        if any_word_match(["mechanical", "mech"], q_lower):
            target_depts.extend(["mechanical", "all departments"])
        if any_word_match(["civil"], q_lower):
            target_depts.extend(["civil", "all departments"])
        if any_word_match(["electrical", "electronics", "ece", "eee"], q_lower):
            target_depts.extend(["electrical", "electronics", "all departments"])

        scored = []
        for n in notices:
            score = 0
            title = (n.get("title") or "").lower()
            desc = (n.get("description") or "").lower()
            dept = (n.get("department") or "").lower()
            cat = (n.get("category") or "").lower()
            venue = (n.get("venue") or "").lower()
            deadline = n.get("deadline") or ""
            event_date = n.get("event_date") or ""

            # Check for direct phrase match in title (e.g. "dynamic notice test", "aws cloud workshop", "cce timetable")
            # If query phrase matches title or vice versa
            matched_keywords = 0
            for kw in query_keywords:
                kw_matched = False
                if word_match(kw, title):
                    score += 6
                    kw_matched = True
                elif kw in title:
                    score += 3
                    kw_matched = True

                if word_match(kw, desc):
                    score += 2.5
                    kw_matched = True
                elif kw in desc:
                    score += 1
                    kw_matched = True

                if word_match(kw, cat):
                    score += 4
                    kw_matched = True

                if word_match(kw, dept):
                    score += 3
                    kw_matched = True

                if word_match(kw, venue):
                    score += 2
                    kw_matched = True

                if kw_matched:
                    matched_keywords += 1

            # Exact multi-word phrase matching
            clean_phrase = " ".join(query_keywords)
            if clean_phrase and (clean_phrase in title or title in clean_phrase):
                score += 15

            # If user asked for general notices, all notices, or latest announcements
            if wants_all:
                score += 5
            elif wants_latest:
                score += 8

            # Category boost only if relevant keywords or category match
            if cat:
                if wants_exams and cat in ["examination", "academic"]:
                    score += 3 if matched_keywords > 0 or wants_exams else 0
                if wants_events and cat in ["workshop", "event", "hackathon"]:
                    score += 4
                if wants_placements and cat in ["placement", "career"]:
                    score += 4
                if wants_scholarships and cat in ["scholarship", "financial"]:
                    score += 4

            # Department matching boost
            if target_depts:
                if any(td in dept for td in target_depts):
                    score += 5
                elif dept in ["all departments", "all"]:
                    score += 2

            # Deadlines & Dates boost
            if wants_deadlines and deadline and deadline not in ["—", "-", "None"]:
                score += 4

            # Registration boost
            if wants_registration and n.get("registration_url"):
                score += 5

            # Require at least one matched keyword if user asked a specific non-generic question
            if query_keywords and not (wants_all or wants_latest or wants_deadlines or wants_exams or wants_events):
                if matched_keywords == 0:
                    score = 0

            if score > 0:
                scored.append((score, n))

        # Sort by score descending, then by id descending
        scored.sort(key=lambda item: (item[0], item[1].get("id", 0)), reverse=True)
        ranked = [item[1] for item in scored]

        intents = {
            "is_greeting": is_greeting,
            "wants_all": wants_all,
            "wants_deadlines": wants_deadlines,
            "wants_events": wants_events,
            "wants_exams": wants_exams,
            "wants_placements": wants_placements,
            "wants_scholarships": wants_scholarships,
            "wants_latest": wants_latest,
            "wants_registration": wants_registration,
            "target_depts": target_depts,
            "has_keywords": len(query_keywords) > 0
        }

        return ranked, intents

    def ask(self, question: str) -> dict:
        q_clean = question.strip()
        notices = self.get_all_notices()
        ranked, intents = self.rank_notices(q_clean, notices)

        # Handle greetings or general capability questions
        if intents["is_greeting"] and not ranked:
            return {
                "answer": (
                    "👋 <strong>Hello! I am CampusAI Intelligence</strong>, your automated campus assistant.<br><br>"
                    "I can answer questions about real campus announcements, deadlines, examinations, and events directly from the campus database. "
                    "Try asking me questions such as:<ul>"
                    "<li><em>'What notices are available?'</em></li>"
                    "<li><em>'When is the next examination?'</em></li>"
                    "<li><em>'Show me upcoming workshops.'</em></li>"
                    "<li><em>'What events are available for Computer Science students?'</em></li>"
                    "<li><em>'Tell me about upcoming deadlines.'</em></li>"
                    "<li><em>'How do I register for an event?'</em></li>"
                    "<li><em>'What is the latest campus announcement?'</em></li>"
                    "</ul>"
                ),
                "sources": [],
                "provider": "LocalCampusEngine (Campus RAG Engine)"
            }

        # If no matching notices found in database
        if not ranked:
            return {
                "answer": (
                    f"I searched all active campus notices and database records, but found no announcements or events matching "
                    f"<strong>'{q_clean}'</strong>.<br><br>"
                    "<em>Tip: Try checking your department notice board or rephrasing your question with keywords such as 'workshop', 'exam', 'timetable', or 'deadline'.</em>"
                ),
                "sources": [],
                "provider": "LocalCampusEngine (Campus RAG Engine)"
            }

        # User asked for all notices or latest announcements without specific category filter
        if intents["wants_all"] or (intents["wants_latest"] and not intents["wants_exams"] and not intents["wants_events"]):
            if intents["wants_latest"]:
                selected = ranked[:2]
                lines = [f"Here is the latest campus announcement published in the database:<br>"]
            else:
                selected = ranked[:5]
                lines = [f"I found <strong>{len(selected)}</strong> campus notice(s) currently published in the database:<br>"]
            for n in selected:
                lines.append(self._format_notice_card(n))
            return {
                "answer": "<br>".join(lines),
                "sources": selected,
                "provider": "LocalCampusEngine (Campus RAG Engine)"
            }

        # User asked specifically about deadlines
        if intents["wants_deadlines"]:
            with_deadline = [n for n in ranked if n.get("deadline") and n.get("deadline") not in ["—", "-", "None"]]
            selected = with_deadline if with_deadline else ranked[:3]
            lines = ["Here are the upcoming deadlines found in campus notices:<br>"]
            for n in selected:
                d_str = n.get("deadline") or "Not specified"
                lines.append(self._format_notice_card(n, highlight_field=f"⏰ <strong>Deadline:</strong> {d_str}"))
            return {
                "answer": "<br>".join(lines),
                "sources": selected,
                "provider": "LocalCampusEngine (Campus RAG Engine)"
            }

        # User asked specifically about examinations / timetables
        if intents["wants_exams"]:
            selected = ranked[:4]
            lines = ["Here are the examination and academic schedule details found in the campus records:<br>"]
            for n in selected:
                extra = []
                if n.get("event_date"):
                    extra.append(f"📅 Date: {n['event_date']}")
                if n.get("venue"):
                    extra.append(f"📍 Venue: {n['venue']}")
                highlight = " | ".join(extra) if extra else None
                lines.append(self._format_notice_card(n, highlight_field=highlight))
            return {
                "answer": "<br>".join(lines),
                "sources": selected,
                "provider": "LocalCampusEngine (Campus RAG Engine)"
            }

        # User asked how to register for an event
        if intents["wants_registration"]:
            with_reg = [n for n in ranked if n.get("registration_url")]
            selected = with_reg if with_reg else ranked[:3]
            lines = ["To register for campus events, use the official registration links provided in each notice:<br>"]
            for n in selected:
                reg_url = n.get("registration_url")
                highlight = f"🔗 <a href='{reg_url}' target='_blank' style='color:var(--primary);font-weight:700'>Click here to register ↗</a>" if reg_url else "<em>No online registration link provided in this notice.</em>"
                lines.append(self._format_notice_card(n, highlight_field=highlight))
            return {
                "answer": "<br>".join(lines),
                "sources": selected,
                "provider": "LocalCampusEngine (Campus RAG Engine)"
            }

        # Standard relevant notices response
        selected = ranked[:4]
        lines = [f"I found <strong>{len(selected)}</strong> campus notice(s) matching your request:<br>"]
        for n in selected:
            lines.append(self._format_notice_card(n))

        return {
            "answer": "<br>".join(lines),
            "sources": selected,
            "provider": "LocalCampusEngine (Campus RAG Engine)"
        }

    def _format_notice_card(self, n: dict, highlight_field: str = None) -> str:
        nid = n.get("id")
        title = n.get("title", "Untitled")
        dept = n.get("department") or "All Departments"
        cat = n.get("category") or "General"
        desc = n.get("description") or ""
        event_date = n.get("event_date")
        deadline = n.get("deadline")
        venue = n.get("venue")
        reg_url = n.get("registration_url")

        meta_parts = [f"<strong>{cat}</strong>", f"Dept: {dept}"]
        if event_date and event_date not in ["—", "-", "None"]:
            meta_parts.append(f"📅 {event_date}")
        if deadline and deadline not in ["—", "-", "None"]:
            meta_parts.append(f"⏰ Deadline: {deadline}")
        if venue and venue not in ["—", "-", "None"]:
            meta_parts.append(f"📍 {venue}")

        meta_line = " • ".join(meta_parts)

        card_html = (
            f"<div style='background:rgba(248,250,252,0.9);border:1px solid var(--border);border-radius:10px;padding:12px;margin:8px 0;'>"
            f"<div style='font-size:14px;font-weight:700;color:var(--text);margin-bottom:4px;'>"
            f"<a href='#detail-{nid}' style='color:var(--primary);text-decoration:none;'>{title}</a>"
            f"</div>"
            f"<div style='font-size:11px;color:#64748b;margin-bottom:6px;'>{meta_line}</div>"
            f"<div style='font-size:12px;color:#334155;line-height:1.5;'>{desc}</div>"
        )

        if highlight_field:
            card_html += f"<div style='margin-top:6px;font-size:12px;'>{highlight_field}</div>"

        if reg_url and not highlight_field:
            card_html += f"<div style='margin-top:6px;font-size:12px;'>🔗 <a href='{reg_url}' target='_blank' style='color:var(--primary);font-weight:600;'>Register Online ↗</a></div>"

        card_html += (
            f"<div style='margin-top:8px;'>"
            f"<a href='#detail-{nid}' style='font-size:12px;font-weight:600;color:var(--primary);text-decoration:none;'>View Full Notice →</a>"
            f"</div>"
            f"</div>"
        )
        return card_html


class BedrockProvider(CampusAIProvider):
    """
    AWS Amazon Bedrock AI Provider for Production Cloud Deployments.
    Integrates Claude 3 / Titan via boto3 and bedrock-runtime client.
    Safely falls back to LocalCampusEngine if AWS credentials or dependencies are absent.
    """

    def __init__(self):
        self.fallback = LocalCampusEngine()
        self.client = None
        self.model_id = os.environ.get("AWS_BEDROCK_MODEL_ID", "anthropic.claude-3-haiku-20240307-v1:0")
        self.region = os.environ.get("AWS_REGION", os.environ.get("AWS_DEFAULT_REGION", "us-east-1"))

        try:
            import boto3
            self.client = boto3.client("bedrock-runtime", region_name=self.region)
            logger.info(f"Initialized Amazon Bedrock client in region {self.region} with model {self.model_id}")
        except Exception as e:
            logger.warning(f"Amazon Bedrock not configured or boto3 unavailable ({e}). Defaulting to LocalCampusEngine.")
            self.client = None

    def ask(self, question: str) -> dict:
        if not self.client:
            return self.fallback.ask(question)

        try:
            notices = self.fallback.get_all_notices()
            ranked, _ = self.fallback.rank_notices(question, notices)
            context_notices = ranked[:6] if ranked else notices[:6]

            context_str = json.dumps(context_notices, indent=2)
            prompt = (
                f"You are CampusAI, the official campus intelligence assistant for students, faculty, and administrators.\n"
                f"Answer the user's question truthfully using ONLY the provided campus notices context below.\n"
                f"If the question cannot be answered from the provided context, state clearly that no matching campus announcements were found.\n"
                f"Do NOT fabricate notices, dates, or contact information.\n\n"
                f"--- CAMPUS NOTICES CONTEXT ---\n{context_str}\n\n"
                f"--- USER QUESTION ---\n{question}\n"
            )

            response = self.client.converse(
                modelId=self.model_id,
                messages=[{"role": "user", "content": [{"text": prompt}]}]
            )
            output_text = response['output']['message']['content'][0]['text']

            return {
                "answer": output_text,
                "sources": context_notices,
                "provider": f"Amazon Bedrock ({self.model_id})"
            }
        except Exception as e:
            logger.warning(f"Bedrock invocation failed ({e}), falling back to LocalCampusEngine.")
            result = self.fallback.ask(question)
            result["provider"] = "LocalCampusEngine (Bedrock Fallback)"
            return result


def get_ai_provider() -> CampusAIProvider:
    """Returns configured AI provider based on environment variables."""
    use_bedrock = os.environ.get("AWS_BEDROCK_ENABLED", "").lower() in ["true", "1", "yes"]
    if use_bedrock:
        return BedrockProvider()
    return LocalCampusEngine()


def ask_campus_ai(question: str) -> dict:
    """Convenience helper to ask CampusAI."""
    provider = get_ai_provider()
    return provider.ask(question)
