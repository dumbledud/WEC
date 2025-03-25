import time
from datetime import datetime
from sheet_manager import (
    get_user_data, update_user_data,
    append_ledger, get_simulation_data, update_simulation_data
)

# Developer-tweakable config
CONFIG = {
    "DAILY_USER_CAP": 10240,
    "MAX_DAILY_PRS": 3,
    "PR_AWARD": 10,
    "EA_AWARD_TIERS": [100, 90, 90, 80, 80, 80, 50, 50, 50, 40],
    "OVERRUN_BRACKET_STEP": 0.05,
    "HOURLY_2PCT_CAP": 1e14 / 8760.0,  # 2% of 5e15 spread over 8760 hours
    "DOUBLE_MULTIPLIER": 2.0,
    "HALVE_BASE": 1.0,
    "USE_HOUR_LOGIC": True,
    "SECRET_DEV_KEY": "mysecret123"
}

def dev_override(secret_key, new_params):
    """
    Developer override to modify up to 20 parameters in CONFIG, if key is correct.
    """
    if secret_key != CONFIG["SECRET_DEV_KEY"]:
        return (False, "Invalid secret key")
    updated_keys = []
    for k, v in new_params.items():
        if k in CONFIG:
            CONFIG[k] = v
            updated_keys.append(k)
    return (True, f"Updated: {', '.join(updated_keys)}")

def maybe_reset_daily(user_dict):
    """Resets daily counters if the date changed."""
    today_str = datetime.now().date().isoformat()
    if user_dict["last_daily_reset"] != today_str:
        user_dict["daily_earned"] = 0
        user_dict["daily_pr_count"] = 0
        user_dict["last_daily_reset"] = today_str

def register_user(user_id):
    """
    Ensures user exists in the sheet, logs a 'REGISTER' event.
    """
    user_data = get_user_data(user_id)
    append_ledger(user_id, "REGISTER", "N/A", 0, "User creation/exists")
    return f"User '{user_id}' is ready."

def post_pr(user_id):
    user_dict = get_user_data(user_id)
    maybe_reset_daily(user_dict)

    if user_dict["daily_pr_count"] >= CONFIG["MAX_DAILY_PRS"]:
        return f"Daily PR limit of {CONFIG['MAX_DAILY_PRS']} reached."

    final_award = compute_award(user_dict, CONFIG["PR_AWARD"])
    user_dict["daily_pr_count"] += 1

    update_user_data(user_dict)
    append_ledger(user_id, "POST_PR", "N/A", final_award, "User posted PR")

    return f"PR posted. Awarded {final_award} WeCoin."

def post_ea(user_id):
    user_dict = get_user_data(user_id)
    maybe_reset_daily(user_dict)

    # We'll pick the first EA tier for demonstration, though a real system might track how many EAs used
    base_award = CONFIG["EA_AWARD_TIERS"][0]
    final_award = compute_award(user_dict, base_award)

    update_user_data(user_dict)
    append_ledger(user_id, "POST_EA", "N/A", final_award, "User posted EA")

    return f"EA posted. Awarded {final_award} WeCoin."

def view_wallet(user_id):
    user_dict = get_user_data(user_id)
    maybe_reset_daily(user_dict)
    update_user_data(user_dict)
    return (
        f"Balance={user_dict['balance']} | "
        f"Daily Earned={user_dict['daily_earned']} | "
        f"Total Ever={user_dict['total_earned_ever']}"
    )

def compute_award(user_dict, base_amount):
    """
    If USE_HOUR_LOGIC is True, apply overrun/underrun multipliers. Otherwise, do a simple daily cap approach.
    """
    if not CONFIG["USE_HOUR_LOGIC"]:
        return apply_daily_cap(user_dict, base_amount)

    # Hour-based logic:
    sim_data = get_simulation_data()
    ratio = sim_data["hour_awarding_so_far"] / CONFIG["HOURLY_2PCT_CAP"]
    if ratio >= 1.0:
        # Overrun - halving brackets
        bracket_count = int((ratio - 1.0) // CONFIG["OVERRUN_BRACKET_STEP"]) + 1
        new_mult = CONFIG["HALVE_BASE"] / (2 ** bracket_count)
        sim_data["current_multiplier"] = new_mult
    else:
        # Underrun - if awarding < half by half hour => double
        fraction_of_hour = get_fraction_of_hour(sim_data["hour_index"])
        if fraction_of_hour >= 0.5:
            half_cap = 0.5 * CONFIG["HOURLY_2PCT_CAP"]
            if sim_data["hour_awarding_so_far"] < half_cap:
                sim_data["current_multiplier"] = CONFIG["DOUBLE_MULTIPLIER"]
            else:
                sim_data["current_multiplier"] = CONFIG["HALVE_BASE"]

    final = apply_daily_cap(user_dict, base_amount * sim_data["current_multiplier"])
    sim_data["hour_awarding_so_far"] += final
    update_simulation_data(sim_data)
    return final

def apply_daily_cap(user_dict, amt):
    if user_dict["daily_earned"] >= CONFIG["DAILY_USER_CAP"]:
        return 0
    allowable = CONFIG["DAILY_USER_CAP"] - user_dict["daily_earned"]
    final = min(amt, allowable)
    user_dict["balance"] += final
    user_dict["daily_earned"] += final
    user_dict["total_earned_ever"] += final
    return final

def get_fraction_of_hour(hour_index):
    """
    Very naive approach - no hour_start_time. We just measure local time-of-day fraction.
    """
    second_of_day = int(time.time()) % 86400
    minute_in_hour = second_of_day % 3600
    fraction = minute_in_hour / 3600.0
    return fraction
