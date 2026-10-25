"""Six-panel demographic figure for the AMC database.

a) Sex, b) Race, c) Age group at adoption, d) Transition number group (donuts)
e) Country of origin (world map), f) State of residence (US map)

Data: released BLOOM_BUTTERFLY.csv (location resolved by bloom_data.py).
Cleaning trims whitespace and drops blanks.
Run from anywhere: python "Demographic Figure.py"
"""
from pathlib import Path
from bloom_data import load_butterfly
from panel_exports import export_panels
from textwrap import fill

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import colors as mcolors
from matplotlib.gridspec import GridSpec
from shapely import affinity

HERE = Path(__file__).resolve().parent
MAPS = HERE / "Map Data"
OUT = HERE / "Figures" / "Demographics"

# Teal gradient for geographic counts.
CMAP = mcolors.LinearSegmentedColormap.from_list("teal", ["#E6F7F8", "#7FDFE2", "#00BFC4", "#007B80", "#00383B"])
# Preserve earlier donut palettes so they can be restored by changing one setting.
DONUT_PALETTES = {
    "map_teal": [mcolors.to_hex(CMAP(position)) for position in np.linspace(1, 0, 6)],
    "original": ["#F8766D", "#00BFC4", "#00BA38", "#F564E3", "#B79F00", "#619CFF"],
    "warm_alternative": ["#D55E00", "#CC79A7", "#E6AB02", "#7570B3", "#A6761D", "#777777"],
}
DONUT_PALETTE = "map_teal"
DONUT_COLORS = DONUT_PALETTES[DONUT_PALETTE]


def load_manual():
    return load_butterfly()


def clean_str(s: pd.Series) -> pd.Series:
    s = s.astype("string").str.strip()
    return s[s.notna() & (s != "")]


def tally_sex(df):
    return clean_str(df["Sex"]).value_counts().sort_index()


def tally_race(df):
    race = clean_str(df["Race"]).replace({"Unknown / Not Reported": "Other / Unclassified"})
    race = race.replace({"Native Hawaiian or Other Pacific Islander": "Pacific Islander"})
    return race.value_counts().sort_index()


def tally_age_group(df):
    years = pd.to_numeric(df["Age_at_adoption"], errors="coerce").dropna() / 12  # stored in months
    groups = pd.cut(years, [-np.inf, 5, 10, 15, np.inf], right=False, labels=["Under 5", "5-10", "10-15", "15-21"])
    counts = groups.value_counts().reindex(["Under 5", "5-10", "10-15", "15-21"])
    adopted = clean_str(df["Was_this_child_adopted_at_time_of_amc_visit"]).str.lower().eq("yes")
    missing_age = pd.to_numeric(df["Age_at_adoption"], errors="coerce").isna()
    counts["Unknown"] = int((adopted.reindex(df.index, fill_value=False) & missing_age).sum())
    return counts


def tally_transitions(df):
    t = pd.to_numeric(df["Number_of_transitions"], errors="coerce")
    labels = t.map(lambda v: "Unknown" if pd.isna(v) else "4+ Transitions" if v >= 4
                   else f"{int(v)} Transition" + ("" if v == 1 else "s"))
    return labels.value_counts().sort_index()


def donut(fig, spec, counts, title, panel):
    inner = spec.subgridspec(2, 2, height_ratios=[0.18, 0.82],
                            width_ratios=[1, 2.3], wspace=0.06, hspace=0)
    ax, lax = fig.add_subplot(inner[1, 0]), fig.add_subplot(inner[1, 1])
    lax.set_axis_off()
    counts = counts[counts > 0]
    # Every donut draws from the same 6-color palette, by position
    colors = DONUT_COLORS[:len(counts)]
    # ggplot draws the last level first, clockwise from 12 o'clock
    ax.pie(counts.values[::-1], colors=colors[::-1], startangle=90, counterclock=False,
           wedgeprops=dict(width=0.45, edgecolor="white", linewidth=0.6))
    title_ax = fig.add_subplot(spec, frameon=False)
    title_ax.set_axis_off()
    title_ax.text(0.5, 0.98, title, transform=title_ax.transAxes, fontsize=8, fontweight="bold", va="top", ha="center")
    title_ax.text(0.02, 0.98, panel, transform=title_ax.transAxes, fontsize=14, fontweight="bold", va="top")
    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in colors]
    labels = [f"{k} (n = {v:,}, {100 * v / counts.sum():.1f}%)"
              for k, v in counts.items()]
    if panel != "b":
        labels = [fill(label, width=40) for label in labels]
    lax.legend(handles, labels, loc="center left", frameon=False, fontsize=6.5,
               borderaxespad=0, ncol=1, handlelength=1.0, handletextpad=0.5, labelspacing=0.25)


