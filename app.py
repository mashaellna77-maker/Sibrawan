"""Sibrawan presentation UI. Capstone evidence remains immutable."""
from pathlib import Path
from html import escape
from datetime import timedelta
import json, os, re
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from assistant import ask_gemini, infer_case
from gemini_client import connection_state, probe
from ui_analysis import current_forecast, history_diagnostics, one_step_diagnostics, render_shape, render_residuals
from ui_data import validate_upload, uploaded_forecast, capacity_plan

ROOT=Path(__file__).resolve().parent
st.set_page_config(page_title='سِبرَوان | Sibrawan',page_icon='◈',layout='wide',initial_sidebar_state='auto')
st.markdown('<style>'+ (ROOT/'ui.css').read_text(encoding='utf-8')+'</style>',unsafe_allow_html=True)
CYAN,PURPLE,NAVY='#0898ad','#7656bf','#142b42'
ICONS={
 'shield':'<path d="M12 3 4 6v6c0 5 8 9 8 9s8-4 8-9V6z"/><path d="m8 12 3 3 5-6"/>',
 'chart':'<path d="M4 4v16h16M7 14l4-5 4 3 5-7"/>',
 'calendar':'<rect x="4" y="5" width="16" height="15" rx="2"/><path d="M8 3v4m8-4v4M4 10h16m-11 4h2m4 0h2m-8 3h2"/>',
 'forecast':'<path d="M3 17l5-5 5 2 7-10m-5 0h5v5M3 21h18"/>',
 'layers':'<path d="m12 3 10 6-10 6L2 9zm-9 10 9 5 9-5M3 17l9 5 9-5"/>',
 'capacity':'<rect x="3" y="4" width="18" height="6" rx="2"/><rect x="3" y="14" width="18" height="6" rx="2"/><path d="M7 7h.01M7 17h.01M11 7h6m-6 10h6"/>',
 'bot':'<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="3"/><path d="m12 12 7-7"/><circle cx="7" cy="9" r=".7"/><circle cx="15" cy="17" r=".7"/>',
 'info':'<circle cx="12" cy="12" r="9"/><path d="M12 11v6m0-10h.01"/>'}
def icon(name):
    return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'+ICONS[name]+'</svg>'
def section(title, subtitle, symbol='chart'):
    st.markdown(f'<div class="section-heading"><span class="icon-box">{icon(symbol)}</span><h2>{escape(title)}</h2></div><p class="section-description">{escape(subtitle)}</p>',unsafe_allow_html=True)
def note(text):
    st.markdown('<div class="note">'+escape(text)+'</div>',unsafe_allow_html=True)
def theme(fig,height=380):
    fig.update_layout(template='plotly_white',paper_bgcolor='white',plot_bgcolor='white',
        font={'family':'Tahoma, Segoe UI, sans-serif','color':NAVY,'size':11},
        colorway=[CYAN,PURPLE,'#516f94','#a595c6','#58bdc8','#a989d7'],height=height,
        margin={'l':40,'r':20,'t':25,'b':90},hovermode='x unified',
        hoverlabel={'bgcolor':'#10253e','font':{'color':'white','size':12}},
        legend={'orientation':'h','y':-.2,'x':1,'xanchor':'right','yanchor':'top','font':{'size':10}},
        xaxis={'showgrid':False,'automargin':True,'tickformat':'%Y-%m','hoverformat':'%Y-%m'},
        yaxis={'gridcolor':'#edf1f7','zeroline':False,'automargin':True})
    return fig
def plot(fig): st.plotly_chart(fig,width='stretch',config={'displaylogo':False,'displayModeBar':False,'modeBarButtonsToRemove':['lasso2d','select2d']})

if not (ROOT/'artifacts/summary.json').exists():
    st.error('نتائج التحليل غير موجودة. شغّل project.ipynb لإنشائها أولًا.');st.stop()
summary=json.loads((ROOT/'artifacts/summary.json').read_text(encoding='utf-8'))
metrics=pd.read_csv(ROOT/'artifacts/metrics.csv')
reference_data=validate_upload((ROOT/'data/synthetic_phishing.csv').read_bytes())
reference_fc=current_forecast(reference_data,summary['chosen'])
row=metrics[metrics.model==summary['chosen']].iloc[0]
PAGES=['نظرة عامة','تحليل الحوادث','التوقعات','مقارنة النماذج','تخطيط السعة','رصد 📡','عن البيانات']
if 'active_data' not in st.session_state:
    st.session_state.active_data=reference_data
    st.session_state.active_fc=reference_fc
    st.session_state.upload_label=None
