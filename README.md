# EPUScreeningCompiler

Convert the raw output of ThermoFisher EPU automated grid screening sessions into a useful, portable set of files: 
- The raw data MRC or TIFF files
- Full-resolution, nicely contrasted PNG images for easy viewing, putting in presentations, etc
- The atlas -- including a version with the color coded categorization you saw at the microscope
- Annotated versions of the atlas and gridsquares documenting which squares and holes were imaged
- Interactive HTML reports. You click the squares and holes on the images to navigate. Responsive live scale bars, image zoom and pan.

<!-- TODO: screenshot or short GIF of the atlas report and a gridsquare report -->

## Why

The files EPU writes during automated acquisition are cumbersome to look at later when the goal is visual screening. Problems include:

- EPU keeps every gridsquare and hole image it takes, leading to several duplicates from square and hole re-centering
- EPU's JPG previews are 4x downsampled, while the full-resolution MRC/TIFF files are not convenient to view on most PCs
- EPU names output files using long unique ID numbers that are not otherwise exposed in the EPU GUI. Good for avoiding filename collisions but bad for humans.
- Atlas images are saved in an entirely different location from the data collection session

## Details

*epuscreeningcompiler* reads the XML metadata files in the given EPU sessions the and the associated atlas session to understand what happened. The user only needs to provide the paths to these directories. The output is a folder hierarchy in the style of EPU sessions themselves, but with files that are more friendly :-) 

The HTML output is entirely self-contained and dependency free -- no internet connection required.

## Installation

Requires Python 3.8 or newer.

```bash
pip install git+https://github.com/fullerjamesr/epuscreeningcompiler.git
```

<!-- TODO: confirm this URL once the repository is published -->

## Usage

```bash
epuscreeningcompiler --output OUTPUT_DIR [--atlas ATLAS_SESSION_DIR] [--onlypng] [--verbose] EPU_SESSION_DIR [EPU_SESSION_DIR ...]
```

or, without installing the command: `python -m epuscreeningcompiler ...`

| Argument          | Description                                                                                |
|-------------------|--------------------------------------------------------------------------------------------|
| `EPU_SESSION_DIR` | Root folder of one of more EPU data collection sessions (contains `EpuSession.dm`).        |
| `--output`        | Root folder for the output. A subfolder named after each session is created.               |
| `--atlas`         | Root folder of the atlas session. If omitted, the path stored in the EPU metadata is used. |
| `--onlypng`       | Write PNG files only; do not also copy the original MRC/TIFF files.                        |
| `--verbose`       | Print progress information.                                                                |

### Finding the atlas session

The EPU session metadata records the path to its atlas session, but that path is probably only valid on the
Windows PC that controls the microscope. There are two ways to point the tool at the atlas session:

1. Pass `--atlas` with the root of the atlas session directory. This overrides the path in the
   metadata entirely.
2. Populate the `EPU_PATH_MAP` environment variable with find/replace rules to be applied to the path read from
   the metadata. This is intended for machines that mount the same drives as the microscope PC under
   different paths:

   ```bash
   export EPU_PATH_MAP='Y:/Data=/mnt/data;D:/Atlas=/mnt/atlas'
   ```

   Format: `WIN_PATH1=LOCAL_PATH1;WIN_PATH2=LOCAL_PATH2`.

If the atlas session can't be found, the app prints a warning and
carries on without it, skipping any outputs that require the atlas images/information.

### Example

```bash
epuscreeningcompiler \
  --atlas /data/atlas_session/Supervisor_20260604_103634 \
  --output /data/screening_reports \
  --onlypng \
  /data/epu_session/20260604_sample_1
```

### Output layout

All MRC files are direct copies of the EPU outputs. All PNG files maintain the full resolution of the source MRC files.
Output folder and file structure is similar the structure of EPU sessions, but simplified and with atlases at the root:
```
<session_name>/
  index.html                                       interactive atlas/overview page
  atlas.[png, mrc]                                 plain atlas
  atlas_selected.png                               atlas with acquired gridsquares annotated
  atlas_categories.png                             atlas with EPU categorization annotations
  GridSquare_<id>/
    index.html                                     interactive gridsquare page
    GridSquare_<id>.[png, mrc]                     gridsquare image
    GridSquare_<id>_annotated.png                  gridsquare image with acquired holes annotated
    FoilHoles/
      FoilHole_<id>.[png, mrc]                     most recent Foilhole images for all imaged holes
      ...
    Data/
      FoilHole_<hole id>_Data_*_<id>.[png, mrc]    full magnification data images
```

## Supported data

Tested on MRC or TIFF output from EPU.

## Development

Help is welcome! Please disclose LLM usage if it was used to write the final code.

Claude was entirely responsible for the JavaScript in the HTML templates, as well much of the corresponding Python code in `html_output.py` that uses the templates. 
<!-- TODO: contributing notes, how to run the tests -->

## License

GPL-3.0-or-later. See [LICENSE](LICENSE).

The bundled DejaVu Sans font is distributed under its own license
(<https://dejavu-fonts.github.io/License.html>).
