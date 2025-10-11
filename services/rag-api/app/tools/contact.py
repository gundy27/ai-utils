"""Contact information tool."""

from .base import Tool


def contact_handler(args: dict) -> dict:
    """Handle contact information requests.

    Args:
        args: Tool arguments with contact_method

    Returns:
        Action result with contact link
    """
    contact_method = args.get("contact_method", "email")

    # Map contact methods to links
    # In production, these would come from config/env
    contact_links = {
        "email": {
            "url": "mailto:dan@example.com",
            "text": "Send me an email",
        },
        "linkedin": {
            "url": "https://linkedin.com/in/dan-gunderson",
            "text": "Connect on LinkedIn",
        },
        "github": {
            "url": "https://github.com/dangunderson",
            "text": "View my GitHub",
        },
    }

    contact_info = contact_links.get(contact_method, contact_links["email"])

    return {
        "action": "link",
        "url": contact_info["url"],
        "text": contact_info["text"],
        "contact_method": contact_method,
    }


CONTACT_TOOL = Tool(
    name="get_contact_info",
    description="Provide Dan's contact information when the user wants to reach out via email, LinkedIn, or GitHub. Use this when they ask how to contact, get in touch, or connect with Dan.",
    parameters={
        "type": "object",
        "properties": {
            "contact_method": {
                "type": "string",
                "enum": ["email", "linkedin", "github"],
                "description": "Method to contact Dan: email for direct contact, linkedin for professional networking, github for technical collaboration",
            }
        },
        "required": ["contact_method"],
    },
    handler=contact_handler,
)