if 'messages' not in st.session_state: st.session_state.messages=[]
if 'nav' not in st.session_state: st.session_state.nav='نظرة عامة'
if 'capacity_values' not in st.session_state: st.session_state.capacity_values=[120,120,120]
def update_capacity(i):
    st.session_state.capacity_values[i]=st.session_state[f'capacity_{i}']
def navigation_changed():
    st.session_state.scroll_top=True

@st.cache_data(show_spinner=False,ttl=3600,max_entries=8)
def process_upload(content, chosen):
    data=validate_upload(content)
    return data,uploaded_forecast(data,chosen)

def reset_data():
    st.session_state.active_data=reference_data
    st.session_state.active_fc=reference_fc
    st.session_state.upload_label=None
    st.session_state.messages=[]
    st.session_state.case_state='غير محدد'
    st.session_state.capacity_values=[120,120,120]
    for i in range(3): st.session_state.pop(f'capacity_{i}',None)

def clear_conversation():
    st.session_state.messages=[]
    st.session_state.case_state='غير محدد'

with st.sidebar:
    st.markdown(f'<div class="brand">{icon("shield")}<div>سِبرَوان<br><small>SIBRAWAN</small></div></div>',unsafe_allow_html=True)
    st.caption('بصيرة تساعدك على الاستعداد')
    st.markdown('<div class="side-label">مساحة العمل</div>',unsafe_allow_html=True)
    page=st.radio('التنقل',PAGES,key='nav',label_visibility='collapsed',on_change=navigation_changed)
    st.markdown('<div class="side-label">السجل الشهري</div>',unsafe_allow_html=True)
    upload=st.file_uploader('رفع بيانات CSV',type=['csv'],key='upload',help='month, confirmed_phishing_incidents · 48 شهرًا على الأقل · دون فجوات أو تكرار')
    if upload is not None:
        st.caption('يُطبّق الملف محليًا على الرسوم والتوقعات؛ لا يُحفظ في المستودع.')
        if st.button('التحقق وتحديث التوقعات',key='apply_upload',width='stretch'):
            try:
                with st.spinner('جارٍ فحص السجل وتدريب النموذج المختار…'):
                    new_data,new_fc=process_upload(upload.getvalue(),summary['chosen'])
                st.session_state.active_data=new_data
                st.session_state.active_fc=new_fc
                st.session_state.upload_label=upload.name
                st.session_state.messages=[]
                st.session_state.case_state='غير محدد'
                st.session_state.capacity_values=[120,120,120]
                for i in range(3): st.session_state.pop(f'capacity_{i}',None)
                st.success('تم تحديث السجل والتوقعات. نتائج التقييم الأصلية محفوظة.')
            except ValueError as exc: st.error(str(exc))
            except Exception: st.error('تعذر تدريب النموذج على هذا الملف. لم يتغير السجل الحالي؛ راجع تنوع القيم وطول التاريخ.')
    if st.session_state.upload_label:
        st.caption('السجل الحالي: '+st.session_state.upload_label)
        st.button('استعادة سجل المشروع',key='reset_data',on_click=reset_data,width='stretch')
    else: st.caption('السجل الحالي: سجل المشروع · 72 شهرًا')
    st.markdown('<div class="side-label">اتصال رصد 📡</div>',unsafe_allow_html=True)
    link_state=connection_state()
    st.caption(('المفتاح موجود محليًا' if link_state['key_present'] else 'لا يوجد مفتاح محلي')+' · '+link_state['model'])
    status='رصد 📡' if link_state['status']=='connected' else 'رصد 📡 · وضع محلي'
    detail='' if link_state['status']=='connected' else link_state['detail']
    if st.button('اختبار اتصال رصد',key='probe_connection',width='stretch'):
        with st.spinner('رصد يتحقق من النموذج واتصال Gemini…'): check=probe()
        if check['ok']: st.success('نجح الاختبار الفعلي: رد نصي من Gemini.')
        else: st.warning(check['detail'])
        link_state=connection_state()
        status='رصد 📡' if link_state['status']=='connected' else 'رصد 📡 · وضع محلي'
        detail='' if link_state['status']=='connected' else link_state['detail']
    st.markdown(f'<div class="side-status"><span class="status-dot"></span><strong>{status}</strong><small>{detail}</small></div>',unsafe_allow_html=True)
    st.caption('مصدر البيانات وحدود الاستخدام في «عن البيانات».')

