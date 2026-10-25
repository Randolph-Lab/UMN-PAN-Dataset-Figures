"""Recreate aggregate exports for Figures 2 and 3 without touching graphics."""
import runpy
import pandas as pd
from bloom_data import HERE, load_butterfly

def main():
    df=load_butterfly();n=len(df);shared=runpy.run_path(str(HERE/'Placement Figure.py'))
    adoption,placement,cross,transitions,missing=shared['summary'](df)
    rows=[]
    for panel,group,counts in [('a','Adoption',adoption),('b','Placement',placement),*[('c',name,cross[name]) for name in cross],('d','Known transitions',transitions)]:
        den=int(adoption[group]) if panel=='c' else n
        for category,count in counts.items():rows.append({'panel':panel,'group':group,'category':category,'count':int(count),'denominator':den,'percent':100*count/den})
    folder=HERE/'Figures/Placement';folder.mkdir(parents=True,exist_ok=True);pd.DataFrame(rows).to_csv(folder/'placement_counts.csv',index=False)
    code=runpy.run_path(str(HERE/'Prenatal Substance Exposure Figure.py'));columns=code['COLUMNS'];values=df[list(columns.values())].astype('string').apply(lambda s:s.str.strip().str.casefold());x=values.isin(['yes','suspected']);x.columns=list(columns);degree=x.sum(axis=1);exposed=int(degree.gt(0).sum());mono=x[degree.eq(1)].sum().astype(int);total=x.sum().astype(int)
    pd.DataFrame({'substance':mono.index,'single_count':mono.values,'any_exposure_count':total[mono.index].values,'multiple_substance_count':(total-mono)[mono.index].values,
      'panel_a_denominator':int(mono.sum()),'panel_a_single_percent':100*mono.values/mono.sum(),'panel_b_denominator':exposed,
      'panel_b_single_percent':100*mono.values/exposed,'panel_b_any_exposure_percent':100*total[mono.index].values/exposed}).to_csv(HERE/'Figures/Prenatal Substance Exposure/exposure_counts.csv',index=False)
    combos=sorted([(tuple(k),int(v)) for k,v in x[degree.gt(0)].value_counts().items()],key=lambda kv:(sum(kv[0]),kv[1],kv[0]))
    pd.DataFrame([{'combination':' + '.join(name for name,flag in zip(columns,key) if flag),'degree':sum(key),'count':count,
      'displayed_in_panel_c':sum(key)>=code['MIN_COMBINATION_DEGREE'] and count>=code['MIN_COMBINATION_COUNT']} for key,count in combos]).to_csv(HERE/'Figures/Prenatal Substance Exposure/exposure_combinations.csv',index=False)
    return n
if __name__=='__main__':main()
