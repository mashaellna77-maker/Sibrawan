"""Personal-app verification; no live Gemini calls or academic regeneration."""
from pathlib import Path
from unittest.mock import patch,Mock
import hashlib,json,tempfile,sys,os
ROOT=Path(__file__).resolve().parent
os.environ['MPLCONFIGDIR']=str(ROOT/'.runtime/mpl')
import numpy as np
import pandas as pd
import requests
from streamlit.testing.v1 import AppTest
from ui_data import validate_upload,uploaded_forecast,capacity_plan
from diagnostics import describe_series,fitted_diagnostics
from sibrawan import rolling,zoo,score,NAMES
import gemini_client
import assistant

def test_data_and_diagnostics():
    data=validate_upload((ROOT/'data/synthetic_phishing.csv').read_bytes())
    assert len(data)==72 and data.month.min()==pd.Timestamp('2020-01-01') and data.month.max()==pd.Timestamp('2025-12-01')
    for mode in ['missing','duplicate','negative','fractional','null','short','overflow']:
        bad=data.copy()
        if mode=='missing': bad=bad.drop(index=20)
        if mode=='duplicate': bad.loc[20,'month']=bad.loc[19,'month']
        if mode=='negative': bad.loc[0,'confirmed_phishing_incidents']=-1
        if mode=='fractional':
            bad=bad.astype({'confirmed_phishing_incidents':float});bad.loc[0,'confirmed_phishing_incidents']=1.5
        if mode=='null': bad.loc[0,'month']=pd.NaT
        if mode=='short': bad=bad.iloc[:24]
        if mode=='overflow':
            bad=bad.astype({'confirmed_phishing_incidents':'uint64'});bad.loc[0,'confirmed_phishing_incidents']=2**63
        try: validate_upload(bad.to_csv(index=False).encode())
        except ValueError: pass
        else: raise AssertionError(mode)
    shape=describe_series(data)
    assert np.isclose(shape['trend_strength'],.8101760534527432)
    assert np.isclose(shape['seasonal_strength'],.6188254399380149)
    diag=fitted_diagnostics(data,'AutoETS')
    direct=next(m for m in zoo() if str(m)=='AutoETS').fit(data.confirmed_phishing_incidents.to_numpy(dtype=float)).predict_in_sample()['fitted']
    np.testing.assert_allclose(diag['frame'].fitted,direct,rtol=1e-7,atol=1e-7)
    np.testing.assert_allclose(diag['frame'].residual,diag['frame'].actual-diag['frame'].fitted)
    assert len(diag['frame'])==72 and np.isfinite(diag['acf']).all()
    original=uploaded_forecast(data,'AutoETS')
    pd.testing.assert_frame_equal(original,pd.read_csv(ROOT/'artifacts/final_forecast.csv'),check_exact=False,rtol=1e-8)
    assert capacity_plan(original,[0,0,0]).gap.sum()==original['mean'].sum()
    assert capacity_plan(original,[1000]*3).gap.sum()==0
    return data

def test_scoring_and_causality(data):
    spine=pd.DataFrame({'unique_id':'Sibrawan synthetic phishing','ds':data.month,'y':data.confirmed_phishing_incidents.astype(float)})
    cv,scores,dates=rolling(spine)
    expected=pd.read_csv(ROOT/'artifacts/fold_scores.csv')
    for col in ['MASE','scaled_CRPS','coverage_80','width_80','training_scale']:
        # Cross-platform model optimizers can differ by a few millionths.
        np.testing.assert_allclose(scores[col],expected[col],rtol=1e-6,atol=1e-6)
    assert list(dates.n_train)==list(range(48,72,3)) and cv.ds.nunique()==24
    from sibrawan import forecast
    altered=spine.copy();altered.loc[48:,'y']+=1000
    first_a=forecast(spine.iloc[:48]);first_b=forecast(altered.iloc[:48])
    pd.testing.assert_frame_equal(first_a,first_b)
    altered_cv,altered_scores,_=rolling(altered)
    prediction_cols=[c for c in cv.columns if c!='y']
    pd.testing.assert_frame_equal(cv[cv.fold==1][prediction_cols],altered_cv[altered_cv.fold==1][prediction_cols])
    np.testing.assert_allclose(scores[scores.fold==1].training_scale,altered_scores[altered_scores.fold==1].training_scale)
    for fold,g in cv.groupby('fold'):
        history=spine[spine.ds<=g.cutoff.iloc[0]]
        denominator=np.abs(history.y.to_numpy()[12:]-history.y.to_numpy()[:-12]).mean()
        for model in NAMES:
            result=score(g,model,history)
            assert np.isclose(result['training_scale'],denominator)
            assert np.isclose(result['MASE'],np.abs(g.y-g[model]).mean()/denominator)
    return scores

