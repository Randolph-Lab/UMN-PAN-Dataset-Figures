"""Compact Supplement A, calculated exclusively from released BUTTERFLY data."""
from pathlib import Path
import csv
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from bloom_data import load_butterfly

HERE = Path(__file__).resolve().parent
OUT = HERE / 'Figures' / 'Supplement A'


def calculate():
    df = load_butterfly()
    n = len(df)
    assert n > 0
    rows = []
    def add(group, label, count, denominator):
        rows.append(dict(Characteristic=group, Category=label, Count=int(count),
                         Denominator=int(denominator), Percent=100*int(count)/denominator))
    add('Overall cohort', '', n, n)
    sex = df.Sex.astype('string').str.strip().value_counts()
    race = df.Race.astype('string').str.strip().replace({
        'Unknown / Not Reported': 'Other / Unclassified',
        'Native Hawaiian or Other Pacific Islander': 'Pacific Islander'}).value_counts()
    assert sex.sum() == n
    assert race.sum() == n
    for label in ['Male', 'Female']:
        add('Sex', label, sex[label], n)
    for label in ['White', 'Black or African American', 'Asian',
                  'American Indian/Alaska Native', 'Other / Unclassified', 'Pacific Islander']:
        add('Race', label, race[label], n)
    t = pd.to_numeric(df.Number_of_transitions, errors='coerce')
    assert (t.dropna().ge(0) & t.dropna().eq(t.dropna().astype(int))).all()
    for label, mask in [('0 transitions', t.eq(0)), ('1 transition', t.eq(1)),
                        ('2 transitions', t.eq(2)), ('3 transitions', t.eq(3)),
                        ('4+ transitions', t.ge(4)), ('Unknown / missing', t.isna())]:
        add('Placement transitions', label, mask.sum(), n)
    months = pd.to_numeric(df.Age_at_adoption, errors='coerce')
    adopted = df.Was_this_child_adopted_at_time_of_amc_visit.astype('string').str.strip().str.lower().eq('yes')
    unknown = months.isna() & adopted.fillna(False)
    age_n = int(months.notna().sum() + unknown.sum())
    assert 0 <= age_n <= n
    ages = pd.cut(months/12, [-np.inf, 5, 10, 15, np.inf], right=False,
                  labels=['Under 5', '5–<10', '10–<15', '15–21'])
    for label in ages.cat.categories:
        add('Age at adoption (years)', label, ages.eq(label).sum(), age_n)
    add('Age at adoption (years)', 'Unknown age', unknown.sum(), age_n)
    g = pd.to_numeric(df.Gestational_age_at_birth, errors='coerce')
    # Gestational groups do not overlap; "Preterm (>36 to <37 weeks)" is its own
    # group, not a subtotal. Term intervals cover every recorded value.
    groups = [ ('Early preterm (<34 weeks)', g.lt(34)),
               ('Late preterm (34–36 weeks)', g.ge(34) & g.le(36)),
               ('Preterm (>36 to <37 weeks)', g.gt(36) & g.lt(37)),
               ('Early term (37–<39 weeks)', g.ge(37) & g.lt(39)),
               ('Full term (39–<41 weeks)', g.ge(39) & g.lt(41)),
               ('Late/post-term (≥41 weeks)', g.ge(41)),
               ('Unknown / missing', g.isna()) ]
    membership = pd.concat([mask for _, mask in groups], axis=1).sum(axis=1)
    assert membership.eq(1).all(), 'Every child must belong to exactly one gestational group'
    for label, mask in groups:
        add('Gestational age at birth', label, mask.sum(), n)
    for group in {r['Characteristic'] for r in rows}:
        subset = [r for r in rows if r['Characteristic'] == group]
        assert sum(r['Count'] for r in subset) == subset[0]['Denominator']
    return rows


def main():
    rows = calculate()
    OUT.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 7.5,
                         'svg.fonttype': 'none'})
    width, height = 6.0, 6.42
    fig = plt.figure(figsize=(width, height))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set(xlim=(0, width), ylim=(0, height)); ax.set_axis_off()
    left, right = .18, 5.82
    teal = '#00383B'
    title = ax.text(left, 6.25, 'Supplement A. Demographic and Early-Life Characteristics',
                    fontsize=10, weight='bold', va='top')
    top, row_h = 5.96, .205
    ax.add_patch(Rectangle((left, top-.25), right-left, .25, color=teal, lw=0))
    for x, label, align in [(left+.05, 'Characteristic', 'left'),
                             (2.22, 'Category', 'left'), (right-.05, 'Overall, n (%)', 'right')]:
        ax.text(x, top-.125, label, color='white', weight='bold', va='center', ha=align, fontsize=7.5)
    previous = None
    texts_by_row = []
    for i, row in enumerate(rows):
        y = top-.25-i*row_h
        if i % 2 == 0:
            ax.add_patch(Rectangle((left,y-row_h),right-left,row_h,color='#F0F8F8',lw=0))
        group = row['Characteristic']
        artists = []
        if group != previous:
            ax.plot([left,right],[y,y],color='#AFCBCD',lw=.45)
            artists.append(ax.text(left+.05, y-row_h/2, group, weight='bold', va='center', fontsize=7.2))
        artists.append(ax.text(2.22,y-row_h/2,row['Category'],va='center',fontsize=7.2))
        value = f"{row['Count']:,}" if group == 'Overall cohort' else f"{row['Count']:,} ({row['Percent']:.1f})"
        artists.append(ax.text(right-.05,y-row_h/2,value,ha='right',va='center',fontsize=7.5))
        texts_by_row.append(artists)
        previous = group
    bottom = top-.25-len(rows)*row_h
    ax.plot([left,right],[bottom,bottom],color=teal,lw=.7)
    note_artists = []
    fig.canvas.draw()
    renderer=fig.canvas.get_renderer()
    for artists in texts_by_row:
        boxes=[a.get_window_extent(renderer) for a in artists if a.get_text()]
        for a,b in zip(boxes,boxes[1:]):
            assert a.x1 < b.x0, 'Text overlaps between columns'
    for artist in [title]+[a for row in texts_by_row for a in row]+note_artists:
        box=artist.get_window_extent(renderer)
        assert fig.bbox.contains(box.x0,box.y0) and fig.bbox.contains(box.x1,box.y1), artist.get_text()
    for ext in ['png','svg']:
        fig.savefig(OUT/f'Supplement A.{ext}',dpi=300,transparent=True)
    fig.savefig(OUT/'Supplement A - White Background.png',dpi=300,facecolor='white')
    plt.close(fig)
    with (OUT/'Supplement A.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

if __name__ == '__main__':
    main()
