import datetime
import os
import re
from PIL import Image
import jinja2

from . import epu as epu_module

_TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")
# the templates are named *.html.j2, so "j2" (not just "html") has to be enabled for autoescaping to apply to them
_jinja_env = jinja2.Environment(loader=jinja2.FileSystemLoader(_TEMPLATES_DIR),
                                autoescape=jinja2.select_autoescape(["html", "j2"]))

_MONTH_NAMES = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def format_collected_date(start_time):
    """
    Format the date part of an EPU session start time, e.g. ``2026-06-04T17:05:58.6874479Z`` -> ``4 Jun 2026``.

    The date is taken as written in the string (for the ``Z`` form that is the UTC date), without any timezone
    conversion. The string is picked apart with a regular expression because ``datetime.fromisoformat`` does not accept
    EPU's 7 fractional digits on older Pythons. Month names are not locale dependent.

    Returns
    -------
    str or None
        The formatted date, or None if `start_time` is missing or does not start with a valid ``YYYY-MM-DD``.
    """
    match = re.match(r"\s*(\d{4})-(\d{2})-(\d{2})", start_time or "")
    if match is None:
        return None
    try:
        date = datetime.date(*(int(x) for x in match.groups()))
    except ValueError:
        return None
    return f"{date.day} {_MONTH_NAMES[date.month - 1]} {date.year}"


def _ordered_square_ids(session):
    """
    IDs of the selected gridsquares that get a page, sorted. This is the ordering used for the atlas chips and
    cards, the "i of n" in the gridsquare header, and the previous/next links.
    """
    # for now we just sort the selected_gridsquares set. but this is where different ordering could be implemented.
    return sorted(session.selected_gridsquares)


def _hole_records(square, gs_output):
    """
    The per-hole data for a gridsquare page, in parser order. Paths are relative to the gridsquare page. Only images
    that were actually written to `gs_output` are listed, so that counts and displayed images agree.
    """
    holes = []
    for hole in square.holes.values():
        exposures = []
        for acq in hole.acquisitions:
            path = f"Data/{os.path.splitext(os.path.basename(acq.image_path))[0]}.png"
            if os.path.isfile(os.path.join(gs_output, path)):
                exposures.append({"path": path, "pixel_size": acq.pixel_size})
        foilhole = None
        if hole.image is not None:
            path = f"FoilHoles/FoilHole_{hole.id_str}.png"
            if os.path.isfile(os.path.join(gs_output, path)):
                foilhole = {"path": path, "pixel_size": hole.image.pixel_size}
        holes.append({
            "id": hole.id_str,
            "cx": round(hole.x_pos, 2),
            "cy": round(hole.y_pos, 2),
            "r": round(hole.radius * epu_module.GRIDSQUARE_HOLE_DRAWING_SIZE_FUDGE, 2),
            "exposures": exposures,
            "foilhole": foilhole,
        })
    return holes


def generate_html(session, session_output, has_atlas=True):
    """
    Write the HTML pages for a session: the root ``index.html`` (the atlas page, or just the gridsquare cards if
    there is no atlas) and the ``GridSquare_<id>/index.html`` page of each gridsquare whose gridsquare image was written.

    This has to be called after all the PNG files have been written to `session_output`: the pages only list the images
    that exist there.
    """
    atlas_width = atlas_height = None
    if has_atlas:
        with Image.open(os.path.join(session_output, "atlas.png")) as atlas_png:
            atlas_width, atlas_height = atlas_png.size

    date_collected = format_collected_date(session.start_time)

    ordered_square_ids = _ordered_square_ids(session)

    # gridsquare lookup with wraparound for prev/next navigation, returns dict expected by gridsquare jinja template
    def neighbor(neighbor_i):
        unwrapped_i = neighbor_i % len(ordered_square_ids)
        this_id = ordered_square_ids[unwrapped_i]
        return {"id": this_id,
                "index": unwrapped_i + 1,
                "href": f"../GridSquare_{this_id}/index.html"}

    gridsquare_template = _jinja_env.get_template("gridsquare_index.html.j2")
    gridsquares = []
    for position, gs_id in enumerate(ordered_square_ids):
        square = session.gridsquares[gs_id]
        gs_output = os.path.join(session_output, f"GridSquare_{gs_id}")
        holes = _hole_records(square, gs_output)
        n_holes = len(holes)
        n_data_exposures = sum(len(hole["exposures"]) for hole in holes)
        n_foilhole_exposures = sum(1 for hole in holes if hole["foilhole"] is not None)
        square_index = position + 1  # "index" on the html pages is base 1 not 0

        # build `gridsquares`, a list of the needed per-gridsquare information in dict format so jinja can use it
        # the actual gridsquare pages don't use most of this, but the session/atlas/root page does
        gridsquares.append({
            "id": gs_id,
            "index": square_index,
            "points": " ".join(f"{x:.2f},{y:.2f}" for x, y in square.vertices) if square.vertices else None,
            "href": f"GridSquare_{gs_id}/index.html",
            "thumb": f"GridSquare_{gs_id}/GridSquare_{gs_id}.png",
            "n_holes": n_holes,
            "n_exposures": n_data_exposures,
            "n_foilholes": n_foilhole_exposures,
        })

        gs_png = os.path.join(gs_output, f"GridSquare_{gs_id}.png")
        if not os.path.isfile(gs_png):
            continue  # no image was generated (source missing), skip this page
        with Image.open(gs_png) as gs_image:
            gs_width, gs_height = gs_image.size

        html = gridsquare_template.render(
            session_name=session.session_name,
            collected=date_collected,
            gs_id=gs_id,
            index=square_index,
            n_gridsquares=len(ordered_square_ids),
            prev=neighbor(position - 1), # the index arg for `neighbor` is base 0, but it returns base 1 for the html
            next=neighbor(position + 1),
            gs_width=gs_width,
            gs_height=gs_height,
            gs_pixel_size=square.image.pixel_size,
            holes=holes,
            n_holes=n_holes,
            n_exposures=n_data_exposures,
            n_foilholes=n_foilhole_exposures,
        )
        with open(os.path.join(gs_output, "index.html"), "w", encoding="utf-8") as f:
            f.write(html)

    n_session_exposures = sum(g["n_exposures"] for g in gridsquares)
    html = _jinja_env.get_template("session_index.html.j2").render(
        session_name=session.session_name,
        collected=date_collected,
        n_exposures=n_session_exposures,
        has_atlas=has_atlas,
        atlas_width=atlas_width,
        atlas_height=atlas_height,
        atlas_pixel_size=session.atlas_image.pixel_size if session.atlas_image is not None else 0.0,
        gridsquares=gridsquares,
    )
    with open(os.path.join(session_output, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)
