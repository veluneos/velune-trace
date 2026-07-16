"""Versioned presentation policy for comparison Markdown outputs."""

PRESENTATION_POLICY_VERSION = "0.1.0"

MARKDOWN_CHANGED_TOPIC_PREVIEW_LIMIT = 5
MARKDOWN_CHANGED_TOPIC_DETAIL_LIMIT = 20

HUMAN_JUDGMENT_BOUNDARY_STATEMENT = (
    "Velune reports observable differences between the Reference Bundle "
    "and Target Bundle. Engineers determine their meaning and cause."
)

HUMAN_JUDGMENT_BOUNDARY_DETAIL = (
    "This report does not determine root cause, fault, liability, safety, "
    "severity, normality, superiority, regression, or improvement."
)

HUMAN_COMPLETE_DETAIL_NOTICE = (
    "Complete machine-readable comparison details remain available in "
    "comparison_report.json."
)
