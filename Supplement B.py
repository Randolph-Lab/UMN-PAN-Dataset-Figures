"""Generate Supplement B with emphasized counts."""
from pathlib import Path
import csv
import json
import numpy as np
import pandas as pd
import io
import xml.etree.ElementTree as ET
from PIL import Image
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from bloom_data import load_butterfly

HERE = Path(__file__).resolve().parent
OUT = HERE/'Figures'/'Supplement B'
ETHNICITY_MAPPING = HERE/'References'/'ethnicity_mapping.json'
HISTORIES = [
    ('International\nadoption', 'International_adoption'),
    ('Domestic\nadoption', 'Domestic_adoption'),
    ('Foster to\nadopt', 'Foster_to_adopt_adoption'),
    ('Foster care\nsystem', 'Foster_care_system'),
    ('Traditional', 'Traditional'), ('Kinship\ncare', 'Kinship_care'),
    ('Group\nhome', 'Group_home'), ('Institutional\ncare', 'Institutional_care'),
    ('Orphanage\ncare', 'Orphanage_care'), ('Respite\ncare', 'Respite_care')]


def load_ethnicity_mapping():
    rules = json.loads(ETHNICITY_MAPPING.read_text(encoding='utf-8'))
    if not isinstance(rules, list):
        raise ValueError(f'{ETHNICITY_MAPPING} must contain a list of category rules.')
    mapping = {}
    for rule in rules:
        if (not isinstance(rule, dict)
                or not isinstance(rule.get('category'), str)
                or not isinstance(rule.get('values'), list)
                or not all(isinstance(value, str) for value in rule['values'])):
            raise ValueError(f'Invalid ethnicity category rule in {ETHNICITY_MAPPING}: {rule!r}')
        for value in rule['values']:
            mapping.setdefault(value, rule['category'])
    if mapping.get('Marshallese') != 'Asian':
        raise ValueError(f'{ETHNICITY_MAPPING} must preserve the first-match Marshallese category of Asian.')
    return mapping


def calculate():
    df = load_butterfly()
    assert len(df) == 2720
    sex = df.Sex.astype('string').str.strip()
    race = df.Race.astype('string').str.strip().replace({
        'Unknown / Not Reported': 'Other / Unclassified',
        'Native Hawaiian or Other Pacific Islander': 'Pacific Islander'})
    mapping = load_ethnicity_mapping()
    ethnicity = df.Ethnicity.astype('string').str.strip().map(mapping).fillna('Other / Unclassified')
    ethnicity = ethnicity.mask(df.Ethnicity.isna(), 'Unknown / Not Reported')
    months = pd.to_numeric(df.Age_at_adoption, errors='coerce')
    adopted = df.Was_this_child_adopted_at_time_of_amc_visit.astype('string').str.strip().str.lower().eq('yes').fillna(False)
    eligible = months.notna() | adopted
    age = pd.Series(pd.cut(months / 12, [-np.inf, 5, 10, 15, np.inf], right=False,
        labels=['Under 5', '5–<10', '10–<15', '15–21']), index=df.index).astype('string')
    age = age.mask(months.isna() & adopted, 'Unknown age')
    assert eligible.sum() == 1706
    groups = [('Sex', sex, ['Male', 'Female']),
        ('Race', race, ['White', 'Black or African American', 'Asian', 'American Indian/Alaska Native', 'Other / Unclassified', 'Pacific Islander']),
        ('Ethnicity group', ethnicity, ['White', 'Black or African American', 'Asian', 'Other / Unclassified', 'American Indian/Alaska Native', 'Pacific Islander', 'Unknown / Not Reported']),
        ('Age at adoption (years)', age, ['Under 5', '5–<10', '10–<15', '15–21', 'Unknown age'])]
    columns = [('Overall', 'All', pd.Series(True, index=df.index))]
    for label, field in HISTORIES:
        values = df[field].astype('string').str.strip().str.lower()
        assert values.isin(['yes', 'no']).all(), f'Unexpected or missing value: {field}'
        for answer in ['Yes', 'No']:
            columns.append((label.replace('\n', ' '), answer, values.eq(answer.lower())))
    records, display = [], []
    def append(group, category, series=None):
        cells = []
        for label, answer, mask in columns:
            denominator = int((mask & eligible).sum()) if group == 'Age at adoption (years)' else int(mask.sum())
            count = int(mask.sum()) if series is None else int((mask & series.eq(category).fillna(False)).sum())
            percent = 100 * count / denominator if denominator else None
            records.append(dict(Characteristic=group, Category=category, History=label, Response=answer,
                Count=count, Denominator=denominator, Percent=percent))
            cells.append(f'{count:,}' if series is None else f'{count:,} ({percent:.1f})' if percent is not None else '—')
        display.append((group, category, cells))
    append('Overall cohort', '')
    for group, series, categories in groups:
        for category in categories:
            append(group, category, series)
        for label, answer, mask in columns:
            subset = [r for r in records if r['Characteristic'] == group and r['History'] == label and r['Response'] == answer]
            assert sum(r['Count'] for r in subset) == subset[0]['Denominator']
    return records, display


