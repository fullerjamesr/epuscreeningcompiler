import xml.etree.ElementTree as ET
import pandas as pd
import numpy as np
import os.path
import re
from pathlib import PureWindowsPath
from enum import Enum
from dataclasses import dataclass


class _EPU:
    """Cross-document XML keys shared across all EPU file types."""
    NULL        = "{http://www.w3.org/2001/XMLSchema-instance}nil"
    KVP_KEY     = "{http://schemas.datacontract.org/2004/07/System.Collections.Generic}key"
    KVP_VALUE   = "{http://schemas.datacontract.org/2004/07/System.Collections.Generic}value"
    SELECTED    = "{http://schemas.datacontract.org/2004/07/Applications.Epu.Persistence}Selected"
    ID          = "{http://schemas.datacontract.org/2004/07/Fei.Applications.Common.Types}Id"


class _Session:
    """XML paths for EpuSession.dm and its per-GridSquare .dm sidecar files."""
    NAME                = "{http://schemas.datacontract.org/2004/07/Applications.Epu.Persistence}Name"
    GRID_NAME           = "{http://schemas.datacontract.org/2004/07/Applications.Epu.Persistence}AutoloaderDescription"
    GRID_SLOT           = "{http://schemas.datacontract.org/2004/07/Applications.Epu.Persistence}AutoloaderSlot"
    IMAGE_FORMAT        = "{http://schemas.datacontract.org/2004/07/Applications.Epu.Persistence}ImageFileFormat"
    MOVIE_FORMAT        = "{http://schemas.datacontract.org/2004/07/Applications.Epu.Persistence}DoseFractionsOutputFormat"
    SAMPLE              = "{http://schemas.datacontract.org/2004/07/Applications.Epu.Persistence}Samples/{http://schemas.datacontract.org/2004/07/Applications.Epu.Persistence}_items/{http://schemas.datacontract.org/2004/07/Applications.Epu.Persistence}SampleXml"
    SAMPLE_ATLAS_ID     = "{http://schemas.datacontract.org/2004/07/Applications.Epu.Persistence}AtlasId"
    SAMPLE_OPTICS_PRESETS   = "{http://schemas.datacontract.org/2004/07/Applications.Epu.Persistence}MicroscopeSettings/KeyValuePairs/{http://schemas.datacontract.org/2004/07/System.Collections.Generic}KeyValuePairOfExperimentSettingsIdMicroscopeSettingsCG2rZ1D8"
    SAMPLE_CAMERA_SETTINGS  = "{http://schemas.datacontract.org/2004/07/Fei.Applications.Common.Services}Acquisition/{http://schemas.datacontract.org/2004/07/Fei.SharedObjects}camera/{http://schemas.datacontract.org/2004/07/Fei.SharedObjects}CameraSpecificInput/KeyValuePairs/{http://schemas.datacontract.org/2004/07/System.Collections.Generic}KeyValuePairOfstringanyType"
    SAMPLE_GRIDSQUARES      = "{http://schemas.datacontract.org/2004/07/Applications.Epu.Persistence}GridSquares/{http://schemas.microsoft.com/2003/10/Serialization/Arrays}m_serializationArray/{http://schemas.datacontract.org/2004/07/System.Collections.Generic}KeyValuePairOfintSerializedReferenceOfGridSquareXml_PsqDC3X0m6koiAE_P"
    GRIDSQUARE_FILENAME     = "{http://schemas.datacontract.org/2004/07/Fei.Applications.Common.Types}FileName"


