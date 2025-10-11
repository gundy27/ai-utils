"""Lead signal detection for portfolio chatbot."""

import re
import structlog
from typing import Dict, Any, List

logger = structlog.get_logger(__name__)

# Keywords that indicate hiring/recruiting interest
HIRING_KEYWORDS = [
    "hire",
    "hiring",
    "recruit",
    "position",
    "role",
    "job",
    "opportunity",
    "opening",
    "candidate",
    "interview",
    "team",
    "onboard",
    "salary",
    "compensation",
    "benefits",
    "start date",
    "available",
    "availability",
    "full-time",
    "part-time",
    "contract",
    "contractor",
    "freelance",
]

# Keywords that indicate technical depth/interest
TECHNICAL_KEYWORDS = [
    "architecture",
    "system design",
    "scalability",
    "performance",
    "database",
    "api",
    "backend",
    "frontend",
    "infrastructure",
    "deploy",
    "devops",
    "ci/cd",
    "testing",
    "security",
    "python",
    "typescript",
    "react",
    "docker",
    "kubernetes",
    "aws",
    "gcp",
    "azure",
    "microservices",
    "monolith",
]

# Keywords that indicate experience interest
EXPERIENCE_KEYWORDS = [
    "experience",
    "worked on",
    "built",
    "shipped",
    "delivered",
    "led",
    "managed",
    "designed",
    "implemented",
    "solved",
    "challenge",
    "problem",
    "project",
    "portfolio",
    "case study",
]


def detect_interest_signal(
    message: str,
    conversation_history: List[Dict[str, Any]],
    context_used: List[str],
) -> Dict[str, Any]:
    """Detect if user is showing high-interest signals for lead capture.

    This function analyzes the current message and conversation history to determine
    if the user is showing strong interest signals that warrant lead capture.

    Signals considered:
    - Hiring/recruiting keywords in messages
    - Technical deep-dive questions (3+ technical keywords)
    - Experience questions (3+ times)
    - High engagement (5+ messages)
    - Questions about availability or next steps

    Args:
        message: Current user message
        conversation_history: List of previous messages with role and content
        context_used: List of document chunks used in responses

    Returns:
        {
            "should_capture": bool,  # Whether to trigger lead capture
            "interest_level": "low" | "medium" | "high",
            "trigger": str,  # Reason for triggering
            "score": float,  # Confidence score (0-1)
        }
    """
    message_lower = message.lower()
    score = 0.0
    triggers = []

    # Count user messages (engagement level)
    user_message_count = sum(
        1 for msg in conversation_history if msg.get("role") == "user"
    )

    # Signal 1: Hiring/recruiting keywords (strong signal)
    hiring_matches = sum(1 for keyword in HIRING_KEYWORDS if keyword in message_lower)
    if hiring_matches > 0:
        score += 0.4
        triggers.append(f"hiring_keywords ({hiring_matches})")

    # Signal 2: Technical deep-dive questions
    technical_matches = sum(
        1 for keyword in TECHNICAL_KEYWORDS if keyword in message_lower
    )
    if technical_matches >= 3:
        score += 0.25
        triggers.append(f"technical_depth ({technical_matches})")
    elif technical_matches >= 1:
        score += 0.1

    # Signal 3: Experience/portfolio questions
    experience_matches = sum(
        1 for keyword in EXPERIENCE_KEYWORDS if keyword in message_lower
    )

    # Count how many times they've asked about experience across conversation
    total_experience_mentions = sum(
        sum(
            1
            for keyword in EXPERIENCE_KEYWORDS
            if keyword in msg.get("content", "").lower()
        )
        for msg in conversation_history
        if msg.get("role") == "user"
    )

    if total_experience_mentions >= 3:
        score += 0.2
        triggers.append(f"experience_interest ({total_experience_mentions})")
    elif experience_matches > 0:
        score += 0.1

    # Signal 4: High engagement (5+ messages)
    if user_message_count >= 5:
        score += 0.15
        triggers.append(f"high_engagement ({user_message_count} messages)")
    elif user_message_count >= 3:
        score += 0.05

    # Signal 5: Availability questions
    availability_patterns = [
        r"when.*available",
        r"start.*date",
        r"notice.*period",
        r"can.*start",
        r"available.*start",
        r"free.*to.*start",
    ]
    if any(re.search(pattern, message_lower) for pattern in availability_patterns):
        score += 0.3
        triggers.append("availability_inquiry")

    # Signal 6: Questions about compensation
    compensation_keywords = ["salary", "compensation", "pay", "rate", "benefits"]
    if any(keyword in message_lower for keyword in compensation_keywords):
        score += 0.25
        triggers.append("compensation_inquiry")

    # Signal 7: Request for more information
    info_patterns = [
        r"tell.*more.*about",
        r"can.*you.*share",
        r"would.*like.*to.*know",
        r"interested.*in.*learning",
        r"resume",
        r"cv",
    ]
    if any(re.search(pattern, message_lower) for pattern in info_patterns):
        score += 0.1
        triggers.append("info_request")

    # Determine interest level and capture decision
    if score >= 0.6:
        interest_level = "high"
        should_capture = True
        trigger_text = f"High interest detected: {', '.join(triggers)}"
    elif score >= 0.35:
        interest_level = "medium"
        should_capture = user_message_count >= 3  # Only capture if they're engaged
        trigger_text = f"Medium interest detected: {', '.join(triggers)}"
    else:
        interest_level = "low"
        should_capture = False
        trigger_text = f"Low interest: {', '.join(triggers) if triggers else 'exploratory conversation'}"

    logger.info(
        "lead_signal_detected",
        score=score,
        interest_level=interest_level,
        should_capture=should_capture,
        triggers=triggers,
        message_count=user_message_count,
    )

    return {
        "should_capture": should_capture,
        "interest_level": interest_level,
        "trigger": trigger_text,
        "score": score,
        "message_count": user_message_count,
    }
