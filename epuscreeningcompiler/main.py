import os
import shutil
import sys
import xml.etree.ElementTree as ET
from . import image, epu, html_output

FONT_PATH = os.path.join(os.path.dirname(__file__), "fonts", "DejaVuSans.ttf")


def warn(message):
    print(message, file=sys.stderr, flush=True)


def error_die(message):
    sys.exit(f"{sys.argv[0]}: {message}")


def process_session(session, output_root, onlypng=False, verbose=False):
    session_output = os.path.join(str(output_root), session.session_name)
    os.makedirs(session_output, exist_ok=True)

    if verbose:
        print(f"Processing session '{session.session_name}'")

    # --- Atlas images ---
    if not os.path.isfile(session.atlas_image_path):
        warn(f"  Atlas image not found at {session.atlas_image_path}, skipping atlas images")
    else:
        # for speed, atlases don't need sigma contrasting, so just scale values as-is
        atlas_arr = image.image_file_to_arr(session.atlas_image_path)
        image.scale_arr(atlas_arr, inplace=True)
        image.arr_to_png(atlas_arr, os.path.join(session_output, "atlas.png"))
        if not onlypng:
            shutil.copy2(session.atlas_image_path, session_output)
        atlas_img, atlas_canvas = image.arr_to_drawable_img(atlas_arr)

        # Size font to fit the smallest selected gridsquare
        selected_with_geom = [session.gridsquares[x] for x in session.selected_gridsquares
                               if x in session.gridsquares and session.gridsquares[x].vertices]
        if selected_with_geom:
            smallest_r = min(g.radius for g in selected_with_geom)
            max_label_px = smallest_r * epu.ATLAS_SQUARE_DRAWING_SIZE_FUDGE
            gs_label_font = image.maximize_font_to_fit(
                canvas=atlas_canvas, font_path=FONT_PATH,
                text=next(iter(session.gridsquares.values())).id_str,
                max_text_length=max_label_px, min_font_size=10)
        else:
            gs_label_font = None

        # atlas_selected.png — selected gridsquares with color + label
        for sel_id in session.selected_gridsquares:
            sq = session.gridsquares.get(sel_id)
            if sq is None or not sq.vertices:
                continue
            image.draw_gridsquare(atlas_canvas, sq.vertices,
                                  color=epu.ATLAS_CATEGORY_COLOR_MAP.get(sq.category, "red"),
                                  label=sel_id, label_font=gs_label_font,
                                  label_pos=(sq.x_pos, sq.y_pos), label_textcolor="red")
        atlas_img.save(os.path.join(session_output, "atlas_selected.png"),
                       format='png', compress_level=9)

        # atlas_categories.png — add all remaining gridsquares (color only)
        for gs_id, sq in session.gridsquares.items():
            if gs_id in session.selected_gridsquares or not sq.vertices:
                continue
            image.draw_gridsquare(atlas_canvas, sq.vertices,
                                  color=epu.ATLAS_CATEGORY_COLOR_MAP.get(sq.category, "red"))
        atlas_img.save(os.path.join(session_output, "atlas_categories.png"),
                       format='png', compress_level=9)

    # --- Per-gridsquare images ---
    for sel_id in session.selected_gridsquares:
        sq = session.gridsquares.get(sel_id)
        if sq is None:
            continue

        gs_output = os.path.join(session_output, f"GridSquare_{sq.id_str}")
        acq_output = os.path.join(gs_output, "Data")
        hole_output = os.path.join(gs_output, "FoilHoles")
        os.makedirs(acq_output, exist_ok=True)
        os.makedirs(hole_output, exist_ok=True)

        if verbose:
            print(f"  GridSquare_{sq.id_str}: {len(sq.holes)} holes")

        if os.path.isfile(sq.image_path):
            # for speed, gridsquare images also don't need sigma contrasting
            gs_arr = image.image_file_to_arr(sq.image_path)
            image.scale_arr(gs_arr, inplace=True)
            image.arr_to_png(gs_arr, os.path.join(gs_output, f"GridSquare_{sq.id_str}.png"))
            if not onlypng:
                shutil.copy2(sq.image_path, gs_output)

            if sq.holes:
                gs_img, gs_canvas = image.arr_to_drawable_img(gs_arr)
                smallest_hole = min(sq.holes.values(), key=lambda h: h.radius)
                max_hole_label_px = smallest_hole.radius * 3 * epu.GRIDSQUARE_HOLE_DRAWING_SIZE_FUDGE
                hole_label_font = image.maximize_font_to_fit(
                    canvas=gs_canvas, font_path=FONT_PATH,
                    text=str(smallest_hole.id_str),
                    max_text_length=max_hole_label_px, min_font_size=10)
                for hole in sq.holes.values():
                    image.draw_hole(gs_canvas,
                                   coord=(hole.x_pos, hole.y_pos),
                                   radius=hole.radius * epu.GRIDSQUARE_HOLE_DRAWING_SIZE_FUDGE,
                                   label=hole.id_str, label_font=hole_label_font)
                gs_img.save(os.path.join(gs_output, f"GridSquare_{sq.id_str}_annotated.png"),
                            format='png', compress_level=9)
        else:
            if verbose:
                warn(f"  GridSquare_{sq.id_str}: image not found at {sq.image_path!r}")

        for hole in sq.holes.values():
            if hole.image_path is not None:
                # image_path may be absolute (after path mapping) or relative to session_dir
                hole_src = os.path.join(session.session_dir, hole.image_path)
                if os.path.isfile(hole_src):
                    hole_arr = image.image_file_to_arr(hole_src)
                    image.auto_contrast_arr(hole_arr, sigma=image.DefaultSigmaContrast.HOLE, inplace=True)
                    image.arr_to_png(hole_arr,
                                     os.path.join(hole_output, f"FoilHole_{hole.id_str}.png"))
                    if not onlypng:
                        shutil.copy2(hole_src, hole_output)

            for acq_path in hole.acquisitions:
                acq_src = os.path.join(session.session_dir, acq_path)
                if os.path.isfile(acq_src):
                    acq_arr = image.image_file_to_arr(acq_src)
                    image.auto_contrast_arr(acq_arr, sigma=image.DefaultSigmaContrast.DATA, inplace=True)
                    stem = os.path.splitext(os.path.basename(acq_src))[0]
                    image.arr_to_png(acq_arr,
                                     os.path.join(acq_output, f"{stem}.png"))
                    if not onlypng:
                        shutil.copy2(acq_src, acq_output)

        html_output.generate_gridsquare_html(session, sq, gs_output)

    html_output.generate_session_html(session, session_output)


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Create a simplified, annotated file hierarchy from EPU screening data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Path remapping:\n"
            "  Set EPU_PATH_MAP to remap Windows paths embedded in EPU metadata to local paths.\n"
            "  Format: 'WIN_PATH1=LOCAL_PATH1;WIN_PATH2=LOCAL_PATH2'\n"
            "  Example: EPU_PATH_MAP='Y:/Data=/mnt/data;D:/Atlas=/mnt/atlas'"
        ))
    parser.add_argument("--atlas",
                        help="Root folder for the Atlas session. If omitted the path embedded in the "
                             "EPU metadata is used (applying EPU_PATH_MAP if it exists).")
    parser.add_argument("--output", required=True,
                        help="Root folder for the output hierarchy")
    parser.add_argument("--onlypng", action="store_true",
                        help="Only write PNG files; do not copy source MRC/TIFF files")
    parser.add_argument("--verbose", action="store_true",
                        help="Print progress information")
    parser.add_argument("epu_sessions", nargs="+",
                        help="Root folder(s) for EPU data collection sessions (each must contain EpuSession.dm)")
    args = parser.parse_args()

    # Build PATH_MAP from EPU_PATH_MAP environment variable
    path_map = {}
    env_path_map = os.environ.get("EPU_PATH_MAP", "")
    if env_path_map:
        for pair in env_path_map.split(";"):
            if "=" in pair:
                win_path, _, local_path = pair.partition("=")
                path_map[epu.windows_to_posix_path(win_path)] = local_path
    epu.PATH_MAP = path_map

    for session_dir in args.epu_sessions:
        if not os.path.isfile(os.path.join(session_dir, "EpuSession.dm")):
            error_die(f"{session_dir}: cannot find EpuSession.dm")

        if args.verbose:
            print(f"Parsing {session_dir}")
        session = epu.parse_epu_session(session_dir)

        # Resolve atlas metadata path
        if args.atlas:
            # path to the atlas is  root/SampleX/Atlas/Atlas.dm where X is autoloader_slot + 1
            atlas_dm = os.path.join(args.atlas, f"Sample{session.autoloader_slot + 1}", "Atlas", "Atlas.dm")
            session.atlas_file = atlas_dm
        if not os.path.isfile(session.atlas_file):
            error_die(f"Cannot find Atlas.dm at {session.atlas_file}. Use --atlas to point to the atlas session folder,"
                      f"or set EPU_PATH_MAP to remap the path in the EPU metadata.")
        if args.verbose:
            print(f"  Atlas: {session.atlas_file}")
        epu.populate_session_with_atlas(session)

        process_session(session, args.output, onlypng=args.onlypng, verbose=args.verbose)