class _GridSquare:
    """XML paths within per-GridSquare .dm metadata files."""
    IMAGE_PATH          = "{http://schemas.datacontract.org/2004/07/Applications.Epu.Persistence}GridSquareImagePath"
    HOLES               = "{http://schemas.datacontract.org/2004/07/Applications.Epu.Persistence}TargetLocationsEfficient/{http://schemas.microsoft.com/2003/10/Serialization/Arrays}m_serializationArray/{http://schemas.datacontract.org/2004/07/System.Collections.Generic}KeyValuePairOfintTargetLocationXmlBpEWF4JT/{http://schemas.datacontract.org/2004/07/System.Collections.Generic}value"
    HOLE_POS_PREFIX     = "{http://schemas.datacontract.org/2004/07/Applications.Epu.Persistence}PixelCenter"
    HOLE_POS_X          = "{http://schemas.datacontract.org/2004/07/System.Drawing}x"
    HOLE_POS_Y          = "{http://schemas.datacontract.org/2004/07/System.Drawing}y"
    HOLE_RADIUS         = "{http://schemas.datacontract.org/2004/07/Applications.Epu.Persistence}PixelWidthHeight/{http://schemas.datacontract.org/2004/07/System.Drawing}height"
    HOLE_FOLDER         = "{http://schemas.datacontract.org/2004/07/Applications.Epu.Persistence}ImageFolderName"
    HOLE_ACQUISITION_KVP = "{http://schemas.datacontract.org/2004/07/System.Collections.Generic}KeyValuePairOfintParticleAcquisitionDataXmlBpEWF4JT"
    IMAGE               = "{http://schemas.datacontract.org/2004/07/Applications.Epu.Persistence}Image"
    IMAGE_FILENAME      = "{http://schemas.datacontract.org/2004/07/Fei.Applications.Common.Types}BaseFileName"
    IMAGE_FORMAT        = "{http://schemas.datacontract.org/2004/07/Fei.Applications.Common.Types}FileFormat"
    GRIDSQUARE_ID       = "{http://schemas.datacontract.org/2004/07/Applications.Epu.Persistence}GridSquareId"


class _Atlas:
    """XML paths within Atlas.dm files."""
    STORAGE         = "{http://schemas.datacontract.org/2004/07/Applications.SciencesAppsShared.GridAtlas.Persistence}StorageFolder"
    IMAGE_REF       = "{http://schemas.datacontract.org/2004/07/Applications.SciencesAppsShared.GridAtlas.Persistence}Atlas/{http://schemas.datacontract.org/2004/07/Applications.SciencesAppsShared.GridAtlas.Persistence}AtlasImageReference"
    SQUARE_SEARCH   = ".//{http://schemas.datacontract.org/2004/07/System.Collections.Generic}KeyValuePairOfintNodeXml30oatNZW/{http://schemas.datacontract.org/2004/07/System.Collections.Generic}value"
    SQUARE_POS      = "{http://schemas.datacontract.org/2004/07/Applications.SciencesAppsShared.GridAtlas.Persistence}PositionOnTheAtlas"
    SQUARE_X        = "{http://schemas.datacontract.org/2004/07/Applications.SciencesAppsShared.GridAtlas.Datamodel}Center/{http://schemas.datacontract.org/2004/07/System.Drawing}x"
    SQUARE_Y        = "{http://schemas.datacontract.org/2004/07/Applications.SciencesAppsShared.GridAtlas.Datamodel}Center/{http://schemas.datacontract.org/2004/07/System.Drawing}y"
    SQUARE_HEIGHT   = "{http://schemas.datacontract.org/2004/07/Applications.SciencesAppsShared.GridAtlas.Datamodel}Size/{http://schemas.datacontract.org/2004/07/System.Drawing}height"
    SQUARE_WIDTH    = "{http://schemas.datacontract.org/2004/07/Applications.SciencesAppsShared.GridAtlas.Datamodel}Size/{http://schemas.datacontract.org/2004/07/System.Drawing}width"
    SQUARE_ROTATION = "{http://schemas.datacontract.org/2004/07/Applications.SciencesAppsShared.GridAtlas.Datamodel}Rotation"
    SQUARE_CATEGORY = "{http://schemas.datacontract.org/2004/07/Applications.SciencesAppsShared.GridAtlas.Persistence}Category"

class _ImageMeta:
    """XML path within EPU image metadata files"""
    PIXEL_SIZE = "./{http://schemas.datacontract.org/2004/07/Fei.SharedObjects}SpatialScale/{http://schemas.datacontract.org/2004/07/Fei.SharedObjects}pixelSize/{http://schemas.datacontract.org/2004/07/Fei.SharedObjects}x/{http://schemas.datacontract.org/2004/07/Fei.SharedObjects}numericValue"


PATH_MAP = {}  # populated at runtime from EPU_PATH_MAP env var (or set directly for testing)

ATLAS_CATEGORY_COLOR_MAP = {0: (0, 221, 238),    # cyan
                            1: (137, 109, 251),  # purple
                            2: (210, 15, 127),   # magenta
                            3: (255,138, 41),    # orange
                            4: (244, 237, 57)}   # yellow

ATLAS_SQUARE_DRAWING_SIZE_FUDGE = 1.2
GRIDSQUARE_HOLE_DRAWING_SIZE_FUDGE = 1.4


class ImageFormat(Enum):
    TIFF = "tiff"
    MRC = "mrc"


