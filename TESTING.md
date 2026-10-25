# Verification - 14 October 2026

Executed locally with Python 3.12 on Windows. Full environment versions are in `requirements-tested.txt`.

| Check | Result |
|---|---|
| Clean-kernel `python run_notebook.py` | Passed, complete notebook saved with outputs; latest run 29.51 seconds excluding installation |
| Frozen generator equality and CSV integrity | Passed: 72 consecutive monthly rows, integer nonnegative counts, no gaps/duplicates/nulls |
| Eight quarterly expanding origins | Passed: 48,51,54,57,60,63,66,69 training rows; 24 unique 2024-2025 test months |
| Five models with identical test dates | Passed; no hidden replacement/fallback |
| Seasonal training-only scaling | Independently recomputed and matched for every model/fold |
| MASE | Independently compared against utilsforecast MASE for every model/fold |
| Approximate scaled CRPS | Independent explicit trapezoid sums matched all saved scores |
| 80% coverage and mean width | Independently recomputed for every model/fold |
| Quantile ordering and finiteness | Passed all five models and all outer folds |
| Zero denominator guard | Passed: constant-series scaling raises a clear error |
| Notebook completeness | All code cells executed, no error outputs or TODO code |
| Final forecast dates | Passed: January-March 2026, following December 2025 |
| Report | Exactly 3 PDF pages; all three rendered and visually inspected for clipping/overlap/legibility |
| Streamlit AppTest | Passed startup, capacity 0 and 1000, incident-state selection and local calculated response |
| Gemini request contract | Mocked response passed; headers/system context parsed without making a live request |
| Secrets/ignored paths | `.env`, virtual environments and runtime caches ignored; no real keys used |
| README attribution and rubric mapping | Passed; all A-E criteria mapped to actual cells/files |

## Honest limits

- Actual Colab execution has not been performed here; the Colab setup cell points to this fork and installs documented dependencies. Local clean-kernel runtime is comfortably below ten minutes; network installation time on Colab is variable.
- AutoGluon is not installed/executed; StatsForecast is the explicitly documented allowed equivalent. Leaderboard scores are local negative-MASE adapter fields with exactly two internal windows.
- Gemini live authentication/model availability has not been verified without an API key. The local mode and mocked request path passed.
- Original Streamlit functional tests passed; the subsequent redesign also received actual browser visual/interaction testing. See `UI_TESTING.md` for screenshots, responsive checks and remaining limits.
- This is synthetic data. The final model was selected retrospectively from the same eight test folds, which may be optimistic; a past-only adaptive policy is separately scored. Neither result establishes real-world cyber forecasting capability.
- Coverage uses just 24 observations. AutoETS observed coverage 91.7% is conservative on this sample, not proof of calibrated real-world intervals.

## Commands

```powershell
python run_notebook.py
python verify_submission.py
python test_app.py
streamlit run app.py
```