def render(rows,histories):
    # A4 landscape at native size; stack counts and percentages for legibility.
    width,height=11.7,8.3
    plt.rcParams.update({'font.family':'DejaVu Sans','svg.fonttype':'none','pdf.fonttype':42})
    fig=plt.figure(figsize=(width,height)); ax=fig.add_axes([0,0,1,1])
    ax.set(xlim=(0,width),ylim=(0,height)); ax.set_axis_off()
    left,right=.25,width-.25; label_end=2.65; cell=(right-label_end)/21
    teal='#00383B'; artists=[]; cells=[]
    def txt(x,y,s,**kw):
        a=ax.text(x,y,s,**kw); artists.append(a); return a
    txt(left,height-.19,'Supplement B. Demographic Characteristics by Adoption and Placement History',fontsize=10,weight='bold',va='top')
    top=height-.48; hh=.55
    ax.add_patch(Rectangle((left,top-hh),right-left,hh,color=teal,lw=0))
    ax.add_patch(Rectangle((label_end,top-hh),cell,hh,color='#176064',lw=0))
    txt(left+.05,top-hh/2,'Characteristic / category',fontsize=8,color='white',weight='bold',va='center')
    txt(label_end+cell/2,top-hh/2,'Overall',fontsize=6.7,color='white',weight='bold',ha='center',va='center')
    for j,(label,_) in enumerate(histories):
        x=label_end+cell*(1+2*j)
        txt(x+cell,top-.19,label,fontsize=6.7,color='white',weight='bold',ha='center',va='center',linespacing=1.08)
        for k,answer in enumerate(['Yes','No']):
            txt(x+cell*(k+.5),top-.45,answer,fontsize=6.8,color='white',ha='center',va='center')
    value_pairs=[]
    y=top-hh; previous=None; row_h=.285
    for i,(group,category,values) in enumerate(rows):
        if group!=previous and group!='Overall cohort':
            gh=.24
            ax.add_patch(Rectangle((left,y-gh),right-left,gh,color='#DCECEE',lw=0))
            txt(left+.05,y-gh/2,group,fontsize=8,weight='bold',va='center')
            y-=gh
        if i%2==0: ax.add_patch(Rectangle((left,y-row_h),right-left,row_h,color='#F0F8F8',lw=0))
        ax.add_patch(Rectangle((label_end,y-row_h),cell,row_h,color='#DFEFF0',lw=0))
        a=txt(left+.05,y-row_h/2,category or group,fontsize=7.8,weight='bold' if group=='Overall cohort' else 'normal',va='center')
        cells.append((a,left,label_end,y-row_h,y))
        for j,value in enumerate(values):
            x=label_end+cell*(j+.5)
            if ' (' in value:
                count,percentage=value.split(' ',1)
                count_artist=txt(x,y-row_h/2+.052,count,fontsize=7.8,ha='center',va='center',weight='bold',color='#111111')
                percent_artist=txt(x,y-row_h/2-.052,percentage,fontsize=6.7,ha='center',va='center',color='#505050')
                value_pairs.append((count_artist,percent_artist))
                body_artists=[count_artist,percent_artist]
            else:
                body_artists=[txt(x,y-row_h/2,value,fontsize=7.8,ha='center',va='center',weight='bold',color='#111111')]
            for a in body_artists:
                cells.append((a,label_end+cell*j,label_end+cell*(j+1),y-row_h,y))
        y-=row_h; previous=group
    assert y>.25
    for j in [0,1]+[1+2*k for k in range(1,11)]:
        x=label_end+cell*j
        ax.plot([x,x],[y,top],color='#9DBFC1',lw=.45)
    ax.plot([left,right],[y,y],color=teal,lw=.7)
    fig.canvas.draw(); renderer=fig.canvas.get_renderer()
    for a in artists:
        b=a.get_window_extent(renderer)
        assert fig.bbox.contains(b.x0,b.y0) and fig.bbox.contains(b.x1,b.y1),a.get_text()
    for a,x0,x1,y0,y1 in cells:
        b=a.get_window_extent(renderer); lo=ax.transData.transform((x0,y0)); hi=ax.transData.transform((x1,y1))
        assert b.x0>=lo[0] and b.x1<=hi[0] and b.y0>=lo[1] and b.y1<=hi[1],a.get_text()
    for count,percentage in value_pairs:
        assert not count.get_window_extent(renderer).overlaps(percentage.get_window_extent(renderer)),count.get_text()
    # Header bounds and pairwise overlap checks (two levels have distinct y positions).
    header=[a for a in artists if a.get_position()[1]>top-hh]
    for i,a in enumerate(header):
        for b in header[i+1:]:
            assert not a.get_window_extent(renderer).overlaps(b.get_window_extent(renderer)),(a.get_text(),b.get_text())
    # Rotate the entire completed figure 90 degrees clockwise, without cropping.
    buffer=io.BytesIO()
    fig.savefig(buffer,format='svg',facecolor='white')
    root=ET.fromstring(buffer.getvalue())
    ns='http://www.w3.org/2000/svg'
    ET.register_namespace('',ns)
    scale=9.0/width
    old_width,old_height=width*72,height*72
    root.set('width',f'{old_height*scale}pt'); root.set('height',f'{old_width*scale}pt')
    root.set('viewBox',f'0 0 {old_height} {old_width}')
    group=ET.Element(f'{{{ns}}}g',{'transform':f'translate({old_height},0) rotate(90)'})
    for child in list(root):
        root.remove(child); group.append(child)
    root.append(group)
    ET.ElementTree(root).write(OUT/'Supplement B.svg',encoding='utf-8',xml_declaration=True)
    for transparent,suffix in [(False,' - White Background'),(True,'')]:
        buffer=io.BytesIO()
        fig.savefig(buffer,format='png',dpi=600,transparent=transparent,facecolor='none' if transparent else 'white')
        buffer.seek(0)
        with Image.open(buffer) as im:
            rotated=im.transpose(Image.Transpose.ROTATE_270)
            rotated.resize((round(height*scale*600),5400),Image.Resampling.LANCZOS).save(OUT/f'Supplement B{suffix}.png',dpi=(600,600))
    plt.close(fig)


def main():
    records,rows=calculate(); histories=HISTORIES
    OUT.mkdir(parents=True,exist_ok=True)
    render(rows,histories)
    with (OUT/'Supplement B.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(records[0])); w.writeheader(); w.writerows(records)

if __name__=='__main__': main()
