import xml.etree.ElementTree as ET
import pandas as pd
import numpy as np
import os.path
from pathlib import PureWindowsPath
from enum import Enum, auto
from dataclasses import dataclass


EPU_XML_NULL_KEY = "{http://www.w3.org/2001/XMLSchema-instance}nil"
EPU_XML_KEYVALUEPAIR_KEY = "{http://schemas.datacontract.org/2004/07/System.Collections.Generic}key"
EPU_XML_KEYVALUEPAIR_VALUE = "{http://schemas.datacontract.org/2004/07/System.Collections.Generic}value"
EPU_XML_SELECTED_KEY = "{http://schemas.datacontract.org/2004/07/Applications.Epu.Persistence}Selected"
EPU_XML_ID_KEY = "{http://schemas.datacontract.org/2004/07/Fei.Applications.Common.Types}Id"

EPU_SESSION_NAME_KEY = "{http://schemas.datacontract.org/2004/07/Applications.Epu.Persistence}Name"
EPU_GRID_NAME_KEY = "{http://schemas.datacontract.org/2004/07/Applications.Epu.Persistence}AutoloaderDescription"
EPU_GRID_SLOT_KEY = "{http://schemas.datacontract.org/2004/07/Applications.Epu.Persistence}AutoloaderSlot"
EPU_IMAGE_FORMAT_KEY = "{http://schemas.datacontract.org/2004/07/Applications.Epu.Persistence}ImageFileFormat"
EPU_MOVIE_FORMAT_KEY = "{http://schemas.datacontract.org/2004/07/Applications.Epu.Persistence}DoseFractionsOutputFormat"
EPU_SAMPLE_PREFIX = "{http://schemas.datacontract.org/2004/07/Applications.Epu.Persistence}Samples/{http://schemas.datacontract.org/2004/07/Applications.Epu.Persistence}_items/{http://schemas.datacontract.org/2004/07/Applications.Epu.Persistence}SampleXml"
EPU_SAMPLE_ATLAS_KEY = "{http://schemas.datacontract.org/2004/07/Applications.Epu.Persistence}AtlasId"
EPU_SAMPLE_OPTICS_PRESETS = "{http://schemas.datacontract.org/2004/07/Applications.Epu.Persistence}MicroscopeSettings/KeyValuePairs/{http://schemas.datacontract.org/2004/07/System.Collections.Generic}KeyValuePairOfExperimentSettingsIdMicroscopeSettingsCG2rZ1D8"
EPU_SAMPLE_OPTICS_PRESET_CAMERA_SETTINGS = "{http://schemas.datacontract.org/2004/07/Fei.Applications.Common.Services}Acquisition/{http://schemas.datacontract.org/2004/07/Fei.SharedObjects}camera/{http://schemas.datacontract.org/2004/07/Fei.SharedObjects}CameraSpecificInput/KeyValuePairs/{http://schemas.datacontract.org/2004/07/System.Collections.Generic}KeyValuePairOfstringanyType"
EPU_SAMPLE_GRIDSQUARES = "{http://schemas.datacontract.org/2004/07/Applications.Epu.Persistence}GridSquares/{http://schemas.microsoft.com/2003/10/Serialization/Arrays}m_serializationArray/{http://schemas.datacontract.org/2004/07/System.Collections.Generic}KeyValuePairOfintSerializedReferenceOfGridSquareXml_PsqDC3X0m6koiAE_P"
EPU_SAMPLE_GRIDSQUARE_FILENAME_KEY = "{http://schemas.datacontract.org/2004/07/Fei.Applications.Common.Types}FileName"

GRIDSQUARE_IMAGE_PATH_KEY = "{http://schemas.datacontract.org/2004/07/Applications.Epu.Persistence}GridSquareImagePath"

