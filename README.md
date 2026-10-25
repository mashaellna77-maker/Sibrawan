
Submitted by: Mashael Alotaibi — academy: @SDAIAAcademy

# سِبرَوان | Sibrawan

An experimental platform for analyzing monthly phishing incident counts and forecasting the following three months to support response capacity planning and identify projected shortfalls. The platform includes “Rasd,” an AI assistant that explains results and provides initial incident response guidance.

The project uses simulated data for demonstration purposes. A confirmed phishing incident does not necessarily mean a successful compromise.

## Project Contents

| File or Folder | Contents |
|---|---|
| `project.ipynb` | Analysis, modeling, and evaluation notebook with execution outputs |
| `data/synthetic_phishing.csv` | Monthly data from January 2020 to December 2025 |
| `generate_data.py` | Data generation using the fixed seed `20261014` |
| `sibrawan.py` | Models, rolling-origin evaluation harness, and scoring |
| `artifacts/` | Results tables, forecasts, and charts |
| `report.md` and `report.pdf` | Three-page report presenting findings and recommendations |
| `app.py` | Platform interface |
| `assistant.py` and `gemini_client.py` | Assistant logic and language model integration |
| `brief.md` and `rubric.md` | Project instructions and grading criteria |

## Running on Colab

[Open the project notebook in Colab](https://colab.research.google.com/github/mashaellna77-maker/Sibrawan/blob/main/project.ipynb), then select **Runtime → Run all**.

The setup cell clones the repository into `/content/sibrawan` and installs dependencies from `requirements.txt`. Use a fresh session to avoid loading an outdated copy of the files.

The analysis was tested locally using Python 3.12. Installing dependencies requires an internet connection, while analysis and forecasting do not require an API key. Full execution on Colab has not yet been verified.

## Running Locally

```powershell
git clone https://github.com/mashaellna77-maker/Sibrawan.git
cd Sibrawan
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip install jupyterlab
jupyter lab project.ipynb
```

Run the notebook from beginning to end to regenerate the results and report, then launch the interface:

```powershell
streamlit run app.py
```

To execute the notebook automatically and verify the results:

```powershell
python run_notebook.py
python verify_submission.py
python test_local.py
```

Test details and limitations are documented in `TESTING.md` and `LOCAL_STATUS.md`.

## Data and Analysis

The dataset contains 72 consecutive monthly observations with no missing months. Validation checks timestamp regularity, duplicates, missing values, and valid incident counts.

The analysis includes:

- Plotting the series and interpreting its trend and annual variation.
- STL decomposition with a seasonal period of 12 months.
- Calculating trend and seasonal strength.
- Plotting the ACF and interpreting correlations at lags 12 and 24.
- Analyzing benchmark residuals and forecast errors.

## Models and Evaluation

**StatsForecast**, an alternative permitted by the project instructions, was used to fit five models:

`Naive` · `SeasonalNaive(12)` · `AutoETS` · `AutoARIMA` · `AutoTheta`

The notebook explicitly shows the conversion into the required `unique_id`, `ds`, and `y` columns.

The comparison uses eight expanding-window tests, with a three-month forecast horizon and a three-month step. The initial training window contains 48 months, and the test windows cover the quarters of 2024 and 2025. All models use the same test dates.

Scaling denominators are calculated using only the training data available within each window. Evaluation includes:

- MASE for point forecast error.
- Scaled CRPS for predictive distribution performance.
- Observed coverage of the nominal 80% prediction interval.
- Average interval width.
- Window-level results and comparisons against the benchmark.

CRPS is approximated numerically using ten quantiles and trapezoidal integration, assuming zero loss at endpoints 0 and 1, then divided by the training scaling denominator. This scaling definition differs from the original course scoring function and is documented in the notebook.

The internal leaderboard uses two validation windows, followed by a separate test on the final three months. The locally defined `score_val` and `score_test` fields represent negative MASE; values closer to zero are better. This leaderboard is descriptive, while the main comparison uses all eight rolling-origin windows.

## Results and Limitations

**AutoETS** was selected using the lowest average scaled CRPS among models whose observed coverage reached at least 80%.

| Metric | AutoETS | SeasonalNaive |
|---|---:|---:|
| MASE | 0.538 | 1.078 |
| Scaled CRPS | 0.435 | 0.768 |
| Coverage of the nominal 80% interval | 91.7% | 79.2% |
| Average interval width, in incidents | 31.3 | 42.4 |

The final model was selected using the same evaluation windows, so its estimated performance may be optimistic. The notebook also presents a separate selection policy that uses only previously completed windows.

Coverage is based on 24 test observations. It is not an accuracy percentage or a guarantee of future performance. Intervals are evaluated as produced by the models, without calibration against test outcomes or clipping negative bounds.

The final forecast covers **January–March 2026**, immediately following the end of the dataset. Forecasts may contain fractional values because they represent statistical means.

## Capacity Planning

The interface supports a separate processing capacity for each month and calculates the shortfall at the forecast mean:

`shortfall = max(forecast mean − capacity, 0)`

Capacity is measured in **incidents that can be processed per month**, rather than cost or headcount. The calculated shortfall is a planning indicator, not the expected shortfall derived from the full predictive distribution.

## Platform Interface

The Arabic interface supports RTL and includes seven sections:

Overview, Incident Analysis, Forecasts, Model Comparison, Capacity Planning, Rasd, and About the Data.

Users can upload a CSV from the sidebar. The platform validates columns, dates, and nonnegative integer counts, accepting a continuous record of 48–600 months.

After validation, the selected model is refitted on the uploaded data, and forecasts are updated for the following three months. Displayed evaluation metrics remain associated with the original project dataset, with a notice when uploaded data is active.

Interface screenshots are available in `docs/ui-screenshots/`.

## Rasd AI Assistant

Rasd uses the current forecasts, capacity settings, and conversation context to explain results. It asks clarifying questions about phishing situations, suggests initial response actions, and prepares an incident summary for the security team.

The assistant provides local responses without an API key, with optional language model integration. Statistical forecasting models calculate the predictions; the assistant explains them and helps users interpret the results.

### Configuring the Language Model Connection

Create a local `.env` file and add `GEMINI_API_KEY` and `GEMINI_MODEL`. Select a model available to your account.

Environment files and API keys are not included in the repository and are excluded by `.gitignore`. When the connection is enabled, the question and its accompanying context are sent to the service provider. Do not enter confidential information.

Initial response guidance draws on [NIST Phishing](https://www.nist.gov/itl/smallbusinesscyber/guidance-topic/phishing) and [NIST SP 800-61r3](https://csrc.nist.gov/pubs/sp/800/61/r3/final).

## Course Requirements Coverage

| Section | Implementation |
|---|---|
| A — Exploration | Series plot, STL, trend and seasonal strength, and ACF with interpretation |
| B — Benchmark | SeasonalNaive and Naive, benchmark residuals and ACF, prediction intervals, and coverage |
| C — Modeling Framework | Explicit data conversion, five models, and a leaderboard with an explanation of scores and limitations |
| D — Temporal Evaluation | Eight shared rolling-origin windows, error and coverage metrics, and wins and losses against the benchmark |
| E — Report | Evidence-based recommendation, interpretation of intervals and errors, and a specific development step |

The proposed next step is to collect consistently defined real incident counts and suspicious-message volumes, then evaluate a regression model using a lagged predictor against the same benchmark. This is a proposed extension and has not been implemented in the current project.
