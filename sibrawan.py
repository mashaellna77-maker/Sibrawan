"""Small transparent harness: all fit/scale operations are inside each origin."""
from pathlib import Path
import numpy as np
import pandas as pd
from statsforecast import StatsForecast
from statsforecast.models import Naive, SeasonalNaive, AutoETS, AutoARIMA, AutoTheta
from coursekit import scoring

NAMES = ['Naive', 'SeasonalNaive', 'AutoETS', 'AutoARIMA', 'AutoTheta']

def zoo():
    return [Naive(), SeasonalNaive(season_length=12), AutoETS(season_length=12),
            AutoARIMA(season_length=12, stepwise=True, max_p=3, max_q=3, max_P=1, max_Q=1),
            AutoTheta(season_length=12)]

def forecast(history, h=3):
    # No fallback silently replacing a failed model; an error stops execution.
    return StatsForecast(models=zoo(), freq='MS', n_jobs=1).forecast(
        df=history, h=h, level=scoring.LEVELS)

def scale(history):
    y = history.y.to_numpy()
    denominator = np.mean(np.abs(y[12:]-y[:-12]))
    if not np.isfinite(denominator) or denominator <= 0:
        raise ValueError('Undefined seasonal training scale')
    return denominator

def score(frame, name, history):
    y = frame.y.to_numpy()
    qs = frame[scoring.qcols(name)].to_numpy()
    tau = scoring.QUANTILES
    error = y[:, None]-qs
    pinball = np.maximum(tau*error, (tau-1)*error)
    # CRPS = 2 integral pinball. Ten quantiles .025 ... .975;
    # trapezoids on that range, zero loss at endpoints 0 and 1.
    # Endpoint assumption is explicit; finite-grid approximation, not exact CRPS.
    x = np.r_[0, tau, 1]
    losses = np.column_stack([np.zeros(len(y)), pinball, np.zeros(len(y))])
    crps = 2*np.trapezoid(losses, x=x, axis=1).mean()
    d = scale(history)
    return {'MASE': np.abs(y-frame[name]).mean()/d, 'scaled_CRPS': crps/d,
            'coverage_80': scoring.coverage(frame, name),
            'width_80': (frame[f'{name}-hi-80']-frame[f'{name}-lo-80']).mean(),
            'training_scale': d}

def rolling(df):
    frames, rows, dates = [], [], []
    for fold, n in enumerate(range(48, 72, 3), 1):
        history, test = df.iloc[:n].copy(), df.iloc[n:n+3].copy()
        fc = forecast(history).merge(test, on=['unique_id','ds'], validate='one_to_one')
        fc['fold'], fc['cutoff'] = fold, history.ds.max()
        assert len(fc) == 3 and history.ds.max() < fc.ds.min()
        frames.append(fc)
        dates.append({'fold':fold,'n_train':n,'train_start':history.ds.min(),
                      'train_end':history.ds.max(),'test_start':test.ds.min(),'test_end':test.ds.max()})
        for name in NAMES:
            rows.append({'fold':fold,'model':name,**score(fc,name,history)})
    return pd.concat(frames,ignore_index=True), pd.DataFrame(rows), pd.DataFrame(dates)

def residual_read(values):
    from statsmodels.tsa.stattools import acf
    arr = np.asarray(values)
    a = acf(arr, nlags=min(12,len(arr)-1), fft=False)
    ref=1.96/np.sqrt(len(arr))
    bias='under-predicts on average' if arr.mean()>0 else 'over-predicts on average'
    structure='; '.join(f'lag {lag} is {"outside" if abs(a[lag])>ref else "inside"} the approximate reference' for lag in [1,12])
    return (f'mean={arr.mean():.2f} ({bias}), ACF(1)={a[1]:.3f}, ACF(12)={a[12]:.3f}; '
            f'descriptive 95% reference +/-{ref:.3f}; {structure}')
