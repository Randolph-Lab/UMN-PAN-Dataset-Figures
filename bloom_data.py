"""Shared loaders for the released BLOOM datasets."""
from pathlib import Path
from collections import Counter
import hashlib, os, re, tempfile
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
INPUT = HERE / 'Input Data'
DATA = Path(os.environ.get('BLOOM_DATA_DIR', INPUT))
REF = HERE / 'References'
OUT = HERE / 'Figures/Clinical Health'
CHAPTERS = {'A':'Infectious diseases','B':'Infectious diseases','C':'Neoplasms',
'E':'Endocrine disorders','F':'Mental and behavioural disorders','G':'Nervous system diseases',
'I':'Circulatory system diseases','J':'Respiratory system diseases','K':'Digestive system diseases',
'L':'Skin diseases','M':'Musculoskeletal diseases','N':'Genitourinary diseases',
'O':'Pregnancy and childbirth','P':'Perinatal conditions','Q':'Congenital conditions',
'R':'General symptoms','S':'Injuries and consequences','T':'Injuries and consequences',
'V':'External causes','W':'External causes','X':'External causes','Y':'External causes',
'Z':'Factors influencing health','U':'Special purposes'}
F_GROUPS = ['Organic mental disorders','Substance use disorders','Schizophrenia and psychotic disorders',
'Mood disorders','Anxiety and related disorders','Behavioral syndromes','Personality disorders',
'Intellectual disabilities','Developmental disorders','Childhood behavioral disorders']
ALIASES = {'Born_in_america':'Was_this_child_born_in_america',
'Adopted_by_AMC_visit':'Was_this_child_adopted_at_time_of_amc_visit','Cannabis':'Marijuana'}

def read_released_excel(name, sheet):
    source = DATA / name
    key = hashlib.sha256(repr((str(source.resolve()), source.stat().st_mtime_ns, source.stat().st_size, sheet)).encode()).hexdigest()
    cache = Path(tempfile.gettempdir()) / 'bloom-released-figure-cache'
    cache.mkdir(mode=0o700, exist_ok=True)
    target = cache / (key+'.pkl')
    if target.exists(): return pd.read_pickle(target)
    result = pd.read_excel(source, sheet_name=sheet)
    result.to_pickle(target); target.chmod(0o600)
    return result

def load_butterfly():
    df = pd.read_csv(DATA/'BLOOM_BUTTERFLY.csv', low_memory=False)
    df = df[df.Subject_ID.notna()].copy()
    df['Subject_ID'] = df.Subject_ID.astype(str).str.strip()
    if not df.Subject_ID.str.fullmatch(r'[A-Z]\d+').all() or df.Subject_ID.duplicated().any():
        raise ValueError('BUTTERFLY must contain one nonblank valid ID per child.')
    # Compatibility aliases are translations of released fields, not imputed data.
    for released, legacy in ALIASES.items(): df[legacy] = df[released]
    return df.reset_index(drop=True)

def load_compass(cohort=None):
    cohort = set(load_butterfly().Subject_ID) if cohort is None else set(cohort)
    sheets = {}
    for sheet in ['Vitals','Problems','Diagnoses','Labs']:
        df = read_released_excel('BLOOM_COMPASS.xlsx', sheet).copy()
        df['source_row'] = df.index + 2
        df['SUBJECT_ID'] = df.SUBJECT_ID.astype('string').str.strip()
        if not set(df.SUBJECT_ID.dropna()) <= cohort:
            raise ValueError(f'{sheet}: subjects outside the BUTTERFLY cohort require review.')
        sheets[sheet] = df[df.SUBJECT_ID.isin(cohort)].copy()
    return sheets

def code10(value):
    if pd.isna(value): return None
    value = str(value).strip().upper().replace('.','')
    if not re.fullmatch(r'[A-Z][0-9][0-9A-Z]{1,5}', value): return None
    return value if len(value)==3 else value[:3]+'.'+value[3:]

def key9(value):
    if pd.isna(value): return None
    return str(value).strip().upper().replace('.','').lstrip('0') or '0'

def reference_maps():
    gem = pd.read_csv(REF/'icd9toicd10cmgem.csv', dtype='string')
    gem['join_key'] = gem.icd9cm.map(key9)
    nine = gem.drop_duplicates('join_key').set_index('join_key').icd10cm.to_dict()
    desc = pd.read_excel(REF/'section111validicd10-jan2025_0.xlsx', dtype=str)
    desc['code'] = desc.CODE.map(code10)
    names = desc.dropna(subset=['code']).drop_duplicates('code').set_index('code')['SHORT DESCRIPTION (VALID ICD-10 FY2025)'].to_dict()
    return nine, names

def chapter(code):
    if code.startswith('D'):
        return 'Neoplasms' if code[1] in '01234' else 'Blood disorders' if code[1] in '5678' else None
    if code.startswith('H'): return 'Eye disorders' if int(code[1])<6 else 'Ear disorders'
    return CHAPTERS.get(code[0])