COUNTRY_FIXES = {
    "Columbia": "Colombia", "Colombian": "Colombia", "Indian": "India", "Philipines": "Philippines",
    "Uganada": "Uganda", "Korea": "South Korea", "Democratic Republic of Congo": "Dem. Rep. Congo",
    "Marshall Islands": "Marshall Is.", "United States": "United States of America",
    "Dominican Republic": "Dominican Rep.",
}


def tally_countries(df):
    born_us = clean_str(df["Was_this_child_born_in_america"]).str.lower().eq("yes").sum()
    countries = clean_str(df["Country_of_origin"]).replace(COUNTRY_FIXES).value_counts()
    countries["United States of America"] = born_us
    return countries


def tally_states(df):
    return clean_str(df["State"]).str.upper().value_counts()


def shift_state(geom, name):
    # Move Alaska and Hawaii below the contiguous states
    if name == "AK":
        geom = affinity.scale(geom, 0.35, 0.35, origin=(-150, 64))
        return affinity.translate(geom, 32, -38)
    if name == "HI":
        return affinity.translate(geom, 50, 4)
    return geom


COUNTRY_DISPLAY = {"Dem. Rep. Congo": "Democratic Republic of Congo", "Marshall Is.": "Marshall Islands",
                   "United States of America": "United States", "Dominican Rep.": "Dominican Republic"}

# Small eastern states are labeled offshore with a leader line: postal -> (label x, label y)
STATE_OFFSETS = {"VT": (-74, 48.6), "NH": (-65.5, 44.2), "MA": (-65.5, 41.8), "RI": (-65.5, 39.6),
                 "CT": (-65.5, 37.6), "NJ": (-65.5, 35.6), "DE": (-65.5, 33.6), "MD": (-65.5, 31.6),
                 "DC": (-65.5, 28.8), "MS": (-90.5, 28.5), "AL": (-86.5, 29.5), "SC": (-77.5, 32)}
COUNTRY_OFFSETS = {
    "Latvia": (38, 76), "Lithuania": (10, 76), "Poland": (-22, 81), "Hungary": (-22, 61), "Romania": (-22, 71),
    "Serbia": (-22, 51), "Bulgaria": (-22, 41), "Albania": (-22, 31),
    "Burkina Faso": (8, 21), "Sierra Leone": (-38, 17), "Liberia": (-38, -3), "Ghana": (-12, -4),
    "Somalia": (58, 8), "Kenya": (58, 0), "Uganda": (58, -12), "Burundi": (47, -25), "Dem. Rep. Congo": (4, -20),
    "Kyrgyzstan": (66, 30),
    "Thailand": (92, -2), "Cambodia": (106, -7), "Vietnam": (116, 3), "Taiwan": (128, 27), "Philippines": (134, 13),
    "South Korea": (151, 30), "Marshall Is.": (158, 4),
    "Guatemala": (-120, 20), "Honduras": (-114, 12), "Costa Rica": (-108, 4), "Haiti": (-84, 22),
    "Dominican Rep.": (-64, 34), "Grenada": (-43, 37), "Guyana": (-52, 3), "Ecuador": (-102, -6), "Peru": (-98, -14),
}


