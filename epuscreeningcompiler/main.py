import functools
import glob
import os
import shutil
import sys
from . import image, epu, html_output

FONT_PATH = os.path.join(os.path.dirname(__file__), "fonts", "DejaVuSans.ttf")
WINDOWS = sys.platform == "win32"
WINDOWS_MAX_PATH = 260  # includes the terminating NUL, so at most 259 characters of a path are usable


def warn(message):
    print(message, file=sys.stderr, flush=True)


def error_die(message):
    sys.exit(f"{sys.argv[0]}: {message}")


@functools.lru_cache(maxsize=None)
def windows_long_paths_enabled():
    """
    Whether the Windows "long paths" setting (the `LongPathsEnabled` registry value, which the "Enable Win32 long
    paths" Group Policy also sets) is on. Always False on other operating systems, and also if the setting is missing.

    The setting is necessary but not sufficient: a program must also be long-path aware. Standard CPython builds on
    Windows are (Python 3.6+), so this is only a concern for embedded or frozen Python builds.
    """
    if not WINDOWS:
        return False
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\FileSystem") as key:
            return winreg.QueryValueEx(key, "LongPathsEnabled")[0] == 1
    except OSError:
        return False


def path_too_long_for_windows(path, extra=0):
    """
    Whether `path` (made absolute) would be too long for Windows to open, because it reaches the 260 character
    `MAX_PATH` limit and long paths are not enabled. When this is True, Windows fails to open the path (for example,
    `os.path.isfile` quietly returns False) even though it exists.

    Parameters
    ----------
    path : str or os.PathLike
        The path to check. It does not have to exist.
    extra : int
        The number of characters (including any separator) that will be added to the end of `path` before it is used,
        e.g., ``len("\\EpuSession.dm")`` for a file that will be joined on, or 2 for the "\\*" that Windows adds to
        a directory path to list its contents.

    Returns
    -------
    bool
        Always False on operating systems other than Windows, if long paths are enabled, or if `path` already has the
        `\\\\?\\` prefix that lifts the limit. Lengths are counted in UTF-16 code units, as Windows does (a character
        outside the Basic Multilingual Plane, e.g., most emoji, counts as 2).
    """
    path = os.fspath(path)
    if not WINDOWS or path.startswith("\\\\?\\") or windows_long_paths_enabled():
        return False
    utf16_length = len(os.path.abspath(path).encode("utf-16-le", "surrogatepass")) // 2
    return utf16_length + extra >= WINDOWS_MAX_PATH


