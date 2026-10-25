"""Descriptive diagnostics only: never feeds fits, selection, or past forecasts."""
import numpy as np
import pandas as pd
from statsmodels.tsa.seasonal import STL
from statsmodels.tsa.stattools import acf
from statsforecast import StatsForecast
from sibrawan import zoo

def describe_series(data):
    y=data.confirmed_phishing_incidents.to_numpy(dtype=float)
    result=STL(y,period=12,robust=True).fit()
    def strength(component):
        denominator=np.var(component+result.resid)
        return max(0.,1-np.var(result.resid)/denominator) if denominator>0 else 0.
    components=pd.DataFrame({'month':data.month,'trend':result.trend,
        'seasonal':result.seasonal,'remainder':result.resid})
    correlations=acf(y,nlags=24,fft=False) if np.var(y)>0 else np.r_[1.,np.zeros(24)]
    return {'components':components,'trend_strength':strength(result.trend),
        'seasonal_strength':strength(result.seasonal),'acf':correlations,
        'acf_reference':1.96/np.sqrt(len(y)),
        'trend_change':float(result.trend[-1]-result.trend[0]),
        'seasonal_range':float(np.ptp(result.seasonal)),
        'remainder_max':float(np.max(np.abs(result.resid)))}

def fitted_diagnostics(data,chosen):
    spine=pd.DataFrame({'unique_id':'diagnostic history','ds':pd.to_datetime(data.month),
        'y':data.confirmed_phishing_incidents.to_numpy(dtype=float)})
    model=next(m for m in zoo() if str(m)==chosen)
    sf=StatsForecast(models=[model],freq='MS',n_jobs=1)
    sf.forecast(df=spine,h=3,fitted=True)
    fitted=sf.forecast_fitted_values()[['ds','y',chosen]].copy()
    fitted.columns=['month','actual','fitted']
    fitted=fitted[np.isfinite(fitted.fitted)&np.isfinite(fitted.actual)].copy()
    fitted['residual']=fitted.actual-fitted.fitted
    if len(fitted)<25: raise ValueError('لا توجد بواقي ملاءمة كافية للتشخيص.')
    values=fitted.residual.to_numpy()
    correlations=acf(values,nlags=24,fft=False) if np.var(values)>0 else np.r_[1.,np.zeros(24)]
    return {'frame':fitted,'mean':float(values.mean()),'acf':correlations,
        'acf_reference':1.96/np.sqrt(len(values)),'n':len(values)}
