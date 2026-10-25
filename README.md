Submitted by: Mashael Alotaibi — academy: @SDAIAAcademy

# سِبرَوان | Sibrawan

Sibrawan is an experimental platform that forecasts monthly phishing incident counts and compares them with response capacity. It also includes Rasd, an AI assistant that explains the results and provides initial incident response guidance.

The project uses simulated data. A confirmed phishing incident does not necessarily mean a successful compromise.

## Project Files

| File or Folder | Purpose |
|---|---|
| `project.ipynb` | Analysis, model comparison, evaluation, and saved outputs |
| `data/synthetic_phishing.csv` | 72 monthly observations, January 2020–December 2025 |
| `generate_data.py` | Data generator with a fixed seed |
| `sibrawan.py` | Forecasting models and rolling-origin evaluation |
| `artifacts/` | Forecasts, evaluation results, and charts |
| `report.md` and `report.pdf` | Three-page management report |
| `app.py` | Streamlit interface |
| `assistant.py` and `gemini_client.py` | Rasd assistant and language model connection |
| `brief.md` and `rubric.md` | Course brief and assessment criteria |

## Getting Started

### Colab

[Open the notebook in Colab](https://colab.research.google.com/github/mashaellna77-maker/Sibrawan/blob/main/project.ipynb) and select **Runtime → Run all**.

The setup cell downloads the repository and installs the dependencies. Start with a fresh session to avoid using an older copy.

The analysis has been tested locally with Python 3.12. Full execution on Colab has not yet been verified. Forecasting does not require an API key.

### Local Setup

```powershell
git clone https://github.com/mashaellna77-maker/Sibrawan.git
cd Sibrawan
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip install jupyterlab
jupyter lab project.ipynb
```

Run the notebook from top to bottom to regenerate the results and report.

To launch the platform:

```powershell
streamlit run app.py
```

To run the notebook automatically and check the project:

```powershell
python run_notebook.py
python verify_submission.py
python test_local.py
```

See `TESTING.md` and `LOCAL_STATUS.md` for test results and known limitations.

## Analysis

The dataset contains 72 consecutive months. The notebook checks dates, missing months, duplicates, and incident counts before fitting any models.

The analysis covers:

- The historical trend and annual pattern.
- STL decomposition with a 12-month period.
- Trend and seasonal strength.
- Raw-series ACF, including lags 12 and 24.
- Seasonal Naive residuals and out-of-sample forecast errors.

## Forecasting and Evaluation

Five models are fitted using StatsForecast:

- Naive
- SeasonalNaive, with a 12-month seasonal period
- AutoETS
- AutoARIMA
- AutoTheta

The notebook shows how the data is converted into the `unique_id`, `ds`, and `y` columns.

All models are evaluated on the same eight expanding windows. Each window forecasts three months, with a three-month step between origins. The first training window contains 48 months, and the tests cover 2024 and 2025.

The comparison includes MASE, scaled CRPS, 80% interval coverage, and average interval width. Scaling denominators use only the training history available at each origin.

CRPS is approximated from ten quantiles using trapezoidal integration and zero endpoint losses. It is divided by the training seasonal-change scale. This differs from the original course function’s scaling and is explained in the notebook.

A separate leaderboard reports two internal validation windows and a final three-month holdout. Its `score_val` and `score_test` columns use negative MASE, so values closer to zero are better. The eight rolling-origin windows provide the main evaluation evidence.

## Results

AutoETS was selected for its lowest average scaled CRPS among models with observed coverage of at least 80%.

| Metric | AutoETS | SeasonalNaive |
|---|---:|---:|
| MASE | 0.538 | 1.078 |
| Scaled CRPS | 0.435 | 0.768 |
| Observed 80% interval coverage | 91.7% | 79.2% |
| Average 80% interval width, in incidents | 31.3 | 42.4 |

These results come from 24 test observations. Coverage is not an accuracy percentage, and this small sample does not establish future calibration.

The final model was selected using the same evaluation windows, which may make its reported performance optimistic. The notebook also evaluates a selection policy that uses only completed earlier windows.

Prediction intervals are scored without test-based calibration or clipping negative bounds.

After fitting the selected model on the full dataset, the final forecasts cover **January–March 2026**. These dates follow the end of the supplied record. Fractional forecasts represent expected counts.

## Capacity Planning

Users can set a different response capacity for each month. The platform calculates:

```text
shortfall = max(forecast mean − capacity, 0)
```

Capacity means the number of incidents the team can process per month. It does not represent cost or headcount.

The shortfall is calculated at the forecast mean. It is a planning measure rather than the expected shortfall across the full predictive distribution.

## Interface

The platform has an Arabic RTL interface with seven sections:

- Overview
- Incident Analysis
- Forecasts
- Model Comparison
- Capacity Planning
- Rasd
- About the Data

Users can upload a CSV containing 48–600 consecutive months of nonnegative integer counts. Once the file passes validation, the selected model is refitted and forecasts the next three months.

The original evaluation metrics remain tied to the project dataset. They are not presented as evaluation results for uploaded files.

Screenshots are available in `docs/ui-screenshots/`.

## Rasd

Rasd explains the forecasts using the current data, capacity settings, and conversation context. It also asks clarifying questions about phishing situations, suggests initial response steps, and prepares a summary for the security team.

Local responses are available without an API key. A language model can be connected for generative responses. The statistical models produce the forecasts; Rasd explains them.

### Language Model Setup

Create a local `.env` file containing:

```text
GEMINI_API_KEY=your_key
GEMINI_MODEL=your_available_model
```

Keep this file on your device. Environment files and credentials are excluded by `.gitignore`.

When the connection is enabled, the question and supporting context are sent to the model provider. Do not include confidential information.

Response guidance draws on [NIST Phishing](https://www.nist.gov/itl/smallbusinesscyber/guidance-topic/phishing) and [NIST SP 800-61r3](https://csrc.nist.gov/pubs/sp/800/61/r3/final).

## Course Coverage

| Section | Included Work |
|---|---|
| A — Exploration | Series plot, STL, strength measures, and ACF interpretation |
| B — Benchmark | SeasonalNaive and Naive, benchmark residuals, intervals, and coverage |
| C — Framework | Visible data conversion, five fitted models, and leaderboard interpretation |
| D — Evaluation | Shared rolling origins, point and distributional scores, and benchmark comparisons |
| E — Report | Recommendation, interval assessment, error analysis, and a specific next step |

## Next Step

Collect consistently defined real incident counts and suspicious-message volumes, then test whether lagged message volume improves forecasts against the same benchmark.