data=st.session_state.active_data
fc=st.session_state.active_fc.copy()
capacities=list(st.session_state.capacity_values)
plan=capacity_plan(fc,capacities)
period=f'{data.month.min():%Y-%m} — {data.month.max():%Y-%m}'
forecast_period=f'{pd.to_datetime(fc.month.iloc[0]):%Y-%m} — {pd.to_datetime(fc.month.iloc[-1]):%Y-%m}'
st.markdown(f'''<div class="hero"><div><div class="eyebrow">PHISHING RESPONSE · CAPACITY INTELLIGENCE</div><h1>سِبرَوان | <span dir="ltr">Sibrawan</span></h1><p>حوّل سجل الحوادث إلى رؤية أوضح للطلب القادم وسعة الاستجابة.</p><div class="period-chip">{icon('calendar')}<span>فترة السجل</span><bdi>{period}</bdi><span>· {len(data)} شهرًا</span></div></div><div class="hero-art">{icon('shield')}</div></div>''',unsafe_allow_html=True)
# Shared indicators always use active history/forecasts and actual saved test evidence.
kpis=[('إجمالي الحوادث التاريخية',f'{data.confirmed_phishing_incidents.sum():,}',f'حادث مؤكد · {period}','chart'),
      ('توقع الأشهر الثلاثة القادمة',f'{fc["mean"].sum():,.1f}',f'حادث متوقع إجمالًا · {forecast_period}','forecast'),
      ('تغطية نطاق 80%',f'{row.coverage_80:.1%}','24 شهر اختبار · 2024–2025 · ليست دقة النموذج','layers'),
      ('فجوة سعة الاستجابة',f'{plan.gap.sum():,.1f}',f'مجموع العجز عند المتوسط · {forecast_period}','capacity')]
def bidi(text):
    safe=re.sub(r'(\d{4}-\d{2} — \d{4}-\d{2})',r'<bdi dir="ltr">\1</bdi>',escape(text))
    return re.sub(r'(20\d{2}–20\d{2})',r'<bdi dir="ltr">\1</bdi>',safe)
st.markdown('<div class="kpi-grid">'+''.join(f'<div class="kpi"><div class="kpi-top"><span>{title}</span><span class="icon-box">{icon(sym)}</span></div><div class="kpi-value">{value}</div><small>{bidi(subtitle)}</small></div>' for title,value,subtitle,sym in kpis)+'</div>',unsafe_allow_html=True)
if st.session_state.upload_label:
    note('تعرض الرسوم والتوقعات الملف المرفوع. التغطية ومقارنة النماذج تخصان اختبار سجل المشروع الأصلي فقط؛ لم يُقيَّم الملف الجديد بتلك النوافذ.')

def monthly_figure(tail=None):
    frame=data.tail(tail) if tail else data
    fig=go.Figure(go.Scatter(x=frame.month,y=frame.confirmed_phishing_incidents,mode='lines',
        name='الحوادث الشهرية',line={'color':CYAN,'width':2.5},fill='tozeroy',fillcolor='rgba(8,152,173,.06)',
        hovertemplate='%{x|%Y-%m}<br>حوادث مؤكدة: %{y:,.0f}<extra></extra>'))
    fig.update_yaxes(title_text='حوادث مؤكدة / شهر')
    return theme(fig)

def forecast_figure():
    history=data.tail(24)
    future=pd.to_datetime(fc.month)
    fig=go.Figure()
    for upper,lower,label,color in [('hi95','lo95','نطاق 95%','rgba(118,86,191,.07)'),('hi80','lo80','نطاق 80%','rgba(118,86,191,.18)')]:
        level=label.split()[1]
        fig.add_trace(go.Scatter(x=future,y=fc[upper],mode='lines',line={'width':0},
            name='الحد الأعلى '+level,hovertemplate='الحد الأعلى '+level+': %{y:.1f}<extra></extra>',showlegend=False))
        fig.add_trace(go.Scatter(x=future,y=fc[lower],mode='lines',line={'width':0},fill='tonexty',fillcolor=color,
            name=label,hovertemplate='الحد الأدنى '+level+': %{y:.1f}<extra></extra>'))
    fig.add_trace(go.Scatter(x=history.month,y=history.confirmed_phishing_incidents,name='السجل التاريخي',
        line={'color':CYAN,'width':2.5},hovertemplate='التاريخ: %{y:.0f}<extra></extra>'))
    fig.add_trace(go.Scatter(x=future,y=fc['mean'],name='متوسط التوقع',mode='lines+markers',
        line={'color':PURPLE,'width':3,'dash':'dash'},marker={'size':8},hovertemplate='التوقع: %{y:.1f}<extra></extra>'))
    boundary=(data.month.max().to_pydatetime()+timedelta(days=15)).isoformat()
    fig.add_shape(type='line',x0=boundary,x1=boundary,y0=0,y1=1,yref='paper',line={'color':'#bbc7d7','width':1,'dash':'dot'})
    fig.add_annotation(x=future.iloc[1],y=1.03,yref='paper',text='الأشهر القادمة',showarrow=False,font={'color':PURPLE,'size':11})
    fig.update_yaxes(title_text='حوادث مؤكدة / شهر')
    return theme(fig,430)

