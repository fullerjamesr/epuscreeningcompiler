import os
from PIL import Image
import jinja2

from . import epu as epu_module

_TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")
_jinja_env = jinja2.Environment(loader=jinja2.FileSystemLoader(_TEMPLATES_DIR),
                                autoescape=jinja2.select_autoescape(["html"]))


def generate_session_html(session, session_output):
    atlas_png = os.path.join(session_output, "atlas_selected.png")
    atlas_width, atlas_height = Image.open(atlas_png).size

    gridsquares = []
    for sel_id in session.selected_gridsquares:
        sq = session.gridsquares.get(sel_id)
        if sq is None or not sq.vertices:
            continue
        vertices_str = " ".join(f"{x:.2f},{y:.2f}" for x, y in sq.vertices)
        gridsquares.append({
            "id_str": sq.id_str,
            "vertices_str": vertices_str,
            "link": f"GridSquare_{sq.id_str}/index.html",
        })

    template = _jinja_env.get_template("session_index.html.j2")
    html = template.render(
        session_name=session.session_name,
        atlas_width=atlas_width,
        atlas_height=atlas_height,
        gridsquares=gridsquares,
    )
    with open(os.path.join(session_output, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)


def generate_gridsquare_html(session, square, gs_output):
    gs_png = os.path.join(gs_output, f"GridSquare_{square.id_str}.png")
    if not os.path.isfile(gs_png):
        return  # no image was generated (source missing), skip HTML too
    gs_width, gs_height = Image.open(gs_png).size

    holes = []
    for hole in square.holes.values():
        data_pngs = [
            f"Data/{os.path.splitext(os.path.basename(p))[0]}.png"
            for p in hole.acquisitions
        ]
        foilhole_png = (
            f"FoilHoles/FoilHole_{hole.id_str}.png"
            if hole.image_path is not None else None
        )
        holes.append({
            "id_str": hole.id_str,
            "cx": f"{hole.x_pos:.2f}",
            "cy": f"{hole.y_pos:.2f}",
            "r": f"{hole.radius * epu_module.GRIDSQUARE_HOLE_DRAWING_SIZE_FUDGE:.2f}",
            "foilhole_png": foilhole_png,
            "data_pngs": data_pngs,
        })

    ordered = list(session.selected_gridsquares)
    ordered.sort()
    next_id = ordered[(ordered.index(square.id_str) + 1) % len(ordered)]
    next_link = f"../GridSquare_{next_id}/index.html"

    template = _jinja_env.get_template("gridsquare_index.html.j2")
    html = template.render(
        session_name=session.session_name,
        id_str=square.id_str,
        gs_width=gs_width,
        gs_height=gs_height,
        holes=holes,
        next_link=next_link,
    )
    with open(os.path.join(gs_output, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)