def place_label(ax, x, y, name, n, size, norm, off=None):
    on_dark = n is not None and norm(n) > 0.6
    px, py = x, y
    if off is not None:
        x, y, on_dark = off[0], off[1], False
    if n is None:
        texts = [ax.text(x, y, name, fontsize=size + 0.5, ha="center", va="center", color="#555555", zorder=4)]
    else:
        big = size + (2 if n >= 100 else 0)
        color = "white" if on_dark else "black"
        texts = [ax.text(x, y, f"{n}", fontsize=big, fontweight="bold", ha="center", va="bottom",
                         color=color, zorder=4),
                 ax.text(x, y, name, fontsize=size + 0.5, ha="center", va="top", color=color, zorder=4)]
    if off is not None:
        # End the leader line at the edge of the label box instead of its center
        ax.apply_aspect()
        rend = ax.figure.canvas.get_renderer()
        boxes = [t.get_window_extent(rend) for t in texts]
        x0, x1 = min(b.x0 for b in boxes), max(b.x1 for b in boxes)
        y0, y1 = min(b.y0 for b in boxes), max(b.y1 for b in boxes)
        dx, dy = ax.transData.transform((px, py))
        if x0 - 2 < dx < x1 + 2 and y0 - 2 < dy < y1 + 2:
            return
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        ox, oy = max(x0 - dx, dx - x1, 0), max(y0 - dy, dy - y1, 0)
        if name == "Dominican\nRepublic":
            # Keep the short leader distinct from the neighboring island lines.
            ex, ey = cx, y0 - 3
        elif off[0] == -65.5:
            # A shared offshore column needs lines to enter from the left,
            # keeping them clear of the labels immediately above it.
            ex, ey = x0 - 3, cy
        elif oy > ox:
            ex, ey = cx, (y1 + 2 if dy > y1 else y0 - 2)
        else:
            ex, ey = (x1 + 2 if dx > x1 else x0 - 2), cy
        ex, ey = ax.transData.inverted().transform((ex, ey))
        if name == "Dominican\nRepublic":
            ex, ey = x, y - 8
        leader_width = 0.6 if name == "Dominican\nRepublic" else 0.3
        if name == "Sierra Leone":
            # A small arrow distinguishes Sierra Leone from nearby Liberia.
            ax.annotate("", xy=(px, py), xytext=(x + 13, y - 1),
                        arrowprops=dict(arrowstyle="->", color="#555555",
                                        linewidth=.5, mutation_scale=4, shrinkA=0, shrinkB=0),
                        zorder=3)
        else:
            ax.plot([px, ex], [py, ey], color="#555555", linewidth=leader_width, zorder=3)
        ax.plot([px], [py], marker="o", markersize=1.5, color="#333333", zorder=5)


def choropleth(ax, gdf, counts, key, name_col, label_size, offsets, label_all=False, vmin=1):
    gdf = gdf.copy()
    gdf["n"] = gdf[key].map(counts)
    norm = mcolors.LogNorm(vmin=vmin, vmax=max(counts.max(), 10))
    gdf.plot(ax=ax, color="#E6E6E6", edgecolor="white", linewidth=0.2)
    has = gdf[gdf["n"].notna()]
    has.plot(ax=ax, column="n", cmap=CMAP, norm=norm, edgecolor="white", linewidth=0.2)
    ax.set_axis_off()
    for _, row in (gdf if label_all else has).iterrows():
        k = row[key]
        pt = row.geometry.representative_point()
        if k == "MI":
            # Keep the label inside the larger (Lower) Peninsula.
            pt = max(row.geometry.geoms, key=lambda part: part.area).representative_point()
        x, y = (-98, 39) if k == "United States of America" else (pt.x, pt.y)
        if k == "Ukraine":
            x += 4
        n = None if pd.isna(row["n"]) else int(row["n"])
        name = COUNTRY_DISPLAY.get(row[name_col], row[name_col])
        if k == "Dominican Rep.":
            name = "Dominican\nRepublic"
        place_label(ax, x, y, name, n, label_size, norm, offsets.get(k))
    return norm


def colorbar(fig, ax, norm, label):
    sm = plt.cm.ScalarMappable(norm=norm, cmap=CMAP)
    cb = fig.colorbar(sm, ax=ax, fraction=0.02, pad=0.005, shrink=0.8)
    cb.set_label(label, fontsize=7, labelpad=1)
    cb.ax.tick_params(labelsize=6)
    return cb


