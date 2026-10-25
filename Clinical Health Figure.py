"""Figure 5 from the released BUTTERFLY and COMPASS datasets."""
from pathlib import Path
import json, runpy, textwrap
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter, MaxNLocator
import numpy as np
import pandas as pd
from panel_exports import export_panels
from bloom_data import load_butterfly, load_compass, prepare_diagnoses, diagnosis_counts, head_measurements
HERE=Path(__file__).resolve().parent
OUT=HERE/'Figures/Clinical Health'
NAME='PAN Paper Figure 5 - Clinical Health'
def analyte_label(name):
    acronyms = {'WBC', 'RBC', 'MCV', 'MCH', 'MCHC', 'RDW', 'PO2', 'PCO2', 'POCT', 'PTT'}
    return ' '.join(word if word in acronyms else 'pH' if word == 'PH'
                    else word.lower() if word in {'AND', 'WITH', 'OF'}
                    else word.capitalize() for word in str(name).replace('CAPILALRY', 'CAPILLARY').split())

def laboratory_summary(raw):
    """Rank abnormal laboratory analytes and select the ten shown in Figure 5.

    Analytes are ranked by High/Low Panic counts, then by total abnormal
    results, with stable tie ordering. TEST_NAME_ORIG is the analyte field in
    this workbook. All source rows are used, without a cohort join,
    result/date filters, or deduplication.
    """
    flags = raw.RESULT_CHARACTERIZATION
    eligible = (flags.notna()
                & ~flags.isin(['NULL', 'NA', '(NONE)', 'Final Result', 'Routine'])
                & flags.str.lower().ne('normal'))
    data = raw.loc[eligible & raw.TEST_NAME_ORIG.notna()]
    totals = data.groupby('TEST_NAME_ORIG', sort=True).size().rename('Total_Abnormal')
    flags_by_name = pd.crosstab(data.TEST_NAME_ORIG, data.RESULT_CHARACTERIZATION)
    summary = totals.to_frame().join(flags_by_name.reindex(
        columns=['Low', 'High', 'Low Panic', 'High Panic'], fill_value=0))
    summary['Total_Panic'] = summary['Low Panic'] + summary['High Panic']
    summary['Displayed_Total'] = summary.Low + summary.High
    # Rank by total abnormal results, then by panic results, keeping ties stable.
    summary = summary.sort_values('Total_Abnormal', ascending=False, kind='stable')
    summary = summary.sort_values('Total_Panic', ascending=False, kind='stable')
    summary['Selection_Rank'] = np.arange(1, len(summary) + 1)
    selected = summary.head(10).sort_values('Displayed_Total', ascending=False, kind='stable')
    if len(selected) != 10 or not selected.Displayed_Total.gt(0).all():
        raise ValueError('Expected 10 selected analytes with nonzero High/Low counts.')
    summary.index.name = selected.index.name = 'Analyte'
    return summary, selected