def forecast_table():
    table=fc.copy();table['month']=pd.to_datetime(table.month).dt.strftime('%Y-%m')
    return table.rename(columns={'month':'الشهر','mean':'متوسط التوقع','lo80':'80% الأدنى','hi80':'80% الأعلى','lo95':'95% الأدنى','hi95':'95% الأعلى'})

if page=='نظرة عامة':
    section('من التاريخ إلى الاستعداد','اقرأ الطلب المتوقع، ثم اختبر إن كانت سعة فريقك تكفي للربع القادم.','shield')
    with st.container(border=True):
        st.subheader('التاريخ يرسم السياق، والنطاق يوضح عدم اليقين')
        st.caption('آخر 24 شهرًا من السجل، يليها توقع ثلاثة أشهر بالنموذج المختار.')
        plot(forecast_figure())
    left,right=st.columns([1,1])
    with left,st.container(border=True):
        st.subheader('قرار النموذج')
        st.markdown(f'<span class="model-tag">{summary["chosen"]}</span>',unsafe_allow_html=True)
        st.write(f'اختير من مقارنة خمسة نماذج على ثماني نوافذ مشتركة. متوسط MASE يساوي {row.MASE:.3f}، وscaled CRPS يساوي {row.scaled_CRPS:.3f}.')
        st.caption('الاختيار بأثر رجعي من التقييم نفسه؛ قد يكون تقدير أدائه متفائلًا.')
    with right,st.container(border=True):
        st.subheader('ماذا يعني ذلك للفريق؟')
        st.write(f'الطلب المتوقع إجمالًا {fc["mean"].sum():.1f} حادثًا، مقابل سعة {sum(capacities):,} حادثًا موزعة على الأشهر الثلاثة.')
        st.write(f'مجموع الفجوات الشهرية عند المتوسط: {plan.gap.sum():.1f} حادثًا. اقرأ الحد الأعلى 80% كسيناريو ضغط، لا كحد أقصى.')
        st.caption('غيّر سعة كل شهر من قسم «تخطيط السعة»؛ تتحدث المؤشرات فورًا.')
    note('الحادث المؤكد لا يعني بالضرورة اختراقًا ناجحًا. لا تستنتج وقوع اختراق من عدد الحوادث وحده.')

elif page=='تحليل الحوادث':
    section('كيف تغيّر حجم الحوادث؟','قراءة الاتجاه الشهري والتفاوت بين السنوات من السجل الفعلي المعروض.','chart')
    with st.container(border=True):
        st.subheader('التسلسل الشهري يوضح الارتفاعات والتذبذب')
        plot(monthly_figure())
    a,b=st.columns([1,1])
    with a,st.container(border=True):
        st.subheader('إجمالي الحوادث لكل سنة')
        annual=data.groupby(data.month.dt.year).confirmed_phishing_incidents.sum()
        fig=go.Figure(go.Bar(x=annual.index.astype(str),y=annual.values,marker_color=CYAN,
            text=annual.values,textposition='outside',cliponaxis=False,hovertemplate='%{x}<br>%{y:,} حادثًا<extra></extra>'))
        plot(theme(fig,330))
        st.caption('عند رفع سجل يتضمن سنة جزئية، يمثل العمود الأشهر المتاحة فقط.')
    with b,st.container(border=True):
        st.subheader('المقارنة الشهرية بين السنوات')
        fig=go.Figure()
        for year,g in data.groupby(data.month.dt.year):
            fig.add_trace(go.Scatter(x=g.month.dt.month,y=g.confirmed_phishing_incidents,name=str(year),mode='lines',line={'width':1.8},hovertemplate='الشهر %{x}: %{y:.0f}<extra>%{fullData.name}</extra>'))
        fig.update_xaxes(tickmode='array',tickvals=list(range(1,13)),ticktext=[str(i) for i in range(1,13)])
        plot(theme(fig,330))
        st.caption('1 = يناير، 12 = ديسمبر. يفصل الرسم تكرار النمط السنوي عن اختلاف مستوى كل سنة.')
    render_shape(data,theme,plot)
    render_residuals(data,summary['chosen'],theme,plot,ROOT,bool(st.session_state.upload_label))

