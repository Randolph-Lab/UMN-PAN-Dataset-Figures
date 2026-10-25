"""Generate Figure 4: adverse childhood experiences, from BLOOM_BUTTERFLY.csv."""
from pathlib import Path
from bloom_data import load_butterfly
from panel_exports import export_panels
import runpy
import textwrap
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter, MaxNLocator
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
OUT = HERE / 'Figures/Adverse Childhood Experiences'
NAME = 'PAN Paper Figure 4 - Adverse Childhood Experiences'
COLUMNS = [
    'Emotional_abuse', 'Physical_abuse', 'Sexual_abuse', 'Abuse_unspecified',
    'Physical_neglect', 'Neglect_unspecified', 'Caregiver_treated_violently',
    'Family_violence', 'Substance_abuse_in_the_household', 'Mental_illness_in_the_household',
    'Incarcerated_household_member', 'Parental_divorce_separation',
    'Caregiver_Disability_Death', 'Housing_instability', 'Community_violence',
    'Personal_history_of_being_arrested_detained_incarcerated',
    'Personal_history_of_suicidal_ideation_or_attempt',
    'Personal_history_of_self_injurious_behavior',
]


def main():
    shared = runpy.run_path(str(HERE / 'Placement Figure.py'))
    df = shared['load_manual']()
    if df.Subject_ID.duplicated().any():
        raise ValueError('Expected one row per subject.')
    n = len(df)
    values = df[COLUMNS].astype('string').apply(lambda s: s.str.strip().str.casefold())
    invalid = values.apply(lambda s: s.notna() & s.ne('') & ~s.str.match(r'^(yes|suspected|no)\b', na=False))
    if invalid.any().any():
        raise ValueError('Unrecognized ACE response; review the released dataset.')
    # Family/community violence include qualified Yes and Suspected responses.
    values = values.apply(lambda s: s.str.extract(r'^(yes|suspected|no)\b', expand=False)
                          .where(s.notna() & s.ne(''), pd.NA))
    unexpected = set(values.stack().dropna()) - {'yes', 'suspected', 'no', ''}
    if unexpected:
        raise ValueError(f'Unexpected ACE responses: {unexpected}')
    counts = pd.DataFrame({r: values.eq(r.lower()).sum() for r in ['Yes', 'Suspected', 'No']})
    counts['Missing'] = n - counts.sum(axis=1)
    counts['Positive'] = counts.Yes + counts.Suspected
    counts = counts.sort_values('Positive', ascending=False, kind='stable')
    degree = values.isin(['yes', 'suspected']).sum(axis=1)
    distribution = degree.value_counts().reindex(range(int(degree.max()) + 1), fill_value=0).sort_index()
    assert distribution.sum() == n
    assert int((distribution.index * distribution).sum()) == int(counts.Positive.sum())
    assert counts[['Yes', 'Suspected', 'No', 'Missing']].sum(axis=1).eq(n).all()

    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 6,
                         'axes.titlesize': 8, 'axes.titleweight': 'bold',
                         'axes.labelsize': 7, 'xtick.labelsize': 6,
                         'ytick.labelsize': 6, 'svg.fonttype': 'none'})
    fig = plt.figure(figsize=(7.48, 9))
    # Center the full top block, including the shared category labels.
    a = fig.add_axes([.31, .43, .30, .48])
    b = fig.add_axes([.66, .43, .28, .48], sharey=a)
    c = fig.add_axes([.10, .075, .84, .235])
    labels = [textwrap.fill(k.replace('_', ' '), 34) for k in counts.index]
    y = np.arange(len(counts))
    # Use the same first three ordered shades as Figures 1–3.
    dark, medium, light = shared['COLORS'][:3]
    for ax in (a, b, c):
        shared['style'](ax)
    a.barh(y, counts.Positive, color=dark, edgecolor='#555555', lw=.5)
    a.set_yticks(y, labels, fontsize=6)
    a.invert_yaxis()
    a.set_xlim(0, counts.Positive.max() * 1.85)
    a.xaxis.set_major_locator(MaxNLocator(integer=True, nbins=3))
    a.set_xlabel('Number of Children')
    a.set_ylabel('Adverse Childhood Experience')
    a.set_title('ACE Prevalence (Yes or Suspected)', pad=29)
    for i, v in enumerate(counts.Positive):
        a.text(v + counts.Positive.max() * .015, i, f'{v:,} ({v / n:.1%})', va='center', fontsize=6)
    left = np.zeros(len(counts))
    for response, color in [('Yes', dark), ('Suspected', light), ('No', '#E6F7F8'), ('Missing', '#dddddd')]:
        if not counts[response].any():
            continue
        widths = counts[response].to_numpy() / n * 100
        b.barh(y, widths, left=left, color=color, edgecolor='#555555', lw=.35, label=response)
        left += widths
    b.tick_params(axis='y', labelleft=False, left=False)
    b.set_xlim(0, 100)
    b.set_xticks([0, 25, 50, 75, 100])
    b.xaxis.set_major_formatter(PercentFormatter())
    # Draw reference lines over the stacked bars without adding tick labels.
    b.grid(False, axis='x')
    for percentage in (25, 50, 75):
        b.axvline(percentage, color='#999999', linestyle='-', linewidth=.5, zorder=3)
    for percentage in range(10, 100, 10):
        if percentage == 50:
            continue
        b.axvline(percentage, color='#999999', linestyle=':', linewidth=.5, zorder=3)
    b.set_xlabel('Percentage of Children (%)')
    b.set_title('ACE Classification by Type', pad=29)
    b.legend(loc='lower center', bbox_to_anchor=(.5, 1.01), ncol=4, frameon=False,
             fontsize=6.5, handlelength=1, columnspacing=.7, handletextpad=.4)
    c.bar(distribution.index, distribution.values, width=.86, color=dark, edgecolor='#555555', lw=.6)
    c.set_xticks(distribution.index)
    c.set_ylim(0, distribution.max() * 1.21)
    c.set_xlim(-.6, distribution.index.max() + .6)
    c.yaxis.set_major_locator(MaxNLocator(integer=True, nbins=5))
    c.set_xlabel('Number of ACEs (Yes or Suspected)')
    c.set_ylabel('Number of Children')
    c.set_title('Number of ACEs per Child', pad=12)
    for x, v in distribution.items():
        c.text(x, v + 5, f'{v:,}\n({v / n:.1%})', ha='center', va='bottom', fontsize=6)
    for x, y0, letter in [(.265, .965, 'a'), (.63, .965, 'b'), (.025, .345, 'c')]:
        fig.text(x, y0, letter, fontsize=14, fontweight='bold', va='top')
    OUT.mkdir(parents=True, exist_ok=True)
    for ext in ('png', 'svg'):
        fig.savefig(OUT / f'{NAME}.{ext}', dpi=300, transparent=True)
    fig.savefig(OUT / f'{NAME} - White Background.png', dpi=300, facecolor='white')
    # The standalone composition panel needs the category axis shared in the composite.
    b.tick_params(axis='y', labelleft=True, left=True, labelsize=6)
    b.set_ylabel(a.get_ylabel())
    export_panels(fig, OUT, NAME, {
        'a - ACE Prevalence': ([a], [fig.texts[0]]),
        'b - ACE Response Composition': ([b], [fig.texts[1]]),
        'c - Number of ACEs per Participant': ([c], [fig.texts[2]]),
    })
    plt.close(fig)
    exported = counts.rename_axis('ACE').reset_index()
    exported['Denominator'] = n
    exported['Positive_percent'] = exported.Positive / n * 100
    exported.to_csv(OUT / 'ace_counts.csv', index=False)
    pd.DataFrame({'ACE_count': distribution.index, 'Count': distribution.values,
                  'Denominator': n, 'Percent': distribution.values / n * 100}).to_csv(
                      OUT / 'ace_distribution.csv', index=False)
    print(f'Saved Figure 4 and aggregate data to {OUT}; n = {n}.')


if __name__ == '__main__':
    main()
