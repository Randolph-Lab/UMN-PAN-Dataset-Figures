"""Export complete panels without the composite figure's letter labels."""
import matplotlib as mpl
from matplotlib.transforms import Bbox


def export_panels(fig, out, name, panels):
    """panels maps a descriptive name to (axes, figure-level text artists)."""
    folder = out / 'Individual Panels'
    folder.mkdir(parents=True, exist_ok=True)
    visibility = {artist: artist.get_visible() for artist in [*fig.axes, *fig.texts]}
    # Panel letters may live on the figure or on an auxiliary/title axis.
    letters = [text for text in [*fig.texts, *(text for ax in fig.axes for text in ax.texts)]
               if text.get_text().strip() in 'abcdefghijklmnopqrstuvwxyz'
               and len(text.get_text().strip()) == 1
               and text.get_fontweight() == 'bold']
    letter_visibility = {text: text.get_visible() for text in letters}
    old_fonttype = mpl.rcParams['svg.fonttype']
    mpl.rcParams['svg.fonttype'] = 'none'
    try:
        for panel_name, (axes, texts) in panels.items():
            selected = set([*axes, *texts])
            for artist, visible in visibility.items():
                artist.set_visible(visible and artist in selected)
            for text in letters:
                text.set_visible(False)
            fig.canvas.draw()
            renderer = fig.canvas.get_renderer()
            boxes = [artist.get_tightbbox(renderer) for artist in selected if artist.get_visible()]
            bounds = Bbox.union([box for box in boxes if box is not None])
            bounds = bounds.transformed(fig.dpi_scale_trans.inverted()).padded(.08)
            base = folder / f'{name} - {panel_name}'
            fig.savefig(f'{base} - Transparent Background.png', dpi=300,
                        transparent=True, bbox_inches=bounds)
            fig.savefig(f'{base} - White Background.png', dpi=300,
                        transparent=False, facecolor='white', bbox_inches=bounds)
            fig.savefig(f'{base}.svg', transparent=True, bbox_inches=bounds)
    finally:
        for artist, visible in visibility.items():
            artist.set_visible(visible)
        for text, visible in letter_visibility.items():
            text.set_visible(visible)
        mpl.rcParams['svg.fonttype'] = old_fonttype
    print(f'Saved {len(panels)} individual panels to {folder}')