elif page=='التوقعات':
    section('رؤية الأشهر الثلاثة القادمة','فصل واضح بين الماضي والتوقع، مع نطاقين يعرضان اتساع عدم اليقين.','forecast')
    with st.container(border=True):
        st.subheader('المستقبل بعد آخر شهر في السجل')
        st.caption(f'النموذج: \u2066{summary["chosen"]}\u2069 · أفق ثلاثة أشهر · \u2066{forecast_period}\u2069')
        plot(forecast_figure())
        st.caption('مرّر المؤشر على المستقبل لقراءة المتوسط والحدود الفعلية لنطاقي 80% و95%.')
    with st.container(border=True):
        st.subheader('قيم التوقع والنطاقات')
        st.dataframe(forecast_table(),hide_index=True,width='stretch',column_config={c:st.column_config.NumberColumn(format='%.1f') for c in forecast_table().columns if c!='الشهر'})
        st.download_button('تنزيل التوقعات CSV',fc.to_csv(index=False).encode('utf-8-sig'),file_name='Sibrawan-forecast.csv',mime='text/csv')
    note('المتوسط المتوقع قد يكون كسرًا لأنه متوسط طلب، لا عدًّا محققًا. نطاق التنبؤ ليس ضمانًا؛ وقد يتجاوز الطلب حدوده.')
    st.caption('يبدأ أفق التوقع بعد آخر تاريخ في السجل، وليس بعد تاريخ اليوم تلقائيًا. أُعيد تدريب النموذج المختار على كامل السجل الحالي.')

elif page=='مقارنة النماذج':
    section('المقارنة التي تبرر الاختيار','خمسة نماذج، ثماني نوافذ متطابقة، وتقييم النقطة والنطاق معًا.','layers')
    with st.container(border=True):
        st.subheader('نتائج اختبار \u20662024–2025\u2069')
        table=metrics[['model','MASE','scaled_CRPS','coverage_80','width_80']].copy()
        table['coverage_80']*=100
        table=table.rename(columns={'model':'النموذج','scaled_CRPS':'scaled CRPS','coverage_80':'التغطية %','width_80':'عرض نطاق 80%'})
        st.dataframe(table.style.format({'MASE':'{:.3f}','scaled CRPS':'{:.3f}','التغطية %':'{:.1f}','عرض نطاق 80%':'{:.1f}'}).highlight_min(subset=['MASE','scaled CRPS'],color='#e4f4f5'),hide_index=True,width='stretch')
        st.caption('كل المقامات من تدريب النافذة فقط. نطاقات النماذج أصلية دون معايرة على الاختبار.')
    a,b=st.columns(2)
    with a,st.container(border=True):
        st.subheader('الخطأ في توزيع التوقع: الأقل أفضل')
        fig=go.Figure(go.Bar(x=metrics.model,y=metrics.scaled_CRPS,marker_color=[PURPLE if x==summary['chosen'] else CYAN for x in metrics.model],hovertemplate='%{x}<br>scaled CRPS %{y:.3f}<extra></extra>'))
        plot(theme(fig,310))
    with b,st.container(border=True):
        st.subheader('كيف نقرأ المقاييس؟')
        st.write('**MASE ↓** خطأ المتوسط مقارنة بالتغير السنوي المعتاد في التدريب. الأقل أفضل؛ أقل من 1 يتفوق على مقياس التدريب.')
        st.write('**scaled CRPS ↓** جودة توزيع التوقع، وتقريبه من quantiles موضح في الدفتر. الأقل أفضل.')
        st.write('**التغطية ≈ 80%** نسبة المشاهدات داخل النطاق؛ ليست دقة النموذج. الأعلى من 80% ليس أفضل تلقائيًا: قد يعني نطاقًا محافظًا.')
        st.write('**عرض النطاق** بوحدة حادث؛ يوضح تكلفة عدم اليقين، ويُقرأ مع التغطية، لا منفردًا.')
    floor_row=metrics[metrics.model=='SeasonalNaive'].iloc[0]
    note(f'تغطية {summary["chosen"]} المرصودة {row.coverage_80:.1%} بعرض متوسط {row.width_80:.1f} حادثًا، مقابل {floor_row.coverage_80:.1%} وعرض {floor_row.width_80:.1f} لخط الأساس. العينة 24 شهرًا فقط؛ لا تثبت معايرة عامة.')
    with st.expander('الفوز والخسارة حسب النافذة'):
        folds=pd.read_csv(ROOT/'artifacts/fold_scores.csv')
        st.dataframe(folds,hide_index=True,width='stretch')
        baseline=folds[folds.model=='SeasonalNaive'].set_index('fold')
        for name in metrics.model:
            if name=='SeasonalNaive': continue
            candidate=folds[folds.model==name].set_index('fold')
            wins=list(candidate.index[candidate.MASE<baseline.MASE]);losses=list(candidate.index[candidate.MASE>baseline.MASE])
            crps_wins=list(candidate.index[candidate.scaled_CRPS<baseline.scaled_CRPS]);crps_losses=list(candidate.index[candidate.scaled_CRPS>baseline.scaled_CRPS])
            st.write(f'{name}: فوز MASE في النوافذ {wins}، وخسارة {losses}؛ فوز scaled CRPS في {crps_wins}، وخسارة {crps_losses}.')
        st.caption('تفاصيل النوافذ والسياسة التي تختار من الماضي فقط موثقة في الدفتر؛ ترتيب فترة محجوبة واحدة ليس دليلًا نهائيًا.')
    with st.expander('تعريف المقاييس وقاعدة الاختيار ومنع التسرب'):
        st.write('لكل نافذة: d = متوسط |yₜ − yₜ₋₁₂| من تدريب النافذة فقط. MASE = متوسط الخطأ المطلق للاختبار ÷ d. تقريب CRPS = ضعف تكامل خسارة pinball بطريقة شبه المنحرف لعشرة quantiles من 0.025 إلى 0.975، مع افتراض خسارة صفر عند الطرفين 0 و1؛ scaled CRPS = ذلك التقريب ÷ d. ليست CRPS مستمرة دقيقة.')
        st.write('جميع النماذج تستخدم 8 نوافذ تدريب متوسع متطابقة: 48 ثم 51…69 شهرًا؛ h=3 وstep=3. التقدير الداخلي للمعلمات والنطاقات ومقام التطبيع يستعمل تدريب النافذة فقط. الاختيار النهائي الموثق: أقل scaled CRPS بين نماذج تغطيتها ≥80%، وإن لم يوجد فالأقرب إلى 80% ثم الأقل CRPS. هذه مقارنة بأثر رجعي وليست تقييمًا مستقلاً لعملية الاختيار، ولا تتغير القاعدة بناءً على تشخيص البواقي.')
    st.download_button('تنزيل تقرير المدير', (ROOT/'report.pdf').read_bytes(),file_name='Sibrawan-report.pdf',mime='application/pdf')