GRIDSQUARE_HOLES_SEARCH = "{http://schemas.datacontract.org/2004/07/Applications.Epu.Persistence}TargetLocationsEfficient/{http://schemas.microsoft.com/2003/10/Serialization/Arrays}m_serializationArray/{http://schemas.datacontract.org/2004/07/System.Collections.Generic}KeyValuePairOfintTargetLocationXmlBpEWF4JT/{http://schemas.datacontract.org/2004/07/System.Collections.Generic}value"
GRIDSQUARE_HOLES_POS_PREFIX = "{http://schemas.datacontract.org/2004/07/Applications.Epu.Persistence}PixelCenter"
GRIDSQUARE_HOLES_POS_X = "{http://schemas.datacontract.org/2004/07/System.Drawing}x"
GRIDSQUARE_HOLES_POS_Y = "{http://schemas.datacontract.org/2004/07/System.Drawing}y"
GRIDSQAURE_HOLES_RADIUS = "{http://schemas.datacontract.org/2004/07/Applications.Epu.Persistence}PixelWidthHeight/{http://schemas.datacontract.org/2004/07/System.Drawing}height"
GRIDSQUARE_HOLES_FOLDER = "{http://schemas.datacontract.org/2004/07/Applications.Epu.Persistence}ImageFolderName"

HOLE_ACQUISITION_KVP = "{http://schemas.datacontract.org/2004/07/System.Collections.Generic}KeyValuePairOfintParticleAcquisitionDataXmlBpEWF4JT"

IMAGE_KEY = "{http://schemas.datacontract.org/2004/07/Applications.Epu.Persistence}Image"
IMAGE_FILENAME_KEY = "{http://schemas.datacontract.org/2004/07/Fei.Applications.Common.Types}BaseFileName"
IMAGE_FORMAT_KEY = "{http://schemas.datacontract.org/2004/07/Fei.Applications.Common.Types}FileFormat"
IMAGE_GRIDSQUARE_ID_KEY = "{http://schemas.datacontract.org/2004/07/Applications.Epu.Persistence}GridSquareId"

ATLAS_SAMPLE_AQC_STATUS = "{http://schemas.datacontract.org/2004/07/Applications.SciencesAppsShared.GridAtlas.Persistence.Screening}AtlasAcquisitionStatus"
ATLAS_SAMPLE_WRITTEN = "{http://schemas.datacontract.org/2004/07/Applications.SciencesAppsShared.GridAtlas.Persistence.Screening}AcquiredAtlasAvailable"

ATLAS_STORAGE_KEY = "{http://schemas.datacontract.org/2004/07/Applications.SciencesAppsShared.GridAtlas.Persistence}StorageFolder"
ATLAS_IMAGE_KEY = "{http://schemas.datacontract.org/2004/07/Applications.SciencesAppsShared.GridAtlas.Persistence}Atlas/{http://schemas.datacontract.org/2004/07/Applications.SciencesAppsShared.GridAtlas.Persistence}AtlasImageReference"

ATLAS_SQUARE_XML_SEARCH = ".//{http://schemas.datacontract.org/2004/07/System.Collections.Generic}KeyValuePairOfintNodeXml30oatNZW/{http://schemas.datacontract.org/2004/07/System.Collections.Generic}value"
ATLAS_SQUARE_POS_PREFIX = "{http://schemas.datacontract.org/2004/07/Applications.SciencesAppsShared.GridAtlas.Persistence}PositionOnTheAtlas"
ATLAS_SQUARE_XPOS_PATH = "{http://schemas.datacontract.org/2004/07/Applications.SciencesAppsShared.GridAtlas.Datamodel}Center/{http://schemas.datacontract.org/2004/07/System.Drawing}x"
ATLAS_SQUARE_YPOS_PATH = "{http://schemas.datacontract.org/2004/07/Applications.SciencesAppsShared.GridAtlas.Datamodel}Center/{http://schemas.datacontract.org/2004/07/System.Drawing}y"
ATLAS_SQUARE_HEIGHT_PATH = "{http://schemas.datacontract.org/2004/07/Applications.SciencesAppsShared.GridAtlas.Datamodel}Size/{http://schemas.datacontract.org/2004/07/System.Drawing}height"
ATLAS_SQUARE_WIDTH_PATH = "{http://schemas.datacontract.org/2004/07/Applications.SciencesAppsShared.GridAtlas.Datamodel}Size/{http://schemas.datacontract.org/2004/07/System.Drawing}width"
ATLAS_SQUARE_ROT_PATH = "{http://schemas.datacontract.org/2004/07/Applications.SciencesAppsShared.GridAtlas.Datamodel}Rotation"
ATLAS_SQUARE_CATEGORY_PATH = "{http://schemas.datacontract.org/2004/07/Applications.SciencesAppsShared.GridAtlas.Persistence}Category"

