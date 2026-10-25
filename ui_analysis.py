"""UI diagnostics for the active history, with explicit reference-test scope."""
import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from diagnostics import describe_series, fitted_diagnostics
from ui_data import uploaded_forecast

history_diagnostics=st.cache_data(show_spinner=False)(describe_series)
one_step_diagnostics=st.cache_data(show_spinner=False)(fitted_diagnostics)
current_forecast=st.cache_data(show_spinner=False)(uploaded_forecast)

def acf_figure(values,reference,theme):
    fig=go.Figure(go.Bar(x=list(range(len(values))),y=values,marker_color='#0898ad',
        hovertemplate='التأخير %{x}: %{y:.3f}<extra></extra>'))
    fig.add_hline(y=0,line_color='#8192a5',line_width=1)
    fig.add_hrect(y0=-reference,y1=reference,fillcolor='rgba(118,86,191,.10)',line_width=0,layer='below')
    fig.update_xaxes(title_text='التأخير بالشهور',tickmode='array',tickvals=[0,1,6,12,18,24],type='linear')
    fig.update_yaxes(title_text='الارتباط',range=[-1.05,1.05])
    fig=theme(fig,350)
    fig.update_xaxes(tickformat='d',hoverformat='d')
    return fig

def render_shape(data,theme,plot):
    shape=history_diagnostics(data)
    st.subheader('قراءة الاتجاه والموسمية')
    direction='ارتفع' if shape['trend_change']>0 else 'انخفض' if shape['trend_change']<0 else 'ثبت'
    st.write(f"مكون الاتجاه في STL {direction} بمقدار {abs(shape['trend_change']):.1f} حادثًا بين طرفي السجل. نطاق المكون الموسمي {shape['seasonal_range']:.1f} حادثًا، وأكبر باقٍ مطلق {shape['remainder_max']:.1f}. الموسمية هنا نمط سنوي وصفي، وليست سببًا مثبتًا للحوادث.")
    with st.container(border=True):
        st.subheader('STL بفترة 12: الاتجاه، الموسمية، والبواقي')
        frame=shape['components']
        fig=make_subplots(rows=3,cols=1,shared_xaxes=True,vertical_spacing=.09,
            subplot_titles=['الاتجاه','الموسمية السنوية','البواقي بعد التفكيك'])
        for i,(name,color) in enumerate([('trend','#0898ad'),('seasonal','#7656bf'),('remainder','#516f94')],1):
            fig.add_trace(go.Scatter(x=frame.month,y=frame[name],mode='lines',line={'color':color,'width':2},showlegend=False),row=i,col=1)
        fig=theme(fig,680); fig.update_layout(hovermode='x unified',margin={'t':40,'b':45})
        fig.update_xaxes(tickformat='%Y-%m',hoverformat='%Y-%m')
        plot(fig)
        a,b=st.columns(2)
        a.metric('قوة الاتجاه',f"{shape['trend_strength']:.3f}")
        b.metric('قوة الموسمية',f"{shape['seasonal_strength']:.3f}")
        st.latex(r'F_T=\max(0,1-\mathrm{Var}(R)/\mathrm{Var}(T+R))')
        st.latex(r'F_S=\max(0,1-\mathrm{Var}(R)/\mathrm{Var}(S+R))')
        st.caption('T الاتجاه، S الموسمية، R البواقي؛ التباين محسوب من المكونات نفسها. في السلسلة الثابتة نعرّف القوة بصفر لتجنب قسمة غير معرفة.')
        st.write('المكون الاتجاهي يصف تغير المستوى، والموسمي يصف التكرار السنوي، والبواقي تحتفظ بالضوضاء والقفزات غير المفسرة. القوة الأعلى تدعم تجربة نماذج اتجاه/موسمية مثل ETS وARIMA مع الإبقاء على خط الأساس؛ لا تختار الفائز بمفردها.')
    with st.container(border=True):
        st.subheader('ACF للسجل الحالي: ماذا يحدث عند 12 و24 شهرًا؟')
        plot(acf_figure(shape['acf'],shape['acf_reference'],theme))
        for lag in [12,24]:
            value=float(shape['acf'][lag]); outside=abs(value)>shape['acf_reference']
            st.write(f"التأخير {lag}: **{value:.3f}**؛ {'خارج' if outside else 'داخل'} المرجع التقريبي ±{shape['acf_reference']:.3f}. {'ارتباط موجب بين أشهر متباعدة سنة/سنتين' if value>0 else 'ارتباط سالب أو شبه معدوم في هذا التأخير'}. لا تكفي هذه القيمة وحدها لإثبات الموسمية.")
        st.caption('الاتجاه يؤثر في ACF الخام؛ التأخيرات البعيدة تستخدم أزواجًا أقل. المرجع وصفي تقريبي، وليس اختبارًا قاطعًا للاستقلال.')