elif page=='تخطيط السعة':
    section('هل سعة الاستجابة تكفي؟','أدخل عدد الحوادث التي يستطيع الفريق معالجتها في كل شهر، واختبر الفجوة فورًا.','capacity')
    with st.container(border=True):
        st.subheader('سعة الأشهر القادمة')
        cols=st.columns(3)
        for i,col in enumerate(cols):
            with col:
                if f'capacity_{i}' not in st.session_state: st.session_state[f'capacity_{i}']=st.session_state.capacity_values[i]
                st.number_input(f'سعة \u2066{pd.to_datetime(fc.month.iloc[i]):%Y-%m}\u2069 · حادث / شهر',min_value=0,max_value=100000,step=5,key=f'capacity_{i}',on_change=update_capacity,args=(i,))
        capacities=list(st.session_state.capacity_values)
        plan=capacity_plan(fc,capacities)
        st.caption('تتحدث الحسابات بمجرد تغيير المدخلات. السعة منفصلة لكل شهر ولا يُنقل فائض شهر إلى الآخر تلقائيًا.')
    with st.container(border=True):
        st.subheader('المتوسط والسعة وسيناريو الضغط')
        fig=go.Figure()
        labels=pd.to_datetime(fc.month).dt.strftime('%Y-%m')
        fig.add_trace(go.Bar(x=labels,y=fc['mean'],name='متوسط الطلب',marker_color=PURPLE))
        fig.add_trace(go.Bar(x=labels,y=capacities,name='السعة المتاحة',marker_color=CYAN))
        fig.add_trace(go.Scatter(x=labels,y=fc.hi80,name='الحد الأعلى 80%',mode='lines+markers',line={'color':'#536b89','dash':'dot'}))
        fig.update_layout(barmode='group')
        fig.update_xaxes(type='category')
        plot(theme(fig,330))
        table=plan.copy();table.month=pd.to_datetime(table.month).dt.strftime('%Y-%m')
        table=table.rename(columns={'month':'الشهر','mean':'متوسط الطلب','capacity':'السعة','lo80':'80% الأدنى','hi80':'80% الأعلى','gap':'العجز عند المتوسط','stress_gap':'عجز سيناريو الضغط'})
        st.dataframe(table,hide_index=True,width='stretch',column_config={c:st.column_config.NumberColumn(format='%.1f') for c in table.columns if c!='الشهر'})
        st.download_button('تنزيل خطة السعة CSV',plan.to_csv(index=False).encode('utf-8-sig'),file_name='Sibrawan-capacity.csv',mime='text/csv')
    if plan.gap.sum()>0:
        st.warning(f'توجد فجوة عند المتوسط مجموعها {plan.gap.sum():.1f} حادثًا في الأشهر الثلاثة. راجع توزيع السعة والحد الأعلى قبل اعتماد الخطة.')
    else: st.success('السعة تغطي المتوسط المتوقع في الأشهر الثلاثة. راجع سيناريو الحد الأعلى؛ قد يتجاوز الطلب النطاق.')
    note('العجز = max(0، متوسط الطلب − السعة) لكل شهر. هذا مؤشر تخطيطي، وليس متوسط العجز الاحتمالي الكامل. الحد الأعلى 80% ليس أقصى طلب ممكن.')

