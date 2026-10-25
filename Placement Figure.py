"""Generate Figure 2: adoption, foster placement, and transitions.

Run from any directory. Only aggregate counts are exported.
"""
from pathlib import Path
from bloom_data import load_butterfly
from panel_exports import export_panels

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import colors as mcolors
from matplotlib.patches import Patch
from matplotlib.transforms import Bbox
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
OUT = HERE / 'Figures/Placement'
PLACEMENTS = {
    'Group Home': 'Group_home', 'Respite': 'Respite_care',
    'Orphanage': 'Orphanage_care', 'Foster to Adopt': 'Foster_to_adopt_adoption',
    'Kinship': 'Kinship_care', 'Traditional': 'Traditional',
    'Institutional Care': 'Institutional_care',
}
ADOPTIONS = {'Domestic Adoption': 'Domestic_adoption', 'International Adoption': 'International_adoption'}
# Match Figure 1's gradient and first six category shades exactly.
CMAP = mcolors.LinearSegmentedColormap.from_list(
    'teal', ['#E6F7F8', '#7FDFE2', '#00BFC4', '#007B80', '#00383B'])
# Use Figure 1's map background gray for the seventh category (Group Home).
PALETTES = {
    'map_teal': [mcolors.to_hex(CMAP(position)) for position in np.linspace(1, 0, 6)]
                + ['#E6E6E6'],
    'blue': ['#08519C', '#6BAED6', '#C6DBEF', '#2171B5', '#9ECAE1', '#4292C6', '#08306B'],
    'original': ['#F8766D', '#00BFC4', '#00BA38', '#F564E3', '#B79F00', '#619CFF', '#C77CFF'],
}
PALETTE = 'map_teal'
COLORS = PALETTES[PALETTE]


def load_manual():
    return load_butterfly()


def yes(series):
    return series.astype('string').str.strip().str.casefold().eq('yes').fillna(False)


def summary(df):
    adoption = pd.Series({k: int(df.loc[yes(df[v]), 'Subject_ID'].nunique())
                          for k, v in ADOPTIONS.items()})
    placement = pd.Series({k: int(yes(df[v]).sum()) for k, v in PLACEMENTS.items()})
    cross = pd.DataFrame({a: {p: int((yes(df[c]) & yes(df[ac])).sum())
                             for p, c in PLACEMENTS.items()} for a, ac in ADOPTIONS.items()})
    transitions = pd.to_numeric(df['Number_of_transitions'], errors='coerce')
    invalid = df['Number_of_transitions'].notna() & transitions.isna()
    if invalid.any() or ((transitions.dropna() < 0) | (transitions.dropna() % 1 != 0)).any():
        raise ValueError('Transition counts must be nonnegative integers or blank.')
    counts = transitions.value_counts().reindex(range(int(transitions.max()) + 1), fill_value=0).astype(int)
    missing = int(transitions.isna().sum())
    assert int(counts.sum()) + missing == len(df)
    return adoption, placement, cross, counts, missing


def donut(ax, counts, colors):
    # Assign palette colors by descending count, as in Figure 1.
    counts = counts.sort_values(ascending=False, kind='stable')
    ax.pie(counts.values[::-1], colors=colors[::-1], startangle=90, counterclock=False,
           wedgeprops={'width': .5, 'edgecolor': 'white', 'linewidth': .6})
    color_by_category = dict(zip(counts.index, colors))
    ordered = counts.sort_values(ascending=False, kind='stable')
    labels = [f'{k} (n = {v:,}, {v / counts.sum():.1%})' for k, v in ordered.items()]
    legend = ax.legend([Patch(facecolor=color_by_category[k], edgecolor='white')
                        for k in ordered.index], labels,
                      loc='center left', bbox_to_anchor=(1, .5),
                      frameon=False, fontsize=6.5, labelspacing=.6)


def style(ax):
    ax.set_axisbelow(True)
    ax.grid(color='#ededed', linewidth=.6)
    for spine in ['top', 'right']:
        ax.spines[spine].set_visible(False)
    for spine in ['bottom', 'left']:
        ax.spines[spine].set_color('#aaaaaa')
    ax.tick_params(length=0, labelsize=6)