def render_residuals(data,chosen,theme,plot,root,uploaded):
    with st.container(border=True):
        st.subheader('بواقي الملاءمة لخطوة واحدة داخل التدريب')
        result=one_step_diagnostics(data,chosen)
        frame=result['frame']
        st.caption(f'{chosen} · السجل الحالي كاملًا · {result["n"]} قيمة ملاءمة محدودة من StatsForecast.forecast_fitted_values()')
        fig=go.Figure(go.Scatter(x=frame.month,y=frame.residual,mode='lines',line={'color':'#0898ad'},name='y − fitted'))
        fig.add_hline(y=0,line_color='#8192a5');fig.update_yaxes(title_text='باقي الملاءمة / حادث')
        plot(theme(fig,330));plot(acf_figure(result['acf'],result['acf_reference'],theme))
        st.metric('متوسط باقي الملاءمة',f"{result['mean']:.3f} حادث")
        st.write(f"الإشارة {'الموجبة تعني ميلًا إلى التقليل من العدد' if result['mean']>0 else 'السالبة تعني ميلًا إلى المبالغة في العدد'}. الحجم بوحدة حادث، ولا يثبت وحده انحيازًا عمليًا مهمًا.")
        for lag in [1,12]:
            value=float(result['acf'][lag])
            st.write(f"ACF({lag}) = {value:.3f}: {'توجد إشارة وصفية إلى ارتباط متبقٍ' if abs(value)>result['acf_reference'] else 'لا توجد إشارة قوية عند هذا التأخير'} مقارنة بمرجع ±{result['acf_reference']:.3f}.")
        st.info('هذه fitted values لخطوة واحدة، بمعلمات وحالات ابتدائية قُدرت من كامل سجل التدريب. ليست تنبؤات تاريخية من نماذج لم ترَ المستقبل. التشخيص وصفي فقط ولا يعدّل اختبارات النوافذ أو اختيار النموذج أو التوقعات الماضية.')
    with st.container(border=True):
        st.subheader('أخطاء التنبؤ خارج التدريب — سجل المشروع الأصلي')
        cv=pd.read_csv(root/'artifacts/cv_predictions.csv',parse_dates=['ds'])
        fig=go.Figure()
        for name,color in [('SeasonalNaive','#516f94'),(chosen,'#7656bf')]:
            errors=cv.y-cv[name]
            fig.add_trace(go.Scatter(x=cv.ds,y=errors,name=name,line={'color':color}))
        fig.add_hline(y=0,line_color='#8192a5'); plot(theme(fig,350))
        st.caption('24 مشاهدة اختبار، أفق 1–3 أشهر عبر ثماني نوافذ؛ هذه أخطاء مستقبل لم يره تدريب كل نافذة، بخلاف بواقي الملاءمة أعلاه.')
        if uploaded: st.warning('هذا الرسم يخص التقييم الأصلي فقط؛ ليس اختبارًا للسجل المرفوع.')