elif page=='رصد 📡':
    section('رصد 📡 | مساعد سِبرَوان','شرح يستند إلى النتائج الحالية، وإرشاد أولي للحالة دون تشخيص أو تنفيذ تغييرات.','bot')
    st.markdown(f'<div class="chat-intro">{icon("bot")}<div><strong>رصد 📡</strong><small>السياق: {len(data)} شهرًا، توقعات <bdi dir="ltr">{forecast_period}</bdi>، وسعة كل شهر الحالية</small></div></div>',unsafe_allow_html=True)
    state=st.selectbox('نوع التفاعل مع الرسالة', ['غير محدد','رسالة فقط','نقرت رابطًا أو فتحت ملفًا','أدخلت بيانات أو رمز تحقق'],key='incident_state')
    suggestions=['ما توقعات الأشهر القادمة؟','هل سعة الاستجابة تكفي؟','موظف أدخل بياناته في رابط تصيد، ما الخطوات الأولية؟']
    selected=None
    st.caption('ابدأ بسؤال مقترح أو اكتب سؤالك')
    cols=st.columns(3)
    for i,(col,q) in enumerate(zip(cols,suggestions)):
        with col:
            if st.button(q,key=f'suggest_{i}',width='stretch'): selected=q
    if st.session_state.messages:
        st.button('بدء محادثة جديدة',key='clear_chat',on_click=clear_conversation)
    for message in st.session_state.messages:
        with st.chat_message(message['role'],avatar='📡' if message['role']=='assistant' else None): st.markdown(message['content'])
    prompt=st.chat_input('اسأل رصد 📡 عن التوقعات أو السعة أو الاستجابة الأولية…',key='chat_prompt')
    question=selected or prompt
    if question:
        current_state=infer_case(question,state,st.session_state.get('case_state','غير محدد'))
        st.session_state.case_state=current_state
        st.session_state.messages.append({'role':'user','content':question})
        with st.chat_message('user'): st.markdown(question)
        with st.chat_message('assistant',avatar='📡'):
            try:
                with st.spinner('رصد يراجع النتائج وسياق الحالة…'):
                    serial_fc=fc.to_dict('records')
                    cap_by_month={str(r['month'])[:7]:float(c) for r,c in zip(serial_fc,capacities)}
                    context_summary={**summary,'active_history_start':str(data.month.min())[:10],
                        'active_history_end':str(data.month.max())[:10],
                        'active_history_total':int(data.confirmed_phishing_incidents.sum()),
                        'evaluation_scope':'original project history only; not re-evaluated on uploads',
                        'recent_chat_history':st.session_state.messages[-8:],
                        'analysis':{k:v for k,v in history_diagnostics(data).items() if k in ['trend_strength','seasonal_strength','trend_change','seasonal_range','remainder_max']},
                        'fitted_residual_diagnostic':{k:one_step_diagnostics(data,summary['chosen'])[k] for k in ['mean','n','acf_reference']},
                        'uploaded_file_active':bool(st.session_state.upload_label)}
                    answer=ask_gemini(question,current_state,context_summary,metrics.to_dict('records'),serial_fc,cap_by_month)
                st.markdown(answer)
            except Exception:
                from assistant import local_answer
                answer=local_answer(current_state,summary,cap_by_month,metrics.to_dict('records'),serial_fc,question)
                st.warning('تعذر اتصال المساعد الخارجي. ما يلي شرح محلي؛ يمكنك استخدام الدليل والتصعيد للفريق المختص.')
                st.markdown(answer)
        st.session_state.messages.append({'role':'assistant','content':answer})
        if current_state!='غير محدد':
            st.caption('ملخص أولي قابل للنسخ لفريق الأمن — أكمل المعلومات الناقصة عبر قنوات الجهة المعتمدة')
            st.code('ملخص رصد | سِبرَوان\nنوع التفاعل المبلغ عنه: '+current_state+'\nوقت الحدث والحساب المتأثر: غير محددين، يلزم الاستيضاح.\nالمطلوب: تقييم الرسالة والحساب والجهاز وفق خطة الاستجابة.\nلا يوجد تأكيد باختراق ناجح. لم يُنفذ حظر أو تغيير كلمة مرور أو إرسال بلاغ.\nلا تُضمّن كلمات مرور أو رموز تحقق.',language=None)
    with st.expander('الدليل المحلي للاستجابة الأولية والمصادر'):
        guide=(ROOT/'response_guide.md').read_text(encoding='utf-8')
        guide='\n'.join(line for line in guide.splitlines() if not line.startswith('الأرقام المعروضة تجربة اصطناعية'))
        st.markdown(guide)

