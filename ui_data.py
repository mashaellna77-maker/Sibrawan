"""UI-only data validation and forecasts; never overwrites capstone evidence."""
from io import BytesIO
import numpy as np
import pandas as pd
from statsforecast import StatsForecast
from sibrawan import zoo

def validate_upload(content):
    try:
        raw=pd.read_csv(BytesIO(content))
    except Exception as exc:
        raise ValueError('تعذر قراءة CSV. احفظ الملف بترميز UTF-8 وبفاصلة بين العمودين.') from exc
    if list(raw.columns)!=['month','confirmed_phishing_incidents']:
        raise ValueError('العمودان المطلوبان بالترتيب: month و confirmed_phishing_incidents.')
    if not 48<=len(raw)<=600:
        raise ValueError('يلزم سجل من 48 إلى 600 شهر لدعم تدريب نموذج موسمي.')
    if raw.isna().any().any():
        raise ValueError('يوجد تاريخ أو عدد مفقود. أكمل القيم قبل الرفع.')
    try:
        dates=pd.to_datetime(raw.month,format='mixed',errors='raise')
        values=pd.to_numeric(raw.confirmed_phishing_incidents,errors='raise')
    except Exception as exc:
        raise ValueError('تحقق من التواريخ والأعداد. صيغة الشهر المقترحة YYYY-MM.') from exc
    if not (dates.dt.day==1).all() or dates.duplicated().any():
        raise ValueError('يجب تمثيل كل شهر مرة واحدة وبداية الشهر فقط (YYYY-MM أو YYYY-MM-01).')
    if not np.isfinite(values).all() or (values<0).any() or not np.equal(values,np.floor(values)).all():
        raise ValueError('أعداد الحوادث يجب أن تكون صحيحة، غير سالبة، ومحدودة.')
    if (values>np.iinfo(np.int64).max).any():
        raise ValueError('يوجد عدد يتجاوز سعة التخزين الصحيحة المدعومة. راجع قيم CSV.')
    clean=pd.DataFrame({'month':dates,'confirmed_phishing_incidents':values.astype('int64')}).sort_values('month').reset_index(drop=True)
    expected=pd.date_range(clean.month.min(),clean.month.max(),freq='MS')
    if len(expected)!=len(clean) or not np.array_equal(expected.to_numpy(),clean.month.to_numpy()):
        raise ValueError('يوجد شهر مفقود في السجل. يجب أن تكون الأشهر متصلة دون فجوات.')
    return clean

def uploaded_forecast(data, chosen):
    spine=pd.DataFrame({'unique_id':'Uploaded monthly incidents','ds':data.month,
                       'y':data.confirmed_phishing_incidents.astype(float)})
    model=next(m for m in zoo() if str(m)==chosen)
    result=StatsForecast(models=[model],freq='MS',n_jobs=1).forecast(df=spine,h=3,level=[80,95])
    result=result[['ds',chosen,f'{chosen}-lo-80',f'{chosen}-hi-80',f'{chosen}-lo-95',f'{chosen}-hi-95']]
    result.columns=['month','mean','lo80','hi80','lo95','hi95']
    result['month']=result.month.dt.strftime('%Y-%m-%d')
    if not np.isfinite(result[['mean','lo80','hi80','lo95','hi95']]).all().all():
        raise ValueError('تعذر الحصول على نطاقات محدودة لهذا السجل. راجع البيانات قبل تطبيقها.')
    return result

def capacity_plan(fc, capacities):
    result=fc[['month','mean','lo80','hi80']].copy()
    result['capacity']=np.asarray(capacities,dtype=float)
    result['gap']=np.maximum(0,result['mean']-result.capacity)
    result['stress_gap']=np.maximum(0,result.hi80-result.capacity)
    return result
