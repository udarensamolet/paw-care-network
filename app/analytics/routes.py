import importlib
import json
from collections import Counter
from datetime import datetime

from flask import Blueprint, render_template
from flask_login import current_user, login_required

from ..models.assignment import CareAssignment
from ..models.care import CareRequest

analytics_bp = Blueprint("analytics", __name__, template_folder="../templates")

try:
    px = importlib.import_module("plotly.express") 
    PlotlyJSONEncoder = importlib.import_module("plotly.utils").PlotlyJSONEncoder  
    _HAS_PLOTLY = True
except Exception:
    px = None
    PlotlyJSONEncoder = None
    _HAS_PLOTLY = False


def _month_key(dt: datetime) -> str:
    return dt.strftime("%Y-%m")


def _last_n_months_labels(n: int = 6) -> list[str]:
    base = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    months = []
    for i in range(n - 1, -1, -1):
        y = base.year
        m = base.month - i
        while m <= 0:
            m += 12
            y -= 1
        months.append(f"{y:04d}-{m:02d}")
    return months


@analytics_bp.get("/analytics")
@login_required
def overview():
    my_reqs = CareRequest.query.filter_by(owner_id=current_user.id).all()

    by_status = Counter([(r.status or "unknown") for r in my_reqs])
    status_labels = list(by_status.keys()) or ["no data"]
    status_values = list(by_status.values()) or [1]

    months = _last_n_months_labels(6)
    monthly_counts = {m: 0 for m in months}
    for r in my_reqs:
        if r.start_at:
            k = _month_key(r.start_at)
            if k in monthly_counts:
                monthly_counts[k] += 1
    months_x = list(monthly_counts.keys())
    months_y = list(monthly_counts.values())

    my_assignments = CareAssignment.query.filter(
        CareAssignment.sitter_id == current_user.id,
        CareAssignment.status.in_(["pending", "active", "done"]),
    ).all()

    sitter_hours = {m: 0.0 for m in months}
    for a in my_assignments:
        if not a.start_at or not a.end_at:
            continue
        dur_h = (a.end_at - a.start_at).total_seconds() / 3600.0
        if dur_h <= 0:
            continue
        k = _month_key(a.start_at)
        if k in sitter_hours:
            sitter_hours[k] += round(dur_h, 2)

    sitter_x = list(sitter_hours.keys())
    sitter_y = list(sitter_hours.values())

    def dumps_obj(obj) -> str:
        if _HAS_PLOTLY and PlotlyJSONEncoder is not None:
            return json.dumps(obj, cls=PlotlyJSONEncoder, allow_nan=False)
        return json.dumps(obj, allow_nan=False)

    if _HAS_PLOTLY and px is not None:
        fig_status = px.pie(
            names=status_labels,
            values=status_values,
            hole=0.4,
            title="Your care requests by status",
        )
        fig_status.update_traces(textposition="inside", textinfo="percent+label")

        fig_reqs = px.bar(
            x=months_x,
            y=months_y,
            title="Requests per month (last 6 months)",
            labels={"x": "Month", "y": "Requests"},
        )

        fig_hours = px.bar(
            x=sitter_x,
            y=sitter_y,
            title="Your sitter hours per month (last 6 months)",
            labels={"x": "Month", "y": "Hours"},
        )

        status_json = dumps_obj(fig_status)
        requests_json = dumps_obj(fig_reqs)
        hours_json = dumps_obj(fig_hours)
    else:
        status_json = dumps_obj(
            {
                "data": [
                    {
                        "type": "pie",
                        "labels": status_labels,
                        "values": status_values,
                        "hole": 0.4,
                        "textinfo": "percent+label",
                        "textposition": "inside",
                    }
                ],
                "layout": {"title": "Your care requests by status"},
            }
        )
        requests_json = dumps_obj(
            {
                "data": [{"type": "bar", "x": months_x, "y": months_y}],
                "layout": {
                    "title": "Requests per month (last 6 months)",
                    "xaxis": {"title": "Month"},
                    "yaxis": {"title": "Requests"},
                },
            }
        )
        hours_json = dumps_obj(
            {
                "data": [{"type": "bar", "x": sitter_x, "y": sitter_y}],
                "layout": {
                    "title": "Your sitter hours per month (last 6 months)",
                    "xaxis": {"title": "Month"},
                    "yaxis": {"title": "Hours"},
                },
            }
        )

    return render_template(
        "analytics.html",
        status_json=status_json,
        requests_json=requests_json,
        hours_json=hours_json,
    )
