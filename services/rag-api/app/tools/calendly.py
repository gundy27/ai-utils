"""Calendly scheduling tool."""

from .base import Tool


def calendly_handler(args: dict) -> dict:
    """Handle Calendly scheduling requests.

    Args:
        args: Tool arguments with meeting_type

    Returns:
        Action result with Calendly link
    """
    meeting_type = args.get("meeting_type", "intro_call")

    # Map meeting types to Calendly event slugs
    # In production, these would come from config/env
    calendly_links = {
        "intro_call": "https://calendly.com/dan-gunderson/30min",
        "technical_interview": "https://calendly.com/dan-gunderson/60min",
        "coffee_chat": "https://calendly.com/dan-gunderson/15min",
    }

    url = calendly_links.get(meeting_type, calendly_links["intro_call"])

    return {
        "action": "link",
        "url": url,
        "text": f"Schedule a {meeting_type.replace('_', ' ')}",
        "meeting_type": meeting_type,
    }


CALENDLY_TOOL = Tool(
    name="schedule_meeting",
    description="Provide a scheduling link when the user wants to book a meeting, call, or interview with Dan. Use this when they ask about availability, setting up a time to talk, or scheduling an interview.",
    parameters={
        "type": "object",
        "properties": {
            "meeting_type": {
                "type": "string",
                "enum": ["intro_call", "technical_interview", "coffee_chat"],
                "description": "Type of meeting to schedule: intro_call for initial conversations, technical_interview for in-depth technical discussions, coffee_chat for informal brief conversations",
            }
        },
        "required": ["meeting_type"],
    },
    handler=calendly_handler,
)