def process_session(session, output_root, onlypng=False, verbose=False):
    session_output = os.path.join(str(output_root), session.session_name)
    os.makedirs(session_output, exist_ok=True)

    if verbose:
        print(f"Processing session '{session.session_name}'")

    # --- Atlas images ---
    # GridSquare HTML pages need to know if there is an atlas page to link back to
    atlas_written = False
    if session.atlas_image is None:
        pass  # no atlas metadata was available (outer scope like main() should have already warned)
    elif not os.path.isfile(session.atlas_image.image_path):
        warn(f"  Atlas image not found at {session.atlas_image.image_path}, no atlas output will be generated")
    else:
        # for speed, atlases don't need sigma contrasting, so just scale values as-is
        atlas_arr = image.image_file_to_arr(session.atlas_image.image_path)
        image.scale_arr(atlas_arr, inplace=True)
        image.arr_to_png(atlas_arr, os.path.join(session_output, "atlas.png"))
        if not onlypng:
            shutil.copy2(session.atlas_image.image_path, session_output)
        atlas_img, atlas_canvas = image.arr_to_drawable_img(atlas_arr)

        # Size font to fit the smallest selected gridsquare
        selected_with_geom = [session.gridsquares[x] for x in session.selected_gridsquares
                               if x in session.gridsquares and session.gridsquares[x].vertices]
        if selected_with_geom:
            max_label_px = min(image.horizontal_chord_through_center(g.vertices)
                               for g in selected_with_geom)
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
        atlas_written = True

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

        if os.path.isfile(sq.image.image_path):
            # gridsquare images are min/max contrasted, but clip hot pixels
            gs_arr = image.image_file_to_arr(sq.image.image_path)
            image.clip_extremes(gs_arr, inplace=True)
            image.scale_arr(gs_arr, inplace=True)
            image.arr_to_png(gs_arr, os.path.join(gs_output, f"GridSquare_{sq.id_str}.png"))
            if not onlypng:
                shutil.copy2(sq.image.image_path, gs_output)

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
                warn(f"  GridSquare_{sq.id_str}: image not found at {sq.image.image_path!r}")

        for hole in sq.holes.values():
            if hole.image is not None:
                hole_src = hole.image.image_path
                if os.path.isfile(hole_src):
                    hole_arr = image.image_file_to_arr(hole_src)
                    image.auto_contrast_arr(hole_arr, sigma=image.DefaultSigmaContrast.HOLE, inplace=True)
                    image.arr_to_png(hole_arr,
                                     os.path.join(hole_output, f"FoilHole_{hole.id_str}.png"))
                    if not onlypng:
                        shutil.copy2(hole_src, hole_output)

            for acq in hole.acquisitions:
                acq_src = acq.image_path
                if os.path.isfile(acq_src):
                    acq_arr = image.image_file_to_arr(acq_src)
                    image.auto_contrast_arr(acq_arr, sigma=image.DefaultSigmaContrast.DATA, inplace=True)
                    stem = os.path.splitext(os.path.basename(acq_src))[0]
                    image.arr_to_png(acq_arr,
                                     os.path.join(acq_output, f"{stem}.png"))
                    if not onlypng:
                        shutil.copy2(acq_src, acq_output)

        html_output.generate_gridsquare_html(session, sq, gs_output)

    html_output.generate_session_html(session, session_output, has_atlas=atlas_written)


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Create a simplified, annotated file hierarchy from EPU screening data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Path remapping:\n"
            "  Set EPU_PATH_MAP to remap Windows paths embedded in EPU metadata to local paths.\n"
            "  Format: 'WIN_PATH1=LOCAL_PATH1;WIN_PATH2=LOCAL_PATH2'\n"
            "  Example: EPU_PATH_MAP='Y:/Data=/mnt/data;D:/Atlas=/mnt/atlas'\n"
            "  Each WIN_PATH is matched (case insensitive) against the start of the path, on whole folder names;\n"
            "  if several match, the longest is used."
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

    # We need to support Windows because the scope PCs run windows. This leads to 2 annoying issues:
    # 1) Windows can have a limit of 260 characters on paths. We need to check that to warn users.
    # 2) Windows shells (cmd.exe, PowerShell) do not expand wildcards (sad!) so expand them here.
    #    Only arguments that don't exist as-is are treated as patterns, so that legal unix names containing `[`, `?` or
    #    `*`, or quoted patterns work on unix, work too.
    epu_sessions = []
    for session_arg in args.epu_sessions:
        if WINDOWS and path_too_long_for_windows(session_arg, extra=2):
            warn(f"SEVERE WARNING: Windows does not appear to be configured for long paths and the input path "
                 f"'{session_arg}' exceeds the length limit! Fatal errors may occur.")
        if os.path.isdir(session_arg):
            epu_sessions.append(session_arg)
            continue
        elif any(c in session_arg for c in "*?["):
            matches = sorted(glob.glob(session_arg))
            if matches:
                epu_sessions.extend(matches)
                continue
        # only reached if `session_arg` didn't work out
        error_die(f"{session_arg}: no paths match this path/pattern")
    args.epu_sessions = epu_sessions
    if WINDOWS:
        for p in args.epu_sessions:
            if path_too_long_for_windows(p, extra=103): # 103 is the longest likely path length to a movie file
                warn(f"SEVERE WARNING: Windows does not appear to be configured for long paths and input files in "
                     f"'{p}' are likely to exceed the path length limit! Fatal errors or missing files may occur.")
        # Paths inside output folder are 80 + session name, so the value before is a guess/fudge
        if path_too_long_for_windows(args.output, extra=120):
            warn(f"SEVERE WARNING: Windows does not appear to be configured for long paths and output files in "
                 f"'{args.output}' are likely to exceed the path length limit! Fatal errors or missing files may "
                 f"occur.")

    # Build PATH_MAP from EPU_PATH_MAP environment variable
    path_map = {}
    env_path_map = os.environ.get("EPU_PATH_MAP", "")
    if env_path_map:
        for pair in env_path_map.split(";"):
            if "=" in pair:
                win_path, _, local_path = pair.partition("=")
                path_map[win_path.strip()] = local_path.strip()
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
        if os.path.isfile(session.atlas_file):
            if args.verbose:
                print(f"  Atlas: {session.atlas_file}")
            epu.populate_session_with_atlas(session)
        else:
            warn(f"{session_dir}: cannot find Atlas.dm at {session.atlas_file}. Continuing without atlas "
                 f"information: no atlas images will be written. Use --atlas to point to the atlas session "
                 f"folder, or set EPU_PATH_MAP to remap the path in the EPU metadata.")

        # The session name becomes the name of the output subfolder, so it must be a plain, single folder name.
        # EPU only allows valid Windows folder names, so this should only fail if EpuSession.dm was edited after the
        # fact. Check if it's empty-like, or contains path separators (to guard against escaping to write outside the
        # `args.output` folder)
        name = session.session_name
        if (len(name.strip()) < 1
            or name in (".", "..")
            or any(c in name for c in "/\\:")
            or any(ord(c) < 32 for c in name)):
            error_die(f"{session_dir}: the session name {name!r} in EpuSession.dm cannot be used as a folder name "
                      f"(it must not be empty, '.' or '..', or contain any of / \\ : or control characters)")

        process_session(session, args.output, onlypng=args.onlypng, verbose=args.verbose)