def make_figure(adoption, placement, cross, transitions, vertical_transitions=True, cohort_size=2720):
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'svg.fonttype': 'none', 'pdf.fonttype': 42})
    fig = plt.figure(figsize=(7.48, 9))
    grid = fig.add_gridspec(3, 2, height_ratios=[1, 1.1, 2.1],
                           left=.08, right=.97, bottom=.05, top=.96, wspace=.14, hspace=.32)
    # Reserve header space and room for the placement bar labels.
    top_a = grid[0, 0].subgridspec(2, 2, height_ratios=[.18, .82], width_ratios=[1, 1.15], hspace=0)
    top_b = grid[0, 1].subgridspec(2, 2, height_ratios=[.18, .82], width_ratios=[.8, 1.5], hspace=0)
    a = fig.add_subplot(top_a[1, :]); b = fig.add_subplot(top_b[1, 1])
    style(a)
    adoption_positions = np.arange(len(adoption))
    a.bar(adoption_positions, adoption.values, color=COLORS[:2],
          edgecolor='#555555', linewidth=.6, width=.6)
    a.set_xticks(adoption_positions, ['Domestic', 'International'], fontsize=6)
    a.set_ylabel('Number of Children', fontsize=7)
    a.set_xlabel('Adoption Type', fontsize=7, labelpad=2)
    a.set_ylim(0, adoption.max() * 1.25)
    for x, count in enumerate(adoption.values):
        a.text(x, count + 15, f'{count:,} ({count / cohort_size:.1%})',
               ha='center', va='bottom', fontsize=6)
    style(b)
    ordered_placements = placement.sort_values(ascending=False, kind='stable')
    bar_positions = np.arange(len(ordered_placements))
    b.barh(bar_positions, ordered_placements.values, color=COLORS,
           edgecolor='#555555', linewidth=.6, height=.72)
    b.set_yticks(bar_positions, ordered_placements.index, fontsize=6)
    b.invert_yaxis()
    b.set_xlim(0, ordered_placements.max() * 1.5)
    b.set_xticks([0, 1000, 2000])
    b.set_xlabel('Number of Participants', fontsize=7, labelpad=2)
    for y, count in enumerate(ordered_placements.values):
        b.text(count + 35, y, f'{count:,} ({count / cohort_size:.1%})',
               va='center', fontsize=5.5)
    # Match Figure 1: title centered over the full panel, in its header area.
    for spec, title, letter in [(grid[0, 0], 'Adoption Placement', 'a'),
                                 (grid[0, 1], 'Foster Care Placement by Type', 'b')]:
        header = fig.add_subplot(spec, frameon=False)
        header.set_axis_off()
        header.text(.5, .98, title, transform=header.transAxes, fontsize=8,
                    fontweight='bold', va='top', ha='center')
        header.text(.02, .98, letter, transform=header.transAxes, fontsize=14,
                    fontweight='bold', va='top')
    c = fig.add_subplot(grid[1, :]); style(c)
    # Keep panel c in its grid slot, with space below the top-row axis labels.
    order = ['Foster to Adopt', 'Group Home', 'Kinship', 'Orphanage', 'Respite', 'Traditional', 'Institutional Care']
    labels = ['Foster\nto Adopt', 'Group\nHome', 'Kinship\nCare', 'Orphanage\nCare', 'Respite\nCare', 'Traditional', 'Institutional\nCare']
    positions = np.arange(len(order))
    width = .36
    for i, name in enumerate(ADOPTIONS):
        counts = cross[name].reindex(order)
        centers = positions + (i - .5) * width
        c.bar(centers, counts, width=width, color=COLORS[i],
              edgecolor='#555555', linewidth=.6, label=name.removesuffix(' Adoption'))
        for category, x, v in zip(order, centers, counts):
            # Give the domestic institutional-care percentage room beside
            # the taller international bar without moving either bar.
            label_offset = (-1.5, 0) if category == 'Institutional Care' and i == 0 else (0, 0)
            c.annotate(f'{v}\n({v / adoption[name]:.1%})', xy=(x, v + 8),
                       xytext=label_offset, textcoords='offset points',
                       ha='center', fontsize=6)
    c.set_xticks(positions, labels, fontsize=6)
    c.set_ylim(0, cross.to_numpy().max() * 1.25)
    c.set_ylabel('Number of Children', fontsize=7)
    c.set_xlabel('Placement Type', fontsize=7)
    c.set_title('Placement Types by Adoption Status', fontsize=8, fontweight='bold', pad=12)
    c.legend(loc='upper center', ncol=2, frameon=False, fontsize=6.5)
    d = fig.add_subplot(grid[2, :]); style(d)
    transition_positions = np.arange(len(transitions))
    if vertical_transitions:
        d.bar(transition_positions, transitions, color=COLORS[1],
              edgecolor='#555555', linewidth=.6, width=.7)
        d.set_xticks(transition_positions, [str(v) for v in transitions.index])
        d.set_ylim(0, transitions.max() * 1.3)
        d.set_xlabel('Number of Placement Transitions', fontsize=8)
        d.set_ylabel('Number of Participants', fontsize=8)
        for x, v in enumerate(transitions.values):
            if v:
                if v >= 150 or transitions.index[x] == 0:
                    d.text(x, v + 15, f'{v}\n({v / cohort_size:.1%})',
                           ha='center', va='bottom', fontsize=6)
                else:
                    d.text(x, v + 12, f'{v} ({v / cohort_size:.1%})',
                           ha='left', va='bottom', rotation=45, rotation_mode='anchor', fontsize=5)
        d.set_title('Placement Transitions', fontsize=8, fontweight='bold', pad=12)
    else:
        d.barh(transition_positions, transitions, color=COLORS[1], edgecolor='#555555', linewidth=.6, height=.9)
        d.set_yticks(transition_positions, [str(v) for v in transitions.index])
        d.set_xlim(0, transitions.max() * 1.2)
        d.set_xlabel('Count', fontsize=8)
        d.set_ylabel('Transitions', fontsize=8)
        d.set_title('Placement Transitions', fontsize=8, fontweight='bold', pad=12)
        for y, v in enumerate(transitions.values):
            if v:
                d.text(v + 8, y, f'{v} ({v / cohort_size:.1%})', va='center', fontsize=6)
    for spec, letter in [(grid[1, :], 'c'), (grid[2, :], 'd')]:
        box = spec.get_position(fig)
        fig.text(box.x0 - .035, box.y1 + .015, letter, fontsize=14,
                 color='black', fontweight='bold', va='bottom')
    return fig


