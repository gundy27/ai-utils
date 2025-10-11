"""Portfolio and project showcase tool."""

from .base import Tool


def portfolio_handler(args: dict) -> dict:
    """Handle portfolio and project requests.

    Args:
        args: Tool arguments with resource_type

    Returns:
        Action result with portfolio link
    """
    resource_type = args.get("resource_type", "portfolio")

    # Map resource types to links
    # In production, these would come from config/env
    resource_links = {
        "portfolio": {
            "url": "https://dangunderson.com/portfolio",
            "text": "View my portfolio",
        },
        "resume": {
            "url": "https://dangunderson.com/resume.pdf",
            "text": "Download my resume",
        },
        "projects": {
            "url": "https://github.com/dangunderson?tab=repositories",
            "text": "View my projects",
        },
        "case_studies": {
            "url": "https://dangunderson.com/case-studies",
            "text": "View case studies",
        },
    }

    resource_info = resource_links.get(resource_type, resource_links["portfolio"])

    return {
        "action": "link",
        "url": resource_info["url"],
        "text": resource_info["text"],
        "resource_type": resource_type,
    }


PORTFOLIO_TOOL = Tool(
    name="view_portfolio_resource",
    description="Provide links to Dan's portfolio, resume, projects, or case studies when the user wants to see examples of work, download resume, or explore specific projects.",
    parameters={
        "type": "object",
        "properties": {
            "resource_type": {
                "type": "string",
                "enum": ["portfolio", "resume", "projects", "case_studies"],
                "description": "Type of resource: portfolio for complete work showcase, resume for PDF download, projects for GitHub repositories, case_studies for detailed project breakdowns",
            }
        },
        "required": ["resource_type"],
    },
    handler=portfolio_handler,
)