def table(ax, data, heading, count_heading='Children'):
    ax.set_axis_off()
    t = ax.table(cellText=[[textwrap.fill(str(k), 32), f'{v:,}'] for k,v in data.items()],
                 colLabels=[heading, count_heading], colWidths=[.81,.19],
                 cellLoc='left', colLoc='left', bbox=[0,0,1,1])
    t.auto_set_font_size(False)
    t.set_fontsize(6)
    for (r,c), cell in t.get_celld().items():
        cell.set_linewidth(0)
        cell.PAD=.025
        cell.set_facecolor('#EDF5F5' if r % 2 else 'white')
        if r == 0:
            cell.set_text_props(weight='bold', color='#00383B')
        if c == 1:
            cell.get_text().set_ha('right')

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    shared = runpy.run_path(str(HERE/'Placement Figure.py'))
    manual = load_butterfly(); n=len(manual)
    sheets = load_compass(manual.Subject_ID)
    dx, diagnosis_audit, labels, prepared_rows = prepare_diagnoses(sheets)
    counts, fcounts, top = diagnosis_counts(dx,n)
    counts.rename('Children').to_csv(OUT/'icd10_chapter_counts.csv')
    fcounts.rename('Children').to_csv(OUT/'mental_health_counts.csv')
    top.to_csv(OUT/'top_30_diagnoses.csv',index=False)
    labels.to_csv(OUT/'code_labels.csv',index=False)
    (OUT/'diagnosis_preparation_audit.json').write_text(json.dumps(diagnosis_audit,indent=2,default=int))
    vit, eligibility, eligible_records = head_measurements(sheets['Vitals'],manual)
    eligibility.to_csv(OUT/'head_circumference_eligibility.csv',index=False)
    hist_counts, hist_edges = np.histogram(vit.hc, bins=np.arange(30,62,2))
    pd.DataFrame({'Lower_HC_cm':hist_edges[:-1],'Upper_HC_cm':hist_edges[1:],'Children':hist_counts}).to_csv(OUT/'head_circumference_histogram.csv',index=False)
    assert int(hist_counts.sum())==len(vit)
    measurement_counts=vit.set_index('key').Measurements
    longitudinal_children=int(measurement_counts.ge(2).sum())
    single_measurement_children=int(measurement_counts.eq(1).sum())
    # No patient identifiers or individual measurements are exported.
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':6,'axes.titlesize':8,
                         'axes.titleweight':'bold','axes.labelsize':7,'xtick.labelsize':6,
                         'ytick.labelsize':6,'svg.fonttype':'none'})
    fig = plt.figure(figsize=(7.48,9))
    a=fig.add_axes([.06,.715,.43,.25]); c=fig.add_axes([.56,.715,.40,.25])
    # Increase row pitch while keeping the physical bar thickness constant.
    row_spacing = 1.12
    original_height = .335
    panel_height = original_height * ((len(top)-1)*row_spacing + .8) / ((len(top)-1) + .8)
    b=fig.add_axes([.56,.31,.40,panel_height])
    d=fig.add_axes([.28,.035,.21,.19]); e=fig.add_axes([.66,.035,.30,.19])
    table(a,counts,'ICD-10 Chapter', count_heading='Children (n)'); table(c,fcounts,'Mental Health Group', count_heading='Children (n)')
    a.set_title('Diagnoses by ICD-10 Chapter', pad=9)
    c.set_title('Mental Health Diagnoses by Category', pad=9)
    for ax in (b,d,e):
        shared['style'](ax)
    labels=[textwrap.shorten(str(row.Diagnosis), width=82, placeholder='…') for row in top.itertuples()]
    positions = np.arange(len(top)) * row_spacing
    # Remove the default 5% vertical margins to spread rows within the same panel.
    # Scale data-unit bar height to preserve its physical thickness.
    b.barh(positions, top.Prevalence, height=.8 / 1.1, color='#007B80')
    b.set_ylim(positions[-1] + .4, positions[0] - .4)
    b.set_xlim(0, top.Prevalence.max() * 1.4)
    for y, row in zip(positions, top.itertuples()):
        b.annotate(f'{row.Children:,} ({row.Prevalence:.1%})',
                   xy=(row.Prevalence, y), xytext=(3, 0),
                   textcoords='offset points', va='center', fontsize=6)
    b.set_yticks(positions, labels, fontsize=6)
    b.xaxis.set_major_formatter(PercentFormatter(1)); b.set_xlabel('Cohort with Recorded Diagnosis (%)'); b.set_ylabel('Diagnosis')
    b.set_title('Top 30 Recorded Diagnoses',pad=9)
    d.set_title('Abnormal Laboratory Results by Analyte', x=.28, pad=12)
    lab_ranking, labs = laboratory_summary(sheets['Labs'])
    lab_ranking.to_csv(OUT/'lab_analyte_ranking.csv')
    labs.to_csv(OUT/'abnormal_lab_counts.csv')
    d.barh(labs.index,labs.Low,color='#7FDFE2',label='Low')
    d.barh(labs.index,labs.High,left=labs.Low,color='#00383B',label='High')
    d.set_yticks(np.arange(len(labs)), [analyte_label(name) for name in labs.index])
    totals = labs.Displayed_Total
    d.set_xlim(0, totals.max() * 1.25)
    for y, total in enumerate(totals):
        d.annotate(f'{total:,}', xy=(total, y), xytext=(3, 0),
                   textcoords='offset points', va='center', fontsize=6)
    d.tick_params(axis='y',labelsize=6)
    d.set_xlabel('Number of Abnormal Analyte Results')
    d.set_ylabel('Laboratory Analyte')
    d.legend(frameon=False,fontsize=6.5)
    d.xaxis.set_major_locator(MaxNLocator(nbins=3, integer=True))
    e.hist(vit.hc,bins=np.arange(30,62,2),color='#007B80',edgecolor='#555555',linewidth=.5)
    e.set(xlim=(30,60),xlabel='Head Circumference (cm)',ylabel='Number of Children')
    e.set_title('Head Circumference Distribution',pad=12)
    e.yaxis.set_major_locator(MaxNLocator(integer=True,nbins=4))
    e.set_xticks([30,40,50,60])
    panels={}
    for ax,letter,title,pos in [(a,'a','ICD-10 Chapters',(.025,.978)),(b,'b','Top 30 Diagnoses',(.025,.70)),(c,'c','Mental Health Diagnoses',(.525,.978)),(d,'d','Abnormal Laboratory Results',(.025,.245)),(e,'e','Head Circumference',(.525,.245))]:
        txt=fig.text(*pos,letter,fontsize=14,weight='bold',color='black')
        panels[f'{letter} - {title}']=([ax],[txt])
    fig.savefig(OUT/f'{NAME}.png',dpi=300,transparent=True)
    fig.savefig(OUT/f'{NAME} - White Background.png',dpi=300,facecolor='white')
    fig.savefig(OUT/f'{NAME}.svg',transparent=True)
    export_panels(fig, OUT, NAME, panels)
    plt.close(fig)
    summary={'cohort_n':n,'source_diagnosis_children':diagnosis_audit['children_with_source_diagnosis_information'],
      'prepared_diagnosis_children':int(dx.subject.nunique()),'prepared_child_code_pairs':len(dx),
      'F_code_children':int(dx[dx.code.str.startswith('F')].subject.nunique()),
      'top30_children':int(dx[dx.code.str.startswith('F') & dx.label.isin(top.Diagnosis)].subject.nunique()),
      'lab_source_rows':len(sheets['Labs']),'lab_source_children':int(sheets['Labs'].SUBJECT_ID.nunique()),
      'lab_displayed_occurrences':int(labs.Displayed_Total.sum()),
      'lab_displayed_children':int(sheets['Labs'].loc[sheets['Labs'].TEST_NAME_ORIG.isin(labs.index)&sheets['Labs'].RESULT_CHARACTERIZATION.isin(['Low','High']),'SUBJECT_ID'].nunique()),
      'eligible_HC_measurement_rows':len(eligible_records),'HC_child_medians':len(vit),'HC_children':int(vit.key.nunique()),
      'HC_children_with_multiple_measurements':longitudinal_children,'HC_children_with_single_measurement':single_measurement_children,
      'HC_children_with_repeated_measurements':int(vit.Measurements.gt(1).sum()),
      'HC_children_with_different_measurements':int(vit.Minimum.ne(vit.Maximum).sum())}
    (OUT/'figure5_summary.json').write_text(json.dumps(summary,indent=2))
    print(json.dumps(summary,indent=2))
    return summary

if __name__=='__main__': main()