@dataclass
class EpuImage:
    image_path: str
    metadata_path: str
    pixel_size: float
    format: ImageFormat


@dataclass
class EpuDataSession:
    session_dir: str
    session_file: str  # should be session_dir/EpuSession.dm
    atlas_file: str
    autoloader_slot: int
    session_name: str
    grid_name: str
    gain_corrected: bool
    movie_format: ImageFormat
    image_format: ImageFormat
    selected_gridsquares: set
    gridsquares: dict  # dict of id_str => EpuGridSquare
    # ! Below this line requires atlas metadata
    atlas_image: EpuImage


@dataclass
class EpuGridsquare:
    id_str: str
    image: EpuImage
    holes: dict  # dict of id_str => EpuHole
    # ! Below this line requires atlas metadata
    x_pos: float
    y_pos: float
    height: float
    width: float
    radius: float
    rotation: float
    category: int
    vertices: list


@dataclass
class EpuHole:
    id_str: str
    image: EpuImage
    x_pos: float
    y_pos: float
    radius: float
    acquisitions: list


def windows_to_posix_path(path):
    return PureWindowsPath(path).as_posix()


def map_path(path, path_map=None):
    """
    Remap the start of a path stored in EPU metadata (i.e., a Windows path) to a local path.

    Parameters
    ----------
    path : str
        The path to remap, normally already converted with `windows_to_posix_path`.
    path_map : dict of str to str, optional
        Maps the beginning of a Windows path (the key) to the local path that replaces it (the value). Defaults to the
        module-level `PATH_MAP`.

    Returns
    -------
    str
        `path` with the best-matching key replaced by its value, or `path` unchanged if no key matches.

    Notes
    -----
    A key matches only at the start of `path`, on whole path components (so ``D:/ATLAS`` does not match
    ``D:/ATLASES/...``), and case-insensitively on every OS (the metadata paths were written on Windows, where
    ``D:\\ATLASES`` and ``d:\\atlases`` are the same). If several keys match, the longest one wins, and only one
    replacement is made (replaced text is never re-matched). Separators on keys are normalized with
    `windows_to_posix_path`, and trailing separators on keys and values are ignored.
    """
    if path_map is None:
        path_map = PATH_MAP
    best = None  # (length of matched prefix, replacement)
    for find, replace in path_map.items():
        if not find.strip():
            continue
        find = windows_to_posix_path(find).rstrip("/")
        match = re.match(re.escape(find), path, flags=re.IGNORECASE)
        if match is None:
            continue
        end = match.end()
        if end < len(path) and path[end] not in "/\\":
            continue  # matched only part of a path component
        if best is None or end > best[0]:
            best = (end, replace.rstrip("/\\"))
    if best is None:
        return path
    end, replace = best
    return replace + path[end:]


def find_epuxml_kvp_value_node(kvp_nodes, search_key):
    for node in kvp_nodes:
        if node.findtext(f"./{_EPU.KVP_KEY}") == search_key:
            return node.find(f"./{_EPU.KVP_VALUE}")
    return None


def epuxml_node_is_nil(node):
    return node.attrib.get(_EPU.NULL, "false") == "true"


def parse_image_node(root, sub_folder):
    image_filename_node = root.find(f"./{_GridSquare.IMAGE}")
    if epuxml_node_is_nil(image_filename_node):
        return None
    image_file_ext = image_filename_node.findtext(f".//{_GridSquare.IMAGE_FORMAT}").lower() # "mrc" or "tiff"
    image_file_name = image_filename_node.findtext(f".//{_GridSquare.IMAGE_FILENAME}")
    images_folder = root.findtext(f"./{_GridSquare.HOLE_FOLDER}")  # almost always "Images-Disc1"
    # Actual file paths are images_folder/type_folder/base_file_name with image_file_ext and .xml
    image_path    = os.path.join(images_folder, sub_folder, f"{image_file_name}.{image_file_ext}")
    metadata_path = os.path.join(images_folder, sub_folder, f"{image_file_name}.xml")

    # can't read pixel size because the metadata does not tell us the epu session directory path
    # caller needs to fill in pixel_size later by parsing `metadata_path` xml
    return EpuImage(image_path=image_path,
                    metadata_path=metadata_path,
                    pixel_size=0.00,
                    format=ImageFormat(image_file_ext))


def populate_epuimage(image: EpuImage):
    xml_root = ET.parse(image.metadata_path).getroot()
    pixel_size = float(xml_root.findtext(_ImageMeta.PIXEL_SIZE)) * 1e10 # convert to angstroms from meters

    image.pixel_size = pixel_size


