import io
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from datetime import datetime
from sheet_manager import get_ledger_data

def generate_award_graph(mode="global", user_id=None):
    """
    mode = "global", "user", "pr", "ea"
    user_id used if mode="user".
    Returns raw PNG bytes.
    """
    rows = get_ledger_data()
    awarding_points = []
    for row in rows:
        if len(row) < 5:
            continue
        raw_ts, r_user, action_type, pr_or_ea_id, amt_str, notes = row
        if not amt_str:
            continue
        try:
            ts_dt = datetime.fromisoformat(raw_ts)
            amount = float(amt_str)
        except:
            continue

        # Filter logic
        if mode == "user" and user_id:
            if r_user != user_id:
                continue
        if mode == "pr":
            if action_type != "POST_PR":
                continue
        if mode == "ea":
            if action_type != "POST_EA":
                continue

        awarding_points.append((ts_dt, amount))

    # Group by day
    awarding_points.sort(key=lambda x: x[0])
    daily_sum = {}
    for (ts_dt, amt) in awarding_points:
        day_str = ts_dt.date().isoformat()
        daily_sum[day_str] = daily_sum.get(day_str, 0) + amt

    # Prepare plot
    x_vals = sorted(daily_sum.keys())
    y_vals = [daily_sum[x] for x in x_vals]

    fig, ax = plt.subplots()
    ax.plot(x_vals, y_vals, marker='o')
    ax.set_title(f"Awarding Over Time - Mode={mode}, user_id={user_id or 'ALL'}")
    ax.set_xlabel("Date")
    ax.set_ylabel("Sum of Awards")

    plt.xticks(rotation=45)
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format="png")
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()
