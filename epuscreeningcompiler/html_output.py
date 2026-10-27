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


def _counts(holes):
    """ Returns tuple of (number of holes, number of exposures, number of foil hole images) for a list of holes"""
    return (len(holes),
            sum(len(hole["exposures"]) for hole in holes),
            sum(1 for hole in holes if hole["foilhole"] is not None))


def generate_session_html(session, session_output, has_atlas=True):
    atlas_width = atlas_height = None
    if has_atlas:
        with Image.open(os.path.join(session_output, "atlas.png")) as atlas_png:
            atlas_width, atlas_height = atlas_png.size

    gridsquares = []
    n_exposures = 0
    for index, gs_id in enumerate(_ordered_square_ids(session), start=1):
        square = session.gridsquares[gs_id]
        n_holes, n_gs_exposures, n_foilholes = _counts(
            _hole_records(square, os.path.join(session_output, f"GridSquare_{gs_id}")))
        n_exposures += n_gs_exposures
        gridsquares.append({
            "id": gs_id,
            "index": index,
            # the outline (and its label) on the atlas needs the polygon from the atlas metadata
            "points": " ".join(f"{x:.2f},{y:.2f}" for x, y in square.vertices) if square.vertices else None,
            "href": f"GridSquare_{gs_id}/index.html",
            "thumb": f"GridSquare_{gs_id}/GridSquare_{gs_id}.png",
            "n_holes": n_holes,
            "n_exposures": n_gs_exposures,
            "n_foilholes": n_foilholes,
        })

    template = _jinja_env.get_template("session_index.html.j2")
    html = template.render(
        session_name=session.session_name,
        collected=format_collected_date(session.start_time),
        n_exposures=n_exposures,
        has_atlas=has_atlas,
        atlas_width=atlas_width,
        atlas_height=atlas_height,
        atlas_pixel_size=session.atlas_image.pixel_size if session.atlas_image is not None else 0.0,
        gridsquares=gridsquares,
    )
    with open(os.path.join(session_output, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)


def generate_gridsquare_html(session, square, gs_output):
    gs_png = os.path.join(gs_output, f"GridSquare_{square.id_str}.png")
    if not os.path.isfile(gs_png):
        return  # no image was generated (source missing), skip HTML too
    with Image.open(gs_png) as gs_image:
        gs_width, gs_height = gs_image.size

    holes = _hole_records(square, gs_output)
    n_holes, n_exposures, n_foilholes = _counts(holes)

    # previous/next wrap around, so they are never disabled
    ids = _ordered_square_ids(session)
    position = ids.index(square.id_str)

    def neighbor(i):
        gs_id = ids[i % len(ids)]
        return {"id": gs_id, "index": i % len(ids) + 1, "href": f"../GridSquare_{gs_id}/index.html"}

    template = _jinja_env.get_template("gridsquare_index.html.j2")
    html = template.render(
        session_name=session.session_name,
        collected=format_collected_date(session.start_time),
        gs_id=square.id_str,
        index=position + 1,
        n_gridsquares=len(ids),
        prev=neighbor(position - 1),
        next=neighbor(position + 1),
        gs_width=gs_width,
        gs_height=gs_height,
        gs_pixel_size=square.image.pixel_size,
        holes=holes,
        n_holes=n_holes,
        n_exposures=n_exposures,
        n_foilholes=n_foilholes,
    )
    with open(os.path.join(gs_output, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)
