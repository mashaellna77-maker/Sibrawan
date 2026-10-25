# UI verification - 14 October 2026

The redesign changes presentation and UI-only upload/forecast handling. The executed notebook, managerial PDF/Markdown report, CSV, generator, model harness and evaluation artifacts are preserved. Automated regression checks compare their content with commit `4026b851e664354a133ad9eb5a9e144ede036dc9` (normalizing Git text line endings only; PDF bytes unchanged).

## Passed

- All seven sections render with no Streamlit exceptions; navigation, per-month capacities, zero/high capacity cases, persistence across sections, suggested questions, conversation history and reset.
- Actual in-app browser interaction: upload CSV, apply it, and verify forecasts update. A shifted copy of the dataset moves the forecast to February-April 2026; original evaluation remains clearly labeled.
- Actual browser rejects a CSV missing a month, shows a readable validation message, and retains the previously active valid data/forecasts. Original project data can be restored.
- Backend rejection cases: missing month, duplicate month, negative count, fractional count, too-short history, wrong columns. Uploading original data reproduces saved AutoETS forecasts.
- Actual capacity edit to 1000 for January persists in the assistant's numerical answer. Incident suggestion escalates entered credentials to the relevant team without asserting compromise.
- Mocked Gemini request includes numerical context, individual monthly capacities and safety instructions; no real API call was used.
- All seven sections visually reviewed in the actual browser; screenshots show overview, monthly/annual charts, forecasts, model table, capacity, conversation and data disclosure.
- Responsive mobile review at 390 x 844: no horizontal page overflow or card overflow; collapsed sidebar hidden completely; charts/legends do not overlap; columns stack in a narrow workspace.
- Laptop visual review at the actual 1191 x 668 viewport; also reviewed in the narrower 870-pixel in-app pane. Container queries respond to content width rather than only browser width.
- Fixed defects found during testing: capacities being removed after navigation, RTL sidebar positioning, white text on uploaded-file chips, stray collapsed sidebar content on mobile, legend overlap on narrow charts, red/orange default chat avatars, and bidirectional date ranges.

## Limits

- Live Gemini authentication/model availability has not been tested: no API key was provided. UI status distinguishes local readiness from a configured key, and never asserts a live connection before a request.
- A 1440-pixel simulated viewport produced a clipped/black screenshot in the in-app browser. Those images are not delivered; actual laptop/narrow-pane screenshots and the successful 390-pixel mobile screenshots are used instead.
- Native HTML upload was tested through the browser; AppTest does not expose a file-uploader setter, so automated tests validate backend files and active-upload state separately.
- Uploaded data are not subjected to the capstone's original eight-fold evaluation. The reference leaderboard/coverage must not be interpreted as evaluation of a new upload.

## Re-run

```powershell
python test_app.py
python verify_submission.py
streamlit run app.py
```

Screenshots are in `docs/ui-screenshots/`. Current app defaults to the original history and monthly capacities of 120, and runs without an API key.
