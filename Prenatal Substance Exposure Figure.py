"""Generate Figure 3 from BLOOM_BUTTERFLY.csv; export aggregate data only."""
from pathlib import Path
from bloom_data import load_butterfly
from panel_exports import export_panels
import runpy
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.ticker import MaxNLocator
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
OUT = HERE / 'Figures/Prenatal Substance Exposure'
NAME = 'PAN Paper Figure 3 - Prenatal Substance Exposure'
MIN_COMBINATION_COUNT = 5
MIN_COMBINATION_DEGREE = 2
COLUMNS = dict(zip(['Alcohol', 'Tobacco', 'Cannabis', 'Methamphetamine', 'Other',
                    'Opioids', 'Cocaine', 'Unspecified Drugs'],
                   ['Alcohol', 'Tobacco', 'Marijuana', 'Methamphetamine', 'Other',
                    'Opioids', 'Cocaine', 'Unspecified_drugs']))


def export_horizontal_combinations(displayed_combos, order, total, shades, exposed_n, color):
    """Alternate standalone UpSet with one column per exact combination."""
    n = len(displayed_combos)
    fig = plt.figure(figsize=(max(11.7, n * .15 + 2.3), 4.8))
    grid = fig.add_gridspec(2, 2, width_ratios=[2, 10], height_ratios=[2.5, 1.6],
                            left=.07, right=.99, bottom=.13, top=.90,
                            wspace=.04, hspace=.05)
    hist = fig.add_subplot(grid[0, 1])
    matrix = fig.add_subplot(grid[1, 1], sharex=hist)
    sets = fig.add_subplot(grid[1, 0], sharey=matrix)
    hist.bar(range(n), [count for _, count in displayed_combos], width=.72,
             color=color, edgecolor='#555555', linewidth=.5)
    hist.set_ylabel('Number of Children')
    hist.yaxis.set_major_locator(MaxNLocator(integer=True, nbins=5))
    hist.tick_params(axis='x', bottom=False, labelbottom=False)
    hist.set_axisbelow(True)
    hist.grid(axis='y', color='#e6e6e6', lw=.6)
    indices = [list(COLUMNS).index(name) for name in order]
    for row in range(8):
        matrix.axhspan(row-.5, row+.5,
                       color='#eeeeee' if row % 2 == 0 else '#f7f7f7', zorder=0)
    for col, (key, _) in enumerate(displayed_combos):
        active = [row for row, ix in enumerate(indices) if key[ix]]
        matrix.scatter([col]*8, range(8), s=5, color='#d0d0d0', zorder=2)
        matrix.plot([col, col], [min(active), max(active)], color='#333333', lw=.6, zorder=3)
        matrix.scatter([col]*len(active), active, s=10, color='#222222', zorder=4)
    matrix.set_xlim(-.6, n-.4)
    matrix.set_ylim(7.6, -.6)
    matrix.set_xticks([])
    matrix.tick_params(axis='y', left=False, labelleft=False)
    matrix.set_xlabel('Exposure Combinations')
    sets.barh(range(8), total[order], color=[shades[name] for name in order],
              height=.7, edgecolor='#555555', linewidth=.5)
    sets.set_yticks(range(8), order, fontsize=6)
    sets.tick_params(axis='y', length=0)
    sets.set_xlim(total.max()*1.85, 0)
    sets.set_xlabel('Number of Children')
    sets.xaxis.set_major_locator(MaxNLocator(integer=True, nbins=3))
    sets.set_axisbelow(True)
    sets.grid(axis='x', color='#e6e6e6', lw=.6)
    for row, count in enumerate(total[order]):
        sets.annotate(f'{count:,} ({count / exposed_n:.1%})', (count, row),
                      xytext=(-3, 0), textcoords='offset points',
                      ha='right', va='center', fontsize=5.5)
    for ax in (hist, matrix, sets):
        ax.spines[['top', 'right', 'left', 'bottom']].set_visible(False)
    title = fig.text(.5, .97, 'Prenatal Exposure Combinations', ha='center',
                     va='top', fontsize=8, weight='bold')
    export_panels(fig, OUT, NAME, {
        'c - Prenatal Exposure Combinations - Horizontal': ([sets, matrix, hist], [title]),
    })
    plt.close(fig)