elif page=='عن البيانات':
    section('عن البيانات وحدود الاستخدام','مصدر السجل وتعريف الحادث، وما يمكن وما لا يمكن استنتاجه من هذه التجربة.','info')
    with st.container(border=True):
        st.subheader('مصدر سجل المشروع')
        st.write('بيانات المشروع **اصطناعية**: 72 شهرًا من يناير 2020 إلى ديسمبر 2025، ولّدت بـseed ثابت 20261014، مع افتراض اتجاه وموسمية وضوضاء وقفزات. لم تتغير البيانات لإجبار نموذج على الفوز.')
        st.write('هذه تجربة تعليمية لتخطيط سعة الاستجابة، ولا تثبت القدرة على توقع هجمات حقيقية. الحادث المؤكد لا يعني بالضرورة اختراقًا ناجحًا. الإفصاح الكامل محفوظ أيضًا في الدفتر والتقرير.')
        st.caption('الملف المرفوع إن وُجد يُستخدم لهذه الجلسة فقط؛ مصدره ومسؤوليته يعودان للمستخدم. لا يتحول تلقائيًا إلى بيانات موثوقة أو تقييم معتمد.')
    with st.container(border=True):
        st.subheader('رفع سجل جديد دون تغيير أدلة التسليم')
        st.write('العمودان: `month` و`confirmed_phishing_incidents`. كل شهر مرة واحدة، دون أشهر مفقودة؛ القيم صحيحة وغير سالبة، و48 شهرًا على الأقل. يرتّب التطبيق الصفوف زمنيًا ويعيد تدريب النموذج المختار لهذا السجل فقط.')
        st.write('رسوم التاريخ والتوقعات والسعة وسياق المساعد تتحدث مع السجل المرفوع. جدول مقارنة النماذج والتغطية يشيران دائمًا إلى التقييم الأصلي، ولا تُعاد كتابة البيانات أو مخرجات الدفتر أو التقرير.')
        st.download_button('تنزيل نموذج CSV', (ROOT/'data/synthetic_phishing.csv').read_bytes(),file_name='monthly-incidents-template.csv',mime='text/csv')
    with st.container(border=True):
        st.subheader('التقييم والقرار')
        st.write('ثماني نوافذ تدريب متوسع، h=3 وstep=3، وتدريب أول من 48 شهرًا. نتائج التقييم تشمل MASE وscaled CRPS والتغطية والعرض. المقامات من تدريب كل نافذة فقط. النموذج النهائي اختير بعد المقارنة، وأعيد تدريبه على كامل السجل.')
        st.write('24 مشاهدة اختبار لا تكفي لإثبات معايرة عامة. التغطية أعلى من 80% قد تعني نطاقًا محافظًا، لا دقة أعلى. الخطوة التالية بيانات حقيقية محددة التعريف واختبار متغير حجم الرسائل المتأخر.')
        st.download_button('تقرير المدير PDF', (ROOT/'report.pdf').read_bytes(),file_name='Sibrawan-report.pdf',mime='application/pdf')
    with st.expander('الدليل المحلي والمصادر الرسمية'):
        st.markdown((ROOT/'response_guide.md').read_text(encoding='utf-8'))

st.markdown('<div class="footer"><span>سِبرَوان | Sibrawan · رؤية أوضح للاستجابة</span><span>منهج التحليل ونتائج الاختبارات محفوظة في الدفتر والتقرير</span></div>',unsafe_allow_html=True)
if st.session_state.pop('scroll_top',False):
    st.html('''<script>requestAnimationFrame(()=>{const main=document.querySelector('[data-testid="stMain"]');if(main)main.scrollTo({top:0,behavior:'instant'});});</script>''',unsafe_allow_javascript=True)