PATH_MAP = {}  # populated at runtime from EPU_PATH_MAP env var (or set directly for testing)

ATLAS_CATEGORY_COLOR_MAP = {0: (0, 221, 238),    # cyan
                            1: (137, 109, 251),  # purple
                            2: (210, 15, 127),   # magenta
                            3: (255,138, 41),    # orange
                            4: (244, 237, 57)}   # yellow

ATLAS_SQUARE_DRAWING_SIZE_FUDGE = 1.2
GRIDSQUARE_HOLE_DRAWING_SIZE_FUDGE = 1.4


class ImageFormat(Enum):
    TIFF = auto()
    MRC = auto()
    UNKNOWN = auto()


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
    atlas_image_path: str


@dataclass
class EpuGridsquare:
    id_str: str
    image_path: str
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
    image_path: str
    x_pos: float
    y_pos: float
    radius: float
    acquisitions: list


def windows_to_posix_path(path):
    return PureWindowsPath(path).as_posix()


def map_path(path, path_map=None):
    global PATH_MAP
    if path_map is None:
        path_map = PATH_MAP
    for find, replace in path_map.items():
        path = path.replace(find, replace)
    return path


def find_epuxml_kvp_value_node(kvp_nodes, search_key):
    for node in kvp_nodes:
        if node.findtext(f"./{EPU_XML_KEYVALUEPAIR_KEY}") == search_key:
            return node.find(f"./{EPU_XML_KEYVALUEPAIR_VALUE}")
    return None


def epuxml_node_is_nil(node):
    return node.attrib.get(EPU_XML_NULL_KEY, "false") == "true"


def parse_image_node_to_filename(root):
    base_file_name = root.findtext(f".//{IMAGE_FILENAME_KEY}")
    image_format = root.findtext(f".//{IMAGE_FORMAT_KEY}").lower()
    return f"{base_file_name}.{image_format}"


def parse_hole_from_gridsquare_meta_node(node):
    gridsquare_id_str = node.findtext(f"./{IMAGE_GRIDSQUARE_ID_KEY}")
    hole_id_str = node.findtext(f"./{EPU_XML_ID_KEY}")

    x_pos = float(node.findtext(f"./{GRIDSQUARE_HOLES_POS_PREFIX}/{GRIDSQUARE_HOLES_POS_X}"))
    y_pos = float(node.findtext(f"./{GRIDSQUARE_HOLES_POS_PREFIX}/{GRIDSQUARE_HOLES_POS_Y}"))
    radius = float(node.findtext(f"./{GRIDSQAURE_HOLES_RADIUS}")) / 2

    image_path = None
    if not epuxml_node_is_nil(node.find(f"./{IMAGE_KEY}")):
        folder = map_path(windows_to_posix_path(node.findtext(f"./{GRIDSQUARE_HOLES_FOLDER}")))
        image_path = os.path.join(folder,
                                  f"GridSquare_{gridsquare_id_str}",
                                  "FoilHoles",
                                  parse_image_node_to_filename(node.find(f"./{IMAGE_KEY}")))

    acquisition_nodes = node.findall(f".//{HOLE_ACQUISITION_KVP}/{EPU_XML_KEYVALUEPAIR_VALUE}")
    acquisitions = [os.path.join(map_path(windows_to_posix_path(x.findtext(f"./{GRIDSQUARE_HOLES_FOLDER}"))),
                                 f"GridSquare_{gridsquare_id_str}",
                                 "Data",
                                 parse_image_node_to_filename(x.find(f"./{IMAGE_KEY}")))
                    for x in acquisition_nodes]

    return EpuHole(id_str=hole_id_str, image_path=image_path, x_pos=x_pos, y_pos=y_pos, radius=radius,
                   acquisitions=acquisitions)