def main():
    placement = runpy.run_path(str(HERE / 'Placement Figure.py'))
    df = placement['load_manual']()
    if df.Subject_ID.duplicated().any():
        raise ValueError('Expected one row per subject.')
    values = df[list(COLUMNS.values())].astype('string').apply(lambda s: s.str.strip().str.casefold())
    x = values.isin(['yes', 'suspected'])
    x.columns = list(COLUMNS)
    degree = x.sum(axis=1)
    exposed_n = int((degree > 0).sum())
    mono = x.loc[degree == 1].sum().astype(int)
    total = x.sum().astype(int)
    combinations = x.loc[degree > 0].value_counts()
    combos = sorted([(tuple(k), int(v)) for k, v in combinations.items()],
                    key=lambda kv: (sum(kv[0]), kv[1], kv[0]))
    assert sum(v for _, v in combos) == int((degree > 0).sum())
    assert int(mono.sum()) == int((degree == 1).sum())
    assert sum(sum(k) * v for k, v in combos) == int(total.sum())
    order = total.sort_values(ascending=False, kind='stable').index.tolist()
    # Preserve all six Figure 1/2 teal shades; interpolate two for eight substances.
    palette = [placement['CMAP'](position)
               for position in sorted([*np.linspace(1, 0, 6), .9, .1], reverse=True)]
    shades = dict(zip(mono.sort_values(ascending=False, kind='stable').index, palette))
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 6, 'axes.titlesize': 8,
                         'axes.titleweight': 'bold', 'xtick.labelsize': 6, 'ytick.labelsize': 6,
                         'axes.labelsize': 7, 'svg.fonttype': 'none'})
    fig = plt.figure(figsize=(7.48, 9), facecolor='white')
    outer = fig.add_gridspec(2, 1, left=.085, right=.405, bottom=.12, top=.92,
                            hspace=.48)
    a, b = fig.add_subplot(outer[0, 0]), fig.add_subplot(outer[1, 0])
    b_box = b.get_position()
    b.set_position([.105, b_box.y0, .34, b_box.height])
    for ax in (a, b):
        ax.set_axisbelow(True)
        ax.grid(axis='y', color='#e6e6e6', lw=.6)
        ax.spines[['top', 'right']].set_visible(False)
        ax.set_ylabel('Count')
        ax.tick_params(axis='x', length=0, labelsize=6)
        ax.yaxis.set_major_locator(MaxNLocator(integer=True, nbins=5))
    def labels(ax, bars, counts, denominator):
        for bar, count in zip(bars, counts):
            text = f'{count:,} ({count / denominator:.1%})'
            ax.annotate(text,
                        (bar.get_x() + bar.get_width()/2, bar.get_height()),
                        xytext=(0, 3), textcoords='offset points', ha='left', va='bottom',
                        fontsize=5.5, rotation=45 if ax is a else 90, rotation_mode='anchor')
    short = lambda names: [n.replace('Methamphetamine', 'Meth').replace('Unspecified Drugs', 'Unspecified') for n in names]
    names = mono.sort_values(ascending=False, kind='stable').index
    bars = a.bar(range(8), mono[names], color=[shades[n] for n in names], edgecolor='#555555', linewidth=.5)
    labels(a, bars, mono[names], mono.sum())
    a.set_xticks(range(8), short(names))
    a.set_ylim(0, mono.max()*1.34)
    a.set_title('Single-Substance Exposure', pad=12)
    a.set_xlabel('Substance')
    a.set_ylabel('Number of Children')
    positions = np.arange(8) * 1.15
    exposure_colors = {'Single substance': placement['COLORS'][0],
                       'Any exposure': placement['COLORS'][1]}
    for offset, counts, label in [(-.22, mono[order], 'Single substance'),
                                  (.22, total[order], 'Any exposure')]:
        bars = b.barh(positions+offset, counts, height=.44, color=exposure_colors[label],
                      edgecolor='#444444', linewidth=.5)
        for bar, count in zip(bars, counts):
            b.annotate(f'{count:,} ({count / exposed_n:.1%})',
                       (bar.get_width(), bar.get_y()+bar.get_height()/2),
                       xytext=(3, 0), textcoords='offset points',
                       ha='left', va='center', fontsize=5.5)
    b.set_yticks(positions, short(order))
    b.invert_yaxis()
    b.set_xlim(0, total.max()*1.65)
    b.set_axisbelow(True)
    b.grid(False)
    b.grid(axis='x', color='#e6e6e6', lw=.6)
    b.xaxis.set_major_locator(MaxNLocator(integer=True, nbins=4))
    b.yaxis.set_major_locator(matplotlib.ticker.FixedLocator(positions))
    b.tick_params(axis='y', length=0, labelsize=6)
    plt.setp(a.get_xticklabels(), rotation=45, ha='right', rotation_mode='anchor')
    b.set_title('Prenatal Exposure by Substance', pad=12)
    b.set_xlabel('Number of Children')
    b.set_ylabel('Substance')
    b.legend(handles=[Patch(facecolor=exposure_colors['Single substance'], label='Single substance'),
                      Patch(facecolor=exposure_colors['Any exposure'], edgecolor='#444444', label='Any exposure')],
             frameon=False, fontsize=6.5, loc='lower right')
    # Transpose the UpSet: eight substance columns, one row per combination.
    lower = fig.add_gridspec(2, 2, left=.515, right=.985, bottom=.065, top=.96,
                             width_ratios=[1.2, 1], height_ratios=[1.1, 7.9],
                             hspace=0, wspace=.09)
    sets = fig.add_subplot(lower[0, 0])
    matrix = fig.add_subplot(lower[1, 0], sharex=sets)
    hist = fig.add_subplot(lower[1, 1], sharey=matrix)
    # Filter only the displayed intersections; all calculations and marginals above
    # continue to use the complete exposed-child cohort.
    displayed_combos = [(key, count) for key, count in combos
                        if sum(key) >= MIN_COMBINATION_DEGREE and count >= MIN_COMBINATION_COUNT]
    omitted_degree = [(key, count) for key, count in combos if sum(key) < MIN_COMBINATION_DEGREE]
    omitted_count = [(key, count) for key, count in combos
                     if sum(key) >= MIN_COMBINATION_DEGREE and count < MIN_COMBINATION_COUNT]
    assert len(displayed_combos) + len(omitted_degree) + len(omitted_count) == len(combos)
    assert sum(v for group in (displayed_combos, omitted_degree, omitted_count)
               for _, v in group) == exposed_n
    n = len(displayed_combos)
    indices = [list(COLUMNS).index(name) for name in order]
    sets.bar(range(8), total[order], color=[shades[name] for name in order], width=.7,
             edgecolor='#555555', linewidth=.5)
    sets.set_facecolor('white')
    sets.set_axisbelow(True)
    sets.grid(axis='y', color='#e6e6e6', lw=.6)
    sets.set_ylabel('Number of Children', fontsize=6)
    sets.set_yticks([0, 1000, 2000])
    sets.tick_params(axis='x', bottom=False, labelbottom=False)
    sets.tick_params(axis='y', labelsize=5)
    sets.set_ylim(0, total.max()*2.4)
    for i, count in enumerate(total[order]):
        sets.text(i, count+15, f'{count:,} ({count / exposed_n:.1%})',
                  ha='left', va='bottom', fontsize=5, rotation=45, rotation_mode='anchor')
    for col in range(8):
        matrix.axvspan(col-.5, col+.5, color='#eeeeee' if col%2==0 else '#f7f7f7', zorder=0)
    for j, (key, count) in enumerate(displayed_combos):
        active = [i for i, ix in enumerate(indices) if key[ix]]
        matrix.scatter(range(8), [j]*8, s=1.5, color='#d0d0d0', zorder=2)
        matrix.plot([min(active), max(active)], [j,j], color='#333333', lw=.4, zorder=3)
        matrix.scatter(active, [j]*len(active), s=3, color='#222222', zorder=4)
    matrix.set_xlim(-.6, 7.6)
    matrix.set_ylim(n-.3, -.7)
    matrix.set_xticks(range(8), [s.replace('Methamphetamine', 'Meth').replace('Unspecified Drugs', 'Unspecified') for s in order],
                      fontsize=6, rotation=45, ha='right', rotation_mode='anchor')
    matrix.set_yticks([])
    matrix.tick_params(axis='both', length=0)
    matrix.set_ylabel('Exposure Combinations', labelpad=5)
    matrix.set_xlabel('Substances', labelpad=-1)
    hist.barh(range(n), [v for _, v in displayed_combos], color=placement['COLORS'][1], height=.72,
              edgecolor='#555555', linewidth=.5)
    hist.set_xlabel('Number of Children', fontsize=7)
    hist.tick_params(axis='x', labelsize=7, width=.8, length=4, colors='black')
    for tick in hist.get_xticklabels():
        tick.set_fontweight('bold')
    hist.set_xlim(0, max(v for _, v in displayed_combos)*1.12)
    hist.xaxis.set_major_locator(MaxNLocator(integer=True, nbins=3))
    hist.tick_params(axis='y', left=False, labelleft=False)
    hist.set_axisbelow(True)
    hist.grid(axis='x', color='#e6e6e6', lw=.6)
    hist.set_facecolor('white')
    for ax in (sets, matrix, hist):
        ax.spines[['top', 'right', 'left', 'bottom']].set_visible(False)
    for label, pos in [('a', a.get_position()), ('b', b.get_position())]:
        fig.text(.025, pos.y1+.015, label, fontsize=14, weight='bold', color='black')
    fig.text(sets.get_position().x0-.045, .975, 'c', fontsize=14, weight='bold', color='black')
    fig.text(.75, .975, 'Prenatal Exposure Combinations',
             ha='center', fontsize=8, weight='bold', color='black')
    OUT.mkdir(parents=True, exist_ok=True)
    for ext in ['png', 'svg']:
        fig.savefig(OUT / f'{NAME}.{ext}', dpi=300, transparent=True)
    fig.savefig(OUT / f'{NAME} - White Background.png', dpi=300, facecolor='white')
    export_panels(fig, OUT, NAME, {
        'a - Single-Substance Exposure': ([a], [fig.texts[0]]),
        'b - Prenatal Exposure by Substance': ([b], [fig.texts[1]]),
        'c - Prenatal Exposure Combinations': ([sets, matrix, hist], list(fig.texts[2:])),
    })
    plt.close(fig)
    export_horizontal_combinations(displayed_combos, order, total, shades,
                                   exposed_n, placement['COLORS'][1])
    pd.DataFrame({'substance': mono.index, 'single_count': mono.values, 'any_exposure_count': total[mono.index].values,
                  'multiple_substance_count': (total-mono)[mono.index].values,
                  'panel_a_denominator': int(mono.sum()),
                  'panel_a_single_percent': mono.values / mono.sum()*100,
                  'panel_b_denominator': exposed_n,
                  'panel_b_single_percent': mono.values / exposed_n*100,
                  'panel_b_any_exposure_percent': total[mono.index].values / exposed_n*100}).to_csv(OUT / 'exposure_counts.csv', index=False)
    pd.DataFrame([{'combination': ' + '.join(name for name, flag in zip(COLUMNS, key) if flag),
                   'degree': sum(key), 'count': count,
                   'displayed_in_panel_c': sum(key) >= MIN_COMBINATION_DEGREE and count >= MIN_COMBINATION_COUNT} for key, count in combos]).to_csv(OUT / 'exposure_combinations.csv', index=False)
    print(f'Saved {NAME}: {len(df)} subjects, {mono.sum()} single, {(degree > 0).sum()} exposed, {n} combinations.')

if __name__ == '__main__':
    main()
