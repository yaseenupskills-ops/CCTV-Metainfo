"""Compact summaries for analysis results.

`analysis.result` embeds every detected event, each carrying its own per-frame
metrics. A completed scene-change run over a long recording reaches hundreds of
kilobytes, which is appropriate for the detail endpoint but far too heavy to
ship in every row of a list.

`build_analysis_summary` reduces a result to the counts a list view actually
needs. It is the single definition of "summary" in the system: the audit log
records it as `details["result_summary"]` and the API returns it as `summary`,
so the two can never disagree.

The argument is typed as `Any` and read structurally rather than imported from
`app.models`, which lets `app.schemas` reuse this without an import cycle.
"""

from typing import Any

from app.core.enums import AnalysisType


def build_analysis_summary(analysis: Any) -> dict[str, Any] | None:
    """Return a compact summary of ``analysis``'s result.

    Returns None when there is no result yet — an analysis that is queued,
    still processing, or failed. Note that a zero count is therefore
    distinguishable from "not computed yet": a finished scene-change run with no
    scene changes yields ``{"events": 0}``, not None.
    """
    result = getattr(analysis, "result", None)
    if not result:
        return None

    if getattr(analysis, "analysis_type", None) is AnalysisType.SCENE_CHANGE:
        return {"events": len(result.get("events") or [])}
    return {"frames_sampled": result.get("frames_sampled")}