def parse_session_gridsquare_meta(xml_root):
    id_str = xml_root.findtext(f"./{EPU_XML_ID_KEY}")
    image_path = map_path(windows_to_posix_path(xml_root.findtext(f"./{GRIDSQUARE_IMAGE_PATH_KEY}")))

    holes_xml_nodes = xml_root.findall(f".//{GRIDSQUARE_HOLES_SEARCH}")
    selected_hole_xml_nodes = [x for x in holes_xml_nodes if x.findtext(f"./{EPU_XML_SELECTED_KEY}") == 'true']

    holes = {x.findtext(f"./{EPU_XML_ID_KEY}"): parse_hole_from_gridsquare_meta_node(x)
             for x in selected_hole_xml_nodes}

    # Use empty/null/0 values for properties that should be parsed from the atlas metadata
    return EpuGridsquare(id_str=id_str, image_path=image_path, holes=holes,
                         x_pos=0.0, y_pos=0.0, height=0.0, width=0.0, radius=0.0, rotation=0.0,
                         category=-1, vertices=[])


def parse_epu_session(epu_meta_dir):
    epu_meta_path = os.path.join(epu_meta_dir, "EpuSession.dm")

    xml_tree = ET.parse(epu_meta_path)
    xml_root = xml_tree.getroot()

    session_name = xml_root.findtext(f"./{EPU_SESSION_NAME_KEY}")
    grid_name = xml_root.findtext(f"./{EPU_GRID_NAME_KEY}")
    grid_slot = int(xml_root.findtext(f"./{EPU_GRID_SLOT_KEY}"))

    sample_node = xml_root.find(f"./{EPU_SAMPLE_PREFIX}")

    atlas_file = map_path(windows_to_posix_path(sample_node.findtext(f"./{EPU_SAMPLE_ATLAS_KEY}")))

    has_movies = False
    epu_optics_preset_nodes = sample_node.findall(f"./{EPU_SAMPLE_OPTICS_PRESETS}")
    data_acq_preset_node = find_epuxml_kvp_value_node(epu_optics_preset_nodes, "Acquisition")
    camera_settings_nodes = data_acq_preset_node.findall(f"{EPU_SAMPLE_OPTICS_PRESET_CAMERA_SETTINGS}")
    fractionation_settings_node = find_epuxml_kvp_value_node(camera_settings_nodes, "FractionationSettings")
    if fractionation_settings_node.attrib.get(EPU_XML_NULL_KEY, "false") != "true":
        has_movies = True

    image_format = ImageFormat[xml_root.findtext(f"./{EPU_IMAGE_FORMAT_KEY}").upper()]
    movie_format_str = xml_root.findtext(f"./{EPU_MOVIE_FORMAT_KEY}")
    movie_format = None
    gain_corrected = True
    if has_movies:
        movie_format = ImageFormat.TIFF if "tif" in movie_format_str else ImageFormat.MRC
        gain_corrected = "Non-Gain" not in movie_format_str

    gridsquare_nodes = sample_node.findall(f"./{EPU_SAMPLE_GRIDSQUARES}")
    selected_gridsquares = {}
    for gridsquare_node in gridsquare_nodes:
        gs_meta_path = gridsquare_node.findtext(f"./{EPU_XML_KEYVALUEPAIR_VALUE}/{EPU_SAMPLE_GRIDSQUARE_FILENAME_KEY}")
        gs_meta_path = os.path.join(os.path.split(epu_meta_path)[0],
                                    windows_to_posix_path(gs_meta_path))
        gs_xml_root = ET.parse(gs_meta_path).getroot()

        selected_str = gs_xml_root.findtext(f"./{EPU_XML_SELECTED_KEY}")
        selected = (selected_str == "true")
        if not selected:
            continue

        gridsquare = parse_session_gridsquare_meta(gs_xml_root)
        selected_gridsquares[gridsquare.id_str] = gridsquare

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
                          atlas_image_path="")


def get_atlas_image_path(atlas_xml_root):
    folder = map_path(windows_to_posix_path(atlas_xml_root.findtext(f"./{ATLAS_STORAGE_KEY}")))
    filename = parse_image_node_to_filename(atlas_xml_root.find(f"./{ATLAS_IMAGE_KEY}"))
    # The actual mrc/tiff file for the atlas is at `folder`/Atlas/`filename`
    return os.path.join(folder, "Atlas", filename)