def main():
    df = load_manual()
    adoption, placement, cross, transitions, missing = summary(df)
    OUT.mkdir(parents=True, exist_ok=True)
    fig = make_figure(adoption, placement, cross, transitions, cohort_size=df['Subject_ID'].nunique())
    # Trim only the unused top margin, preserving panel sizes and other margins.
    export_bounds = Bbox.from_bounds(0, 0, fig.get_figwidth(), fig.get_figheight() - .25)
    for ext in ('png', 'svg'):
        fig.savefig(OUT / f'PAN Paper Figure 2 - Placement Figure.{ext}', dpi=300,
                    transparent=True, bbox_inches=export_bounds)
    fig.savefig(OUT / 'PAN Paper Figure 2 - Placement Figure - White Background.png',
                dpi=300, transparent=False, facecolor='white', bbox_inches=export_bounds)
    export_panels(fig, OUT, 'PAN Paper Figure 2 - Placement Figure', {
        'a - Adoption Placement': ([fig.axes[0], fig.axes[2]], []),
        'b - Foster Care Placement by Type': ([fig.axes[1], fig.axes[3]], []),
        'c - Placement Types by Adoption Status': ([fig.axes[4]], [fig.texts[0]]),
        'd - Placement Transitions': ([fig.axes[5]], [fig.texts[1]]),
    })
    plt.close(fig)
    rows = []
    for panel, group, counts in [('a', 'Adoption', adoption), ('b', 'Placement', placement),
                                  *[('c', name, cross[name]) for name in cross],
                                  ('d', 'Known transitions', transitions)]:
        denominator = (df['Subject_ID'].nunique() if panel in ('a', 'b', 'd') else
                       int(adoption[group]) if panel == 'c' else int(counts.sum()))
        for category, count in counts.items():
            rows.append({'panel': panel, 'group': group, 'category': category, 'count': int(count),
                         'denominator': denominator, 'percent': 100 * count / denominator})
    pd.DataFrame(rows).to_csv(OUT / 'placement_counts.csv', index=False)
    print(f'Saved figure and aggregate counts to {OUT}; {len(df)} subjects, {missing} missing transition counts.')


if __name__ == '__main__':
    main()
