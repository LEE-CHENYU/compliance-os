"""Case templates for active target search.

Each template defines the document slots a complete case package should have.
The matcher scans a local folder and reports which slots are filled, missing,
misplaced, or have lineage ordering problems.
"""

from compliance_os.case_templates.schema import Slot, Template
from compliance_os.case_templates.h1b import H1B_TEMPLATE
from compliance_os.case_templates.matcher import match_folder, format_report

__all__ = ["Slot", "Template", "H1B_TEMPLATE", "match_folder", "format_report"]