def parse_gridsquare_data_from_atlas(atlas_xml_root):
    gridsquare_xml_nodes = atlas_xml_root.findall(ATLAS_SQUARE_XML_SEARCH)
    gridsquare_data = [(x.findtext(f"./{EPU_XML_ID_KEY}").strip(),
                        float(x.findtext(f"./{ATLAS_SQUARE_POS_PREFIX}/{ATLAS_SQUARE_XPOS_PATH}")),
                        float(x.findtext(f"./{ATLAS_SQUARE_POS_PREFIX}/{ATLAS_SQUARE_YPOS_PATH}")),
                        float(x.findtext(f"./{ATLAS_SQUARE_POS_PREFIX}/{ATLAS_SQUARE_HEIGHT_PATH}")),
                        float(x.findtext(f"./{ATLAS_SQUARE_POS_PREFIX}/{ATLAS_SQUARE_WIDTH_PATH}")),
                        float(x.findtext(f"./{ATLAS_SQUARE_POS_PREFIX}/{ATLAS_SQUARE_ROT_PATH}")),
                        int(x.findtext(f"./{ATLAS_SQUARE_CATEGORY_PATH}"))
                        ) for x in gridsquare_xml_nodes if x.findtext(f"./{ATLAS_SQUARE_CATEGORY_PATH}") != '']
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
                                                        image_path="",
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
    atlas_image_filename = parse_image_node_to_filename(atlas_xml_root.find(f"./{ATLAS_IMAGE_KEY}"))
    atlas_image_path = os.path.join(os.path.dirname(epu_session.atlas_file),
                                    atlas_image_filename)
    epu_session.atlas_image_path = atlas_image_path


