"""Three fixed pages, all numeric evidence supplied by notebook execution."""
from pathlib import Path
from html import escape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from pypdf import PdfReader

def build_report(metrics, final, summary):
    chosen=summary['chosen']; row=metrics.loc[chosen]; floor=metrics.loc['SeasonalNaive']
    sections=[
        ('1. Decision and evidence',[
            summary['recommendation'],
            'Sibrawan | Mashael Alotaibi. This is a synthetic experiment on 72 monthly counts, January 2020-December 2025. A confirmed phishing incident need not be a successful compromise. The evidence does not establish an ability to predict real attacks.',
            f"The series has a rising level and recurring annual variation. STL trend strength is {summary['trend_strength']:.3f} and seasonal strength {summary['seasonal_strength']:.3f}. Raw annual-lag correlation is {summary['acf12']:.3f} at 12 months and {summary['acf24']:.3f} at 24 months; trend also contributes to that correlation.",
            'We compared five real classical models in StatsForecast, an allowed alternative to AutoGluon. Eight expanding quarterly tests use exactly the same dates for every candidate: first history January 2020-December 2023; tests cover all quarters of 2024-2025, three months per quarter. No fold sees its future. The late three-month leaderboard is descriptive, not final ranking evidence.',
            'MASE measures forecast error relative to typical year-on-year training change; below one beats that training scale. Scaled CRPS scores the prediction distribution (smaller is better), approximated from ten quantiles with trapezoidal integration and zero endpoint losses, divided by each fold\'s training seasonal-change scale. Both scores are equal means over eight tests.',
        ]),
        ('2. Bands and what the forecasts missed',[
            f"The floor covers {floor.coverage_80:.1%} of held-out observations with mean 80% band width {floor.width_80:.1f} incidents. {chosen} covers {row.coverage_80:.1%}, width {row.width_80:.1f}. Below 80% is observed undercoverage; above it is conservative observed coverage. A narrow band is useful only when it covers adequately. With 24 targets, one observation changes coverage by 4.17 percentage points, so this is limited evidence of calibration.",
            'Final-model selection was declared as lowest scaled CRPS among candidates covering at least 80%; if none qualified, nearest coverage then lowest CRPS. It is a retrospective choice on these tests, so its own reported performance may be optimistic. The notebook separately evaluates an adaptive policy selecting only from previously completed folds.',
            'Floor annual-difference residuals: '+summary['floor_read']+'. Positive mean exposes missed growth; differencing can induce negative annual-lag correlation. Trend-aware methods can address bias, while shocks can remain unexplained.',
            'Quarterly forecast-error diagnostics: '+'; '.join(k+': '+v for k,v in summary['residuals'].items())+'. These errors mix three horizons and quarterly refits; their ACF is descriptive, not a formal independence test. Surges outside the bands are capacity risk. Values inside approximate ACF references do not prove randomness.',
        ]),
        ('3. Next-quarter capacity and development',[
            f'The selected {chosen} model is refitted on the complete unchanged record. The next months are January-March 2026, immediately after December 2025, rather than after the submission date. Forecast means may be fractional because they are expected counts. Prediction bands quantify uncertainty, not a guarantee.',
            'Use the mean for ordinary workload planning and compare available response capacity with the upper 80% bound for a stress scenario. The upper bound is not a maximum; a larger surge is possible. The interface reports max(0, forecast mean - capacity), a planning proxy rather than the expected positive part of a full demand distribution.',
            'One specific next step: collect consistently defined real monthly confirmed-incident counts and incoming suspicious-message volume; then backtest a lagged-volume regression against the same quarterly floor. Training-only driver joins are essential. This may explain workload surges; validation on real data is required before any operational recommendation.',
            'Reproducibility: fixed seed 20261014, committed generator/CSV, clean-kernel notebook, identical rolling origins, training-only denominators and native model bands. No test-driven generator edits, interval calibration or hidden fallback model. API credentials are not needed for analysis. Optional Gemini explains saved numbers and offers sourced initial-response guidance; it cannot diagnose compromise or perform changes.',
        ])]
    styles=getSampleStyleSheet()
    styles['BodyText'].fontSize=9; styles['BodyText'].leading=11.5
    story=[]; md=['# Sibrawan - Manager report','Mashael Alotaibi','']
    for i,(title,paragraphs) in enumerate(sections):
        if i: story.append(PageBreak())
        story.append(Paragraph('SIBRAWAN | '+title,styles['Heading1']))
        for p in paragraphs:
            story.extend([Paragraph(escape(p),styles['BodyText']),Spacer(1,7)])
        md.extend(['## '+title,'',*sum(([p,''] for p in paragraphs),[])])
        if i==0:
            data=[['Model','MASE','Scaled CRPS','80% cover','80% width']]
            for name,r in metrics.iterrows(): data.append([name,f'{r.MASE:.3f}',f'{r.scaled_CRPS:.3f}',f'{r.coverage_80:.1%}',f'{r.width_80:.1f}'])
            table=Table(data,colWidths=[105,65,85,85,85]); table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#142848')),('TEXTCOLOR',(0,0),(-1,0),colors.white),('FONTSIZE',(0,0),(-1,-1),9),('BOTTOMPADDING',(0,0),(-1,-1),7),('GRID',(0,0),(-1,-1),.3,colors.lightgrey)])); story.append(table)
            md+=['| Model | MASE | Scaled CRPS | 80% coverage | 80% width |','|---|---:|---:|---:|---:|']+['| '+' | '.join(x)+' |' for x in data[1:]]+['']
            for p in summary['comparisons']:
                story.extend([Spacer(1,5),Paragraph(escape(p),styles['BodyText'])]); md +=[p,'']
        if i==1: story.append(Image('artifacts/model_residuals.png',width=460,height=268))
        if i==2:
            data=[['Month','Mean','80% low','80% high','95% low','95% high']]
            for _,r in final.iterrows(): data.append([r.month.strftime('%Y-%m')]+[f'{r[c]:.1f}' for c in ['mean','lo80','hi80','lo95','hi95']])
            story.append(Table(data,colWidths=[85,60,65,65,65,65],style=[('GRID',(0,0),(-1,-1),.3,colors.lightgrey),('FONTSIZE',(0,0),(-1,-1),9)]))
            story.extend([Spacer(1,10),Image('artifacts/final_forecast.png',width=460,height=185)])
            md+=['| Month | Mean | 80% low | 80% high | 95% low | 95% high |','|---|---:|---:|---:|---:|---:|']+['| '+' | '.join(x)+' |' for x in data[1:]]+['','![Quarterly residual evidence](artifacts/model_residuals.png)','![Final forecast](artifacts/final_forecast.png)']
    def footer(c,doc):
        c.setFont('Helvetica',8); c.drawString(40,25,'Sibrawan - synthetic experiment only'); c.drawRightString(A4[0]-40,25,str(doc.page))
    SimpleDocTemplate('report.pdf',pagesize=A4,rightMargin=40,leftMargin=40,topMargin=35,bottomMargin=40).build(story,onFirstPage=footer,onLaterPages=footer)
    assert len(PdfReader('report.pdf').pages)==3, 'Report must be exactly three pages; adjust layout'
    Path('report.md').write_text('\n'.join(md),encoding='utf-8')