def parse_image_node_to_filename(root):
    base_file_name = root.findtext(f".//{_GridSquare.IMAGE_FILENAME}")
    image_format = root.findtext(f".//{_GridSquare.IMAGE_FORMAT}").lower()
    return f"{base_file_name}.{image_format}"


def parse_hole_from_gridsquare_meta_node(node):
    gridsquare_id_str = node.findtext(f"./{_GridSquare.GRIDSQUARE_ID}")
    hole_id_str = node.findtext(f"./{_EPU.ID}")

    x_pos = float(node.findtext(f"./{_GridSquare.HOLE_POS_PREFIX}/{_GridSquare.HOLE_POS_X}"))
    y_pos = float(node.findtext(f"./{_GridSquare.HOLE_POS_PREFIX}/{_GridSquare.HOLE_POS_Y}"))
    radius = float(node.findtext(f"./{_GridSquare.HOLE_RADIUS}")) / 2

    image = parse_image_node(node, sub_folder=os.path.join(f"GridSquare_{gridsquare_id_str}", "FoilHoles"))

    acquisition_nodes = node.findall(f".//{_GridSquare.HOLE_ACQUISITION_KVP}/{_EPU.KVP_VALUE}")
    acquisitions = [parse_image_node(x, sub_folder=os.path.join(f"GridSquare_{gridsquare_id_str}",
                                                                "Data"))
                    for x in acquisition_nodes]

    return EpuHole(id_str=hole_id_str, image=image, x_pos=x_pos, y_pos=y_pos, radius=radius,
                   acquisitions=acquisitions)


def parse_session_gridsquare_meta(xml_root):
    id_str = xml_root.findtext(f"./{_EPU.ID}")
    image = parse_image_node(xml_root, sub_folder=f"GridSquare_{id_str}")

    holes_xml_nodes = xml_root.findall(f".//{_GridSquare.HOLES}")
    selected_hole_xml_nodes = [x for x in holes_xml_nodes if x.findtext(f"./{_EPU.SELECTED}") == 'true']

    holes = {x.findtext(f"./{_EPU.ID}"): parse_hole_from_gridsquare_meta_node(x)
             for x in selected_hole_xml_nodes}

    # Use empty/null/0 values for properties that should be parsed from the atlas metadata
    return EpuGridsquare(id_str=id_str, image=image, holes=holes,
                         x_pos=0.0, y_pos=0.0, height=0.0, width=0.0, radius=0.0, rotation=0.0,
                         category=-1, vertices=[])