def prepare_diagnoses(sheets):
    nine, names = reference_maps(); prepared=[]; audit={}
    for source in ['Diagnoses','Problems']:
        df = sheets[source].copy(); typ=df.DX_CODE_TYPE.astype('string').str.strip().str.upper()
        mapped = df.DX_CODE.map(key9).map(nine)
        codes=df.DX_CODE.where(typ.eq('ICD10'), mapped.where(typ.eq('ICD9'))).map(code10)
        text=df.DX_NAME_ORIG if source=='Diagnoses' else df.DX_NAME
        text=text.astype('string').str.strip().replace({'':'__MISSING__','NULL':'__MISSING__'})
        if source=='Diagnoses':text=text.mask(text.isna()|text.eq('__MISSING__'),df.DX_NAME.astype('string').str.strip())
        erroneous=text.fillna('').str.upper().eq('ERRONEOUS ENCOUNTER--DISREGARD')
        df['code']=codes;df['source_label']=text;df['subject']=df.SUBJECT_ID;df['source']=source
        audit[source]={'source_rows':len(df),'source_children':df.subject.nunique(),
          'icd9_rows':int(typ.eq('ICD9').sum()),'unmapped_icd9_rows':int((typ.eq('ICD9')&mapped.isna()).sum()),
          'invalid_or_unsupported_code_rows':int(codes.isna().sum()),'erroneous_label_rows':int(erroneous.sum())}
        df=df[codes.notna()&~erroneous].copy();prepared.append(df[['subject','code','source_label','source','source_row']])
    rows=pd.concat(prepared,ignore_index=True)
    # Choose one clinically meaningful label per code, independent of worksheet order.
    candidates=rows.dropna(subset=['source_label']).copy()
    candidates=candidates[~candidates.source_label.isin(['__MISSING__','NA','(NONE)'])]
    votes=candidates.drop_duplicates(['subject','code','source_label']).groupby(['code','source_label']).size().rename('children').reset_index()
    fallback=votes.sort_values(['code','children','source_label'],ascending=[True,False,True],kind='stable').drop_duplicates('code').set_index('code').source_label.to_dict()
    labels={c:names.get(c,fallback.get(c)) for c in rows.code.unique()}
    rows['label']=rows.code.map(labels)
    excluded=rows.label.isna()
    audit['rows_excluded_no_usable_label']=int(excluded.sum())
    rows=rows[~excluded].copy()
    # One child/code across both sources. No dates/encounters or NP diagnoses are invented.
    dx=rows[['subject','code','label']].drop_duplicates(['subject','code']).copy()
    dx['chapter']=dx.code.map(chapter)
    dx['f_group']=dx.code.map(lambda c:F_GROUPS[int(c[1])] if c.startswith('F') else None)
    codes=pd.DataFrame({'code':sorted(labels)})
    codes['label']=codes.code.map(labels);codes['label_source']=codes.code.map(lambda c:'FY2025 short description' if c in names else 'Released source label; unique-child frequency, lexical ties')
    audit.update(unique_child_code_pairs=len(dx),children_with_prepared_diagnoses=dx.subject.nunique(),
      children_with_source_diagnosis_information=len(set(sheets['Diagnoses'].SUBJECT_ID)|set(sheets['Problems'].SUBJECT_ID)),
      F_code_children=dx[dx.code.str.startswith('F')].subject.nunique(),
      unmapped_reference_behavior='First normalized GEM mapping; exclude unmapped ICD9.',
      PANDA_diagnosis_contribution='No equivalent new-diagnosis fields found; assessment scores not converted to diagnoses.')
    return dx, audit, codes, rows

def diagnosis_counts(dx, n):
    def count(col):return dx.drop_duplicates(['subject',col]).groupby(col).size().sort_values(ascending=False,kind='stable')
    mental=dx[dx.code.str.startswith('F')]
    top=mental.drop_duplicates(['subject','label']).groupby('label').size().rename('Children').reset_index()
    top=top.sort_values(['Children','label'],ascending=[False,True],kind='stable').head(30).rename(columns={'label':'Diagnosis'})
    top['Prevalence']=top.Children/n
    return count('chapter'), count('f_group'), top.reset_index(drop=True)

def head_measurements(vitals, butterfly):
    """One median eligible HC per child. No use of unverified AGE_AT_COLLECTION units."""
    df=vitals.copy();stages=[]
    def log(stage):stages.append({'stage':stage,'rows':len(df),'children':df.SUBJECT_ID.nunique()})
    log('Released Vitals')
    for c,lo,hi in [('BLOOD_PRESSURE_DIASTOLIC',30,130),('BLOOD_PRESSURE_SYSTOLIC',50,200),('HEIGHT',11,80),('WEIGHT',4,440),('HEAD_CIRCUMFERENCE',30,60),('BMI',10,40)]:
        df[c]=pd.to_numeric(df[c],errors='coerce');df=df[df[c].between(lo,hi)].copy();log(c+' eligibility')
    birth_year=pd.to_numeric(butterfly.set_index('Subject_ID').Year_of_birth,errors='coerce')
    df=df[df.SUBJECT_ID.map(birth_year).ge(1993)].copy();log('Birth year >=1993')
    log('No measurement-age filter: age units unverified')
    selected=df.groupby('SUBJECT_ID',sort=True).agg(hc=('HEAD_CIRCUMFERENCE','median'),
        Measurements=('HEAD_CIRCUMFERENCE','size'),Minimum=('HEAD_CIRCUMFERENCE','min'),Maximum=('HEAD_CIRCUMFERENCE','max')).reset_index().rename(columns={'SUBJECT_ID':'key'})
    return selected,pd.DataFrame(stages),df