def parse_atlas_only_session(atlas_xml_root):
    atlas_squares = parse_gridsquare_data_from_atlas(atlas_xml_root)
    gridsquares = {id: EpuGridsquare(id_str=id,
                                     image_path="",
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
    atlas_file = map_path(windows_to_posix_path(os.path.join(atlas_xml_root.findtext(f"./{ATLAS_STORAGE_KEY}"),
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
                          atlas_image_path=atlas_image_path)



if __name__ == '__main__':
    # For testing only — set PATH_MAP to match your local paths
    PATH_MAP = {"Y:/Fuller_J/20260604_hRTCB_screening": "/Users/jfuller/PycharmProjects/EPUScreeningCompiler/examples/glacios_falcon3/epu_session",
                "D:/ATLASES": "/Users/jfuller/PycharmProjects/EPUScreeningCompiler/examples/glacios_falcon3/atlas_session",
                "Y:/ATLASES": "/Users/James/Desktop/epu_sample_collection/krios_k3"}
    EPU_META_PATH = "/Users/jfuller/PycharmProjects/EPUScreeningCompiler/examples/glacios_falcon3/epu_session/20260604_hRTCB_FOM_2/"
    #EPU_META_PATH = "/Users/James/Desktop/epu_sample_collection/krios_k3/Supervisor_20220624_095627/EpuSession.dm"
    OUTPUT_PATH = "/Users/jfuller/Desktop/epu_sample_collection/output_test"
    if not os.path.exists(OUTPUT_PATH):
        os.makedirs(OUTPUT_PATH, exist_ok=True)
    FONT_PATH = os.path.join(os.path.dirname(__file__), "fonts", "DejaVuSans.ttf")

    epu_session = parse_epu_session(EPU_META_PATH)
    populate_session_with_atlas_squares(epu_session, ET.parse(epu_session.atlas_file).getroot())
    print(epu_session)
    for g in epu_session.gridsquares.values():
        print(g)
        for h in g.holes.values():
            print(h)
    print("\nFound {:d} selected gridsquares "
          "with a total {:d} selected holes".format(len(epu_session.selected_gridsquares),
                                                    sum(len(x.holes) for x in epu_session.gridsquares.values())))

    print("\nFound {:d} gridsquares on the corresponding atlas".format(len(epu_session.gridsquares)))
    print(f"Stitched atlas is at {epu_session.atlas_image_path}")

    import image
    # Atlas image operations
    atlas_arr = image.image_file_to_contrasted_arr(path=epu_session.atlas_image_path,
                                                   sigma_contrast=image.DefaultSigmaContrast.ATLAS)
    atlas_img, atlas_canvas = image.arr_to_drawable_img(atlas_arr, scale=False)
    # Plain
    image.arr_to_png(atlas_arr, os.path.join(OUTPUT_PATH, "atlas.png"), scale=False)
    # Annotated
    smallest_selected_square = min(epu_session.gridsquares[x].radius for x in epu_session.selected_gridsquares)
    max_gridsquare_label_len = smallest_selected_square * 1.41 * ATLAS_SQUARE_DRAWING_SIZE_FUDGE
    gridsquare_label_font = image.maximize_font_to_fit(canvas=atlas_canvas,
                                                       font_path=FONT_PATH,
                                                       text=next(iter(epu_session.gridsquares.values())).id_str,
                                                       max_text_length=max_gridsquare_label_len,
                                                       min_font_size=10)
    #    ...with selected gridsquares
    for selected_id in epu_session.selected_gridsquares:
        square = epu_session.gridsquares[selected_id]
        image.draw_gridsquare(canvas=atlas_canvas,
                              vertices=square.vertices,
                              color=ATLAS_CATEGORY_COLOR_MAP.get(square.category, "red"),
                              label=selected_id,
                              label_font=gridsquare_label_font,
                              label_pos=(square.x_pos, square.y_pos),
                              label_textcolor="red")
    atlas_img.save(os.path.join(OUTPUT_PATH, "atlas_annotated.png"), format='png', compress_level=9)
    #    ...then the rest, onto the same canvas
    nonselected_gridsquares_ids = set(epu_session.gridsquares.keys()).difference(epu_session.selected_gridsquares)
    for nonselected_id in nonselected_gridsquares_ids:
        square = epu_session.gridsquares[nonselected_id]
        image.draw_gridsquare(canvas=atlas_canvas,
                              vertices=square.vertices,
                              color=ATLAS_CATEGORY_COLOR_MAP.get(square.category, "red"))
    atlas_img.save(os.path.join(OUTPUT_PATH, "atlas_categories.png"), format='png', compress_level=9)

    # Now iterate through for copying/converting folders and files
    for selected_id in epu_session.selected_gridsquares:
        square = epu_session.gridsquares[selected_id]
        gs_output_root = os.path.join(OUTPUT_PATH, f"GridSquare_{square.id_str}")
        acq_output_dir = os.path.join(gs_output_root, "Data")
        hole_output_dir = os.path.join(gs_output_root, "FoilHoles")
        os.makedirs(acq_output_dir, exist_ok=True)
        os.makedirs(hole_output_dir, exist_ok=True)

        gridsquare_arr = image.image_file_to_contrasted_arr(path=square.image_path,
                                                            sigma_contrast=image.DefaultSigmaContrast.GRIDSQUARE)
        image.arr_to_png(gridsquare_arr, os.path.join(gs_output_root, f"GridSquare_{square.id_str}.png"), scale=False)
        gs_img, gs_canvas = image.arr_to_drawable_img(gridsquare_arr, scale=False)
        smallest_hole = min(square.holes.values(), key=lambda x: x.radius)
        # Figure that a label can radius * 1.5 * 2 * fudgefactor long
        max_hole_label_pixels = smallest_hole.radius * 3 * GRIDSQUARE_HOLE_DRAWING_SIZE_FUDGE
        hole_label_font = image.maximize_font_to_fit(canvas=gs_canvas,
                                                     font_path=FONT_PATH,
                                                     text=str(smallest_hole.id_str),
                                                     max_text_length=max_hole_label_pixels,
                                                     min_font_size=10)
        for hole in square.holes.values():
            image.draw_hole(gs_canvas, coord=(hole.x_pos, hole.y_pos),
                            radius=hole.radius * GRIDSQUARE_HOLE_DRAWING_SIZE_FUDGE,
                            label=hole.id_str, label_font=hole_label_font)
            if hole.image_path is not None:
                image.image_file_to_png(input_path=os.path.join(epu_session.session_dir, hole.image_path),
                                        output_path=os.path.join(hole_output_dir, f"FoilHole_{hole.id_str}.png"),
                                        sigma_contrast=image.DefaultSigmaContrast.HOLE)
            for a in hole.acquisitions:
                image.image_file_to_png(input_path=os.path.join(epu_session.session_dir, a),
                                        output_path=os.path.join(acq_output_dir, f"FoilHole_{hole.id_str}_Data.png"),
                                        sigma_contrast=image.DefaultSigmaContrast.DATA)
        gs_img.save(os.path.join(gs_output_root, f"GridSquare_{square.id_str}_annotated.png"),
                    format="png", compress_level=9)