def parse_epu_session(epu_meta_dir):
    epu_meta_path = os.path.join(epu_meta_dir, "EpuSession.dm")

    xml_tree = ET.parse(epu_meta_path)
    xml_root = xml_tree.getroot()

    session_name = xml_root.findtext(f"./{_Session.NAME}")
    grid_name = xml_root.findtext(f"./{_Session.GRID_NAME}")
    grid_slot = int(xml_root.findtext(f"./{_Session.GRID_SLOT}"))

    sample_node = xml_root.find(f"./{_Session.SAMPLE}")

    atlas_file = map_path(windows_to_posix_path(sample_node.findtext(f"./{_Session.SAMPLE_ATLAS_ID}")))

    has_movies = False
    epu_optics_preset_nodes = sample_node.findall(f"./{_Session.SAMPLE_OPTICS_PRESETS}")
    data_acq_preset_node = find_epuxml_kvp_value_node(epu_optics_preset_nodes, "Acquisition")
    camera_settings_nodes = data_acq_preset_node.findall(f"{_Session.SAMPLE_CAMERA_SETTINGS}")
    fractionation_settings_node = find_epuxml_kvp_value_node(camera_settings_nodes, "FractionationSettings")
    if fractionation_settings_node.attrib.get(_EPU.NULL, "false") != "true":
        has_movies = True

    image_format = ImageFormat[xml_root.findtext(f"./{_Session.IMAGE_FORMAT}").upper()]
    movie_format_str = xml_root.findtext(f"./{_Session.MOVIE_FORMAT}")
    movie_format = None
    gain_corrected = True
    if has_movies:
        movie_format = ImageFormat.TIFF if "tif" in movie_format_str else ImageFormat.MRC
        gain_corrected = "Non-Gain" not in movie_format_str

    gridsquare_nodes = sample_node.findall(f"./{_Session.SAMPLE_GRIDSQUARES}")
    selected_gridsquares = {}
    for gridsquare_node in gridsquare_nodes:
        gs_meta_path = gridsquare_node.findtext(f"./{_EPU.KVP_VALUE}/{_Session.GRIDSQUARE_FILENAME}")
        gs_meta_path = os.path.join(epu_meta_dir,
                                    windows_to_posix_path(gs_meta_path))
        gs_xml_root = ET.parse(gs_meta_path).getroot()

        selected_str = gs_xml_root.findtext(f"./{_EPU.SELECTED}")
        selected = (selected_str == "true")
        if not selected:
            continue

        gridsquare = parse_session_gridsquare_meta(gs_xml_root)
        # A gridsquare can be selected without ever having been imaged (e.g. the session was ended before EPU got to
        # it). In some cases, such gridsquares even have, unintuitively, `<State>Completed</State>` in their XML.
        # Without a gridsquare image, EPU can't have navigated to holes for any more imaging, so discard the square
        if gridsquare.image is None:
            continue
        selected_gridsquares[gridsquare.id_str] = gridsquare

        # add `epu_meta_dir` to the front of all parsed paths
        # which then allows us t populate EpuImage fields
        gridsquare.image.image_path = os.path.join(epu_meta_dir, gridsquare.image.image_path)
        gridsquare.image.metadata_path = os.path.join(epu_meta_dir, gridsquare.image.metadata_path)
        populate_epuimage(gridsquare.image)
        for hole in gridsquare.holes.values():
            if hole.image is not None:
                hole.image.image_path = os.path.join(epu_meta_dir, hole.image.image_path)
                hole.image.metadata_path = os.path.join(epu_meta_dir, hole.image.metadata_path)
                populate_epuimage(hole.image)
            for data in hole.acquisitions:
                data.image_path = os.path.join(epu_meta_dir, data.image_path)
                data.metadata_path = os.path.join(epu_meta_dir, data.metadata_path)
                populate_epuimage(data)

    return EpuDataSession(session_dir=epu_meta_dir,
                          session_file=epu_meta_path,
                          atlas_file=atlas_file,
                          autoloader_slot=grid_slot,
                          session_name=session_name,
                          grid_name=grid_name,
                          gain_corrected=gain_corrected,
                          movie_format=movie_format,
                          image_format=image_format,
                          selected_gridsquares=set(selected_gridsquares.keys()),
                          gridsquares=selected_gridsquares,
                          atlas_image=None)


def get_atlas_image_path(atlas_xml_root):
    folder = map_path(windows_to_posix_path(atlas_xml_root.findtext(f"./{_Atlas.STORAGE}")))
    filename = parse_image_node_to_filename(atlas_xml_root.find(f"./{_Atlas.IMAGE_REF}"))
    # The actual mrc/tiff file for the atlas is at `folder`/Atlas/`filename`
    return os.path.join(folder, "Atlas", filename)


def parse_gridsquare_data_from_atlas(atlas_xml_root):
    gridsquare_xml_nodes = atlas_xml_root.findall(_Atlas.SQUARE_SEARCH)
    gridsquare_data = [(x.findtext(f"./{_EPU.ID}").strip(),
                        float(x.findtext(f"./{_Atlas.SQUARE_POS}/{_Atlas.SQUARE_X}")),
                        float(x.findtext(f"./{_Atlas.SQUARE_POS}/{_Atlas.SQUARE_Y}")),
                        float(x.findtext(f"./{_Atlas.SQUARE_POS}/{_Atlas.SQUARE_HEIGHT}")),
                        float(x.findtext(f"./{_Atlas.SQUARE_POS}/{_Atlas.SQUARE_WIDTH}")),
                        float(x.findtext(f"./{_Atlas.SQUARE_POS}/{_Atlas.SQUARE_ROTATION}")),
                        int(x.findtext(f"./{_Atlas.SQUARE_CATEGORY}"))
                        ) for x in gridsquare_xml_nodes if x.findtext(f"./{_Atlas.SQUARE_CATEGORY}") != '']
    columns = ["id", "x", "y", "height", "width", "rotation", "category"]
    gridsquares = pd.DataFrame.from_records(data=gridsquare_data, columns=columns, index="id")

    # Compute vertices of all squares
    gridsquares["radius"] = np.sqrt((gridsquares["width"] / 2) ** 2 + (gridsquares["height"] / 2) ** 2)
    vertices_matrix = np.array([[0.5, 0.5], [0.5, -0.5], [-0.5, -0.5], [-0.5, 0.5]])
    corners = gridsquares[["width", "height"]].values[:, np.newaxis] * vertices_matrix
    angles = np.arctan2(corners[:, :, 1], corners[:, :, 0]) + gridsquares["rotation"].values[:, np.newaxis]
    r = gridsquares["radius"].values[:, np.newaxis] * ATLAS_SQUARE_DRAWING_SIZE_FUDGE
    rotated_vertices = np.stack((np.cos(angles) * r, np.sin(angles) * r), axis=-1)
    rotated_vertices[:, :, 0] += gridsquares["x"].values[:, np.newaxis]
    rotated_vertices[:, :, 1] += gridsquares["y"].values[:, np.newaxis]
    gridsquares["vertices"] = rotated_vertices.tolist()

    return gridsquares