def make_figure(df):
    # Map slots remain taller than their fixed-aspect drawing bounds, so the
    # maps keep a constant physical width and height.
    fig = plt.figure(figsize=(7.48, 9))
    gs = GridSpec(4, 2, figure=fig, height_ratios=[1.20, 1.10, 3.02, 3.54], wspace=0.05, hspace=0.0,
                  left=0.01, right=0.95, top=0.99, bottom=0.005)

    donut(fig, gs[0, 0], tally_sex(df).sort_values(ascending=False), "Sex (%)", "a")
    donut(fig, gs[0, 1], tally_race(df).sort_values(ascending=False), "Race (%)", "b")
    donut(fig, gs[1, 0], tally_age_group(df), "Age at Adoption (%)", "c")
    donut(fig, gs[1, 1], tally_transitions(df), "Transition Number (%)", "d")

    world = gpd.read_file(MAPS / "countries")
    world = world[world["NAME"] != "Antarctica"]
    ax_e = fig.add_subplot(gs[2, :])
    norm = choropleth(ax_e, world, tally_countries(df), "NAME", "NAME", 5, COUNTRY_OFFSETS)
    ax_e.set_xlim(-180, 180)
    ax_e.set_ylim(-58, 85)
    ax_e.set_title("Country of Origin (n)", fontsize=8, fontweight="bold", pad=4)
    ax_e.text(0.0, 0.98, "e", transform=ax_e.transAxes, fontsize=14, fontweight="bold", va="top")
    cb_e = colorbar(fig, ax_e, norm, "# Adoptees (log scale)")

    states = gpd.read_file(MAPS / "states")
    # State boundaries include lake waters; remove them to show Michigan's
    # two peninsulas and the surrounding Great Lakes shorelines.
    lakes = gpd.read_file(MAPS / "great_lakes.geojson").to_crs(states.crs)
    states["geometry"] = states.geometry.difference(lakes.geometry.union_all())
    states["geometry"] = [shift_state(g, p) for g, p in zip(states.geometry, states["postal"])]
    ax_f = fig.add_subplot(gs[3, :])
    norm = choropleth(ax_f, states, tally_states(df), "postal", "name", 5, STATE_OFFSETS, label_all=True)
    ax_f.set_xlim(ax_f.get_xlim()[0], -56)
    ax_f.set_title("U.S. State of Residence (n)", fontsize=8, fontweight="bold", y=0.96, pad=0)
    ax_f.text(0.0, 0.98, "f", transform=ax_f.transAxes, fontsize=14, fontweight="bold", va="top")
    cb_f = colorbar(fig, ax_f, norm, "# Adoptees (log scale)")
    # Bring the state map, its title, and its colorbar 0.12 inches closer to e.
    for ax in (ax_f, cb_f.ax):
        ax.set_position(ax.get_position(original=True).translated(0, 0.12 / fig.get_figheight()))
    # Use the bottom margin while preserving the spacing between the two maps.
    for ax in (ax_e, cb_e.ax, ax_f, cb_f.ax):
        ax.set_position(ax.get_position(original=True).translated(0, -0.16 / fig.get_figheight()))
    return fig


if __name__ == "__main__":
    data = load_manual()
    OUT.mkdir(parents=True, exist_ok=True)
    figure = make_figure(data)
    for ext in ("png", "svg"):
        figure.savefig(OUT / f"PAN Paper Figure 1 - Demographic Figure.{ext}", dpi=300, transparent=True)
    export_panels(figure, OUT, "PAN Paper Figure 1 - Demographic Figure", {
        **{label: (figure.axes[i * 3:i * 3 + 3], []) for i, label in enumerate([
            'a - Sex', 'b - Race', 'c - Age at Adoption', 'd - Transition Number'])},
        'e - Country of Origin': (figure.axes[12:14], []),
        'f - US State of Residence': (figure.axes[14:16], []),
    })
    print("Saved to", OUT)
