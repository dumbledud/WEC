# WEC

## Minimal Working Version (MVP)

This streamlined WeCoin simulation app currently supports:

- Registering a user.
- Posting a PR.
- Viewing the current user balance.
- Writing each action to Google Sheets.

### Files

- `app.py`: Streamlit frontend with the three MVP flows.
- `sheet_manager.py`: Google Sheets integration for sheet setup, registration, PR posting, and balance lookup.

## Roadmap to Rebuild the Full Feature Set

### Phase 1: Stability and Caching

- Add concurrency handling and read caching for performance.
- Add error reporting with retry and backoff logic.

### Phase 2: Simulation Logic

- Add PR limits per day and EA logic.
- Add time-window constraints for a 24-hour period.
- Add hourly award logic with global caps and dynamic multipliers.

### Phase 3: Visualization

- Add real-time charts for PRs and EAs per hour.
- Add global cap usage percentage views.
- Add individual award graphs.

### Phase 4: Dev Controls and Simulation Overrides

- Create a developer backdoor panel such as a `Dev Tools` menu tab.
- Add controls to tweak cap, multiplier, award amounts, and behavior.

### Phase 5: Public Participation

- Add simulation of other users.
- Add a leaderboard.
- Add per-user encouragement features and PR/EA histories.

### Phase 6: Advanced Features

- Export or back up Google Sheet snapshots.
- Add webhooks or email notifications.
- Explore token bridging and off-chain to on-chain simulation in a later phase.