def populate_session_with_atlas_squares(epu_session, atlas_xml_root):
    atlas_squares = parse_gridsquare_data_from_atlas(atlas_xml_root)
    for id, square in atlas_squares.iterrows():
        if id in epu_session.gridsquares:
            this_square = epu_session.gridsquares[id]
            this_square.x_pos = square["x"]
            this_square.y_pos = square["y"]
            this_square.radius = square["radius"]
            this_square.height = square["height"]
            this_square.width = square["width"]
            this_square.rotation = square["rotation"]
            this_square.category = square["category"]
            this_square.vertices = square["vertices"]
        else:
            epu_session.gridsquares[id] = EpuGridsquare(id_str=id,
                                                        image=None,
                                                        holes={},
                                                        x_pos=square["x"],
                                                        y_pos=square["y"],
                                                        height=square["height"],
                                                        width=square["width"],
                                                        radius=square["radius"],
                                                        rotation=square["rotation"],
                                                        category=square["category"],
                                                        vertices=square["vertices"])


def populate_session_with_atlas(epu_session):
    atlas_xml_root = ET.parse(epu_session.atlas_file).getroot()
    populate_session_with_atlas_squares(epu_session, atlas_xml_root)
    atlas_dir = os.path.dirname(epu_session.atlas_file)
    image_ref_node = atlas_xml_root.find(f"./{_Atlas.IMAGE_REF}")
    base_name = image_ref_node.findtext(f".//{_GridSquare.IMAGE_FILENAME}")
    fmt = image_ref_node.findtext(f".//{_GridSquare.IMAGE_FORMAT}").lower()
    atlas_image = EpuImage(image_path=os.path.join(atlas_dir, f"{base_name}.{fmt}"),
                           metadata_path=os.path.join(atlas_dir, f"{base_name}.xml"),
                           pixel_size=0.0,
                           format=ImageFormat(fmt))
    populate_epuimage(atlas_image)
    epu_session.atlas_image = atlas_image


def parse_atlas_only_session(atlas_xml_root):
    atlas_squares = parse_gridsquare_data_from_atlas(atlas_xml_root)
    gridsquares = {id: EpuGridsquare(id_str=id,
                                     image=None,
                                     holes={},
                                     x_pos=square["x"],
                                     y_pos=square["y"],
                                     height=square["height"],
                                     width=square["width"],
                                     radius=square["radius"],
                                     rotation=square["rotation"],
                                     category=square["category"],
                                     vertices=square["vertices"])
                   for id, square in atlas_squares.iterrows()}
    atlas_image_path = get_atlas_image_path(atlas_xml_root)
    atlas_metadata_path = os.path.splitext(atlas_image_path)[0] + ".xml"
    fmt = os.path.splitext(atlas_image_path)[1].lstrip(".")
    atlas_image = EpuImage(image_path=atlas_image_path,
                           metadata_path=atlas_metadata_path,
                           pixel_size=0.0,
                           format=ImageFormat(fmt))
    populate_epuimage(atlas_image)
    atlas_file = map_path(windows_to_posix_path(os.path.join(atlas_xml_root.findtext(f"./{_Atlas.STORAGE}"),
                                                             "Atlas", "Atlas.dm")))
    return EpuDataSession(session_dir="",
                          session_file="",
                          atlas_file=atlas_file,
                          autoloader_slot=-1,
                          session_name="",
                          grid_name="",
                          gain_corrected=True,
                          movie_format=ImageFormat.MRC,
                          image_format=ImageFormat.MRC,
                          selected_gridsquares=set(),
                          gridsquares=gridsquares,
                          atlas_image=atlas_image)