def test_client_errors():
    with tempfile.TemporaryDirectory() as temp:
        temporary=Path(temp)
        with patch.object(gemini_client,'ROOT',temporary):
            for code,status in [(401,'authentication'),(403,'authentication'),(404,'model'),(429,'quota'),(503,'service')]:
                with (patch.object(gemini_client,'settings',return_value=('test-only-placeholder','gemini-test')),
                      patch.object(gemini_client.requests,'post',return_value=Mock(ok=False,status_code=code))):
                    r=gemini_client.generate('اختبار','رصد')
                    assert not r['ok'] and r['status']==status and 'test-only-placeholder' not in str(r)
            with patch.object(gemini_client,'settings',return_value=('test-only-placeholder','gemini-test')),patch.object(gemini_client.requests,'post',side_effect=requests.Timeout):
                assert gemini_client.generate('اختبار','رصد')['status']=='timeout'
            with patch.object(gemini_client,'settings',return_value=('','gemini-test')):
                assert gemini_client.connection_state()['key_present'] is False
            success=Mock(ok=True);success.json.return_value={'candidates':[{'content':{'parts':[{'text':'أنا رصد، مساعد سِبرَوان.'}]}}]}
            with patch.object(gemini_client,'settings',return_value=('test-only-placeholder','gemini-test')),patch.object(gemini_client.requests,'post',return_value=success):
                assert gemini_client.generate('اسمك','رصد')['ok']
            with patch.object(gemini_client,'settings',return_value=('test-only-placeholder','gemini-3.8-flash')),patch.object(gemini_client.requests,'post',return_value=success) as post:
                assert gemini_client.generate('اسمك','رصد')['ok']
                assert post.call_args.kwargs['json']['generationConfig']['thinkingConfig']['thinkingLevel']=='low'

def test_interface(data):
    assert assistant.infer_case('لم أدخل بياناتي')=='غير محدد'
    assert assistant.infer_case('نقرت رابطًا مشبوهًا')=='نقرت رابطًا أو فتحت ملفًا'
    with tempfile.TemporaryDirectory() as temp,patch.object(gemini_client,'ROOT',Path(temp)),patch.object(gemini_client,'settings',return_value=('','gemini-test')):
        app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=60).run()
        assert not app.exception
        for page in app.radio[0].options:
            app.radio[0].set_value(page).run(timeout=60)
            assert not app.exception,(page,app.exception)
        app.radio[0].set_value('تخطيط السعة').run()
        app.number_input[0].set_value(1000).run()
        app.radio[0].set_value('رصد 📡').run()
        app.chat_input[0].set_value('ما اسمك؟').run()
        assert 'رصد' in app.session_state['messages'][-1]['content']
        app.button(key='suggest_1').click().run()
        assert '1000' in app.session_state['messages'][-1]['content']
        app.button(key='suggest_2').click().run()
        assert 'ملخص قابل للنسخ' in app.session_state['messages'][-1]['content']
        app.button(key='clear_chat').click().run()
        assert app.session_state['messages']==[]
        moved=data.copy();moved.month=moved.month+pd.DateOffset(months=1)
        app.session_state['active_data']=moved
        app.session_state['active_fc']=uploaded_forecast(moved,'AutoETS')
        app.session_state['upload_label']='test.csv'
        app.button(key='suggest_0').click().run()
        assert '2026-04' in app.session_state['messages'][-1]['content']
        assert 'السجل المرفوع' in app.session_state['messages'][-1]['content']
        app.button(key='reset_data').click().run()
        assert app.session_state['messages']==[] and app.session_state['upload_label'] is None
        assert app.session_state['capacity_values']==[120]*3

if __name__=='__main__':
    data=test_data_and_diagnostics();print('PASS data, STL strengths, native one-step fitted values, final forecasts and capacities')
    test_scoring_and_causality(data);print('PASS eight-fold reproduction, training-only scales and future-perturbation invariance')
    test_client_errors();print('PASS Gemini authentication/quota/model/service/timeout/missing-key and success mocks')
    test_interface(data);print('PASS seven sections, Rasd identity, capacities, chat context, upload state and reset')
