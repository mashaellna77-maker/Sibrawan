"""Independent verification of key scoring and delivery invariants."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
import nbformat
from pypdf import PdfReader
from utilsforecast.losses import mase
from generate_data import generate
from sibrawan import NAMES, score
from coursekit import scoring

ROOT=Path(__file__).resolve().parent

def verify():
    raw=pd.read_csv(ROOT/'data/synthetic_phishing.csv')
    pd.testing.assert_frame_equal(raw,generate())
    df=pd.DataFrame({'unique_id':'Sibrawan synthetic phishing',
                     'ds':pd.to_datetime(raw.month),'y':raw.confirmed_phishing_incidents.astype(float)})
    cv=pd.read_csv(ROOT/'artifacts/cv_predictions.csv',parse_dates=['ds','cutoff'])
    saved=pd.read_csv(ROOT/'artifacts/fold_scores.csv')
    assert len(cv)==24 and cv.ds.nunique()==24 and cv.fold.nunique()==8
    assert cv.ds.min()==pd.Timestamp('2024-01-01') and cv.ds.max()==pd.Timestamp('2025-12-01')
    for fold,g in cv.groupby('fold'):
        hist=df[df.ds<=g.cutoff.iloc[0]]
        assert len(hist)==48+3*(fold-1) and len(g)==3
        assert hist.ds.max()<g.ds.min()
        d=np.mean(np.abs(hist.y.to_numpy()[12:]-hist.y.to_numpy()[:-12]))
        for name in NAMES:
            q=g[scoring.qcols(name)].to_numpy()
            assert np.isfinite(q).all() and (np.diff(q,axis=1)>=-1e-8).all()
            r=saved[(saved.fold==fold)&(saved.model==name)].iloc[0]
            assert np.isclose(r.training_scale,d)
            independent=float(mase(g.drop(columns=['cutoff','fold']),models=[name],seasonality=12,train_df=hist)[name].iloc[0])
            assert np.isclose(independent,r.MASE)
            e=g.y.to_numpy()[:,None]-q
            pb=np.maximum(scoring.QUANTILES*e,(scoring.QUANTILES-1)*e)
            grid=np.r_[0,scoring.QUANTILES,1]
            # Explicit trapezoid sum, independently of harness np.trapezoid call.
            loss=np.column_stack([np.zeros(3),pb,np.zeros(3)])
            integral=((loss[:,:-1]+loss[:,1:])*np.diff(grid)/2).sum(axis=1)
            assert np.isclose(2*integral.mean()/d,r.scaled_CRPS)
            assert np.isclose(((g.y>=g[name+'-lo-80'])&(g.y<=g[name+'-hi-80'])).mean(),r.coverage_80)
            assert np.isclose((g[name+'-hi-80']-g[name+'-lo-80']).mean(),r.width_80)
    dates=pd.read_csv(ROOT/'artifacts/fold_dates.csv')
    assert list(dates.n_train)==list(range(48,72,3))
    final=pd.read_csv(ROOT/'artifacts/final_forecast.csv')
    assert list(pd.to_datetime(final.month).dt.strftime('%Y-%m'))==['2026-01','2026-02','2026-03']
    assert len(PdfReader(ROOT/'report.pdf').pages)==3
    nb=nbformat.read(ROOT/'project.ipynb',as_version=4)
    code=[c for c in nb.cells if c.cell_type=='code']
    assert all(c.execution_count is not None for c in code)
    assert not any(o.output_type=='error' for c in code for o in c.outputs)
    assert not any('TODO' in c.source for c in code)
    assert (ROOT/'README.md').read_text(encoding='utf-8').splitlines()[0]=='Submitted by: Mashael Alotaibi — academy: @SDAIAAcademy'
    # Degenerate scaling must fail instead of quietly emitting invalid metrics.
    from sibrawan import scale
    try: scale(pd.DataFrame({'y':np.ones(48)}))
    except ValueError: pass
    else: raise AssertionError('Constant-series scale was not rejected')
    print('PASS: frozen data, 8 folds, 5 models, training scales, independent MASE/CRPS/coverage/width, monotone quantiles, clean notebook, 3 PDF pages, README attribution.')

if __name__=='__main__': verify()
