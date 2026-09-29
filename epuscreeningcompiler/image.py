import os
from enum import Enum
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import mrcfile
from sklearn.mixture import GaussianMixture
import pzdip


class DefaultSigmaContrast(Enum):
    ATLAS = 4.0
    GRIDSQUARE = 4.0
    HOLE = 5.0
    DATA = 2.75
    PS = 0.6


def sigma_contrast_arr(data, sigma=3.0, mu=None, std=None, new_range=(0, 1), inplace=False):
    """
    Apply sigma contrast adjustment to the values in `data`.

    Clips all values in `data` to within ``mean(data) +/- sigma * std(data)`` then linearly scales the results to
    `new_range`.

    Parameters
    ----------
    data : array-like
        N-dimensional array of values to be scaled
    sigma : float
        How many standard deviations around the mean to keep. Smaller values lead to higher contrast.
    mu : float
        Use this mean instead of computing data mean
    std : float
        Use this std instead of computing data std
    new_range : tuple of float
        The new range for the resulting values. Generally `(0, 1)` or `(0, 255)`.
    inplace : bool
        If `data` is a numpy ndarray, the operation can optionally be performed in-place. In this case nothing is
        returned.

    Returns
    -------
    numpy.ndarray
        The contrast-scaled values. This will have the same shape as `data`.
    """
    # Promote incoming array to full-precision float b/c Relion's new float16 MRC files were causing overflow in np.std
    # If it's already full precision, numpy is smart enough not to make a copy
    data_ = np.asarray(data, dtype=float)

    mean = np.mean(data_) if mu is None else mu
    std = np.std(data_) if std is None else std
    delta = std * sigma
    bottom = max(mean - delta, np.min(data))
    top = min(mean + delta, np.max(data))
    slope = (new_range[1] - new_range[0]) / (top - bottom)
    b = new_range[0] - bottom * slope
    if inplace:
        # if no type promotion was needed, everything can be truly in-place, otherwise (for float16 MRC) we'll do the
        # next best thing and reassign the results back into the original array
        if data_ is data:
            data.clip(bottom, top, out=data)
            data *= slope
            data += b
        else:
            data[:] = np.clip(data_, bottom, top) * slope + b
    else:
        return np.clip(data_, bottom, top) * slope + b


def auto_contrast(arr, sigma=3.0, new_range=(0, 1), inplace=False):
    # apply sigma contrast if unimodal, else fit 2 component gmm and sigma contrast based on the brighter component
    if pzdip.zdip(arr, downsample=True).multimodal:
        flat = arr.ravel()
        n = flat.size
        if n > 200_000:
            rng = np.random.default_rng()
            flat = rng.choice(flat, size=max(200_000, n // 100), replace=False)
        gmm = GaussianMixture(n_components=2, covariance_type="full")
        gmm.fit(flat.reshape(-1, 1))
        order = np.argsort(gmm.means_.ravel())
        mean = gmm.means_.ravel()[order][1]
        std = np.sqrt(gmm.covariances_.ravel()[order][1])
        return sigma_contrast_arr(arr, sigma=sigma, mu=mean, std=std, new_range=new_range, inplace=inplace)
    else:
        return sigma_contrast_arr(arr, sigma=sigma, new_range=new_range, inplace=inplace)


def image_file_to_arr(path):
    """
    Return a numpy array representing the contents of a greyscale TIFF or MRC file. The file extension is used as the
    heuristic for file type.

    Parameters
    ----------
    path : str or os.PathLike
        The file path to the image

    Returns
    -------
    np.ndarray : the contents of the image file
    """
    _, path_ext = os.path.splitext(path)

    if path_ext in (".tiff", ".tif"):
        return np.array(Image.open(path))
    elif path_ext == ".mrc":
        with mrcfile.open(path, permissive=True) as mrc:
            return mrc.data
    else:
        raise ValueError(f"Unrecognized file extension: {path_ext}")


def image_file_to_contrasted_arr(path, sigma_contrast, do_auto_contrast=False):
    raw_data = image_file_to_arr(path)
    if isinstance(sigma_contrast, DefaultSigmaContrast):
        sigma_contrast = sigma_contrast.value
    if do_auto_contrast:
        return auto_contrast(raw_data, sigma_contrast=sigma_contrast, new_range=(0,255))
    else:
        return sigma_contrast_arr(raw_data, sigma=sigma_contrast, new_range=(0, 255))


def arr_to_img(data, scale=True):
    """
    Create a greyscale (mode 'L') Pillow Image object from a 2D numpy array.

    Parameters
    ----------
    data : ndarray
        A 2-D array with pixel values
    scale : bool
        Rescale `data` to the range [0,255]?

    Returns
    -------
    PIL.Image.Image
        A mode 'L' Pillow Image object based on `data` after applying any requested transformations.
    """
    # Scale the values, whatever they may be, to [0-255]
    if scale:
        data = (data - np.min(data)) / np.ptp(data) * 255
    return Image.fromarray(np.uint8(data), 'L')


def arr_to_drawable_img(arr, scale=True):
    img = arr_to_img(arr, scale=scale).convert(mode="RGB")
    draw = ImageDraw.Draw(img, mode="RGB")
    return img, draw


def arr_to_png(arr, output_path, scale=True):
    arr_to_img(arr, scale=scale).save(output_path, format='png', compress_level=9)


def image_file_to_png(input_path, output_path, sigma_contrast=None):
    """
    Convert a TIFF or MRC file to a new PNG file, optionally applying sigma contrast

    Parameters
    ----------
    input_path : str or os.PathLike
        The source TIFF or MRC file
    output_path : str or os.PathLike
        The destination file path and name for the resulting PNG file
    sigma_contrast : float or DefaultSigmaContrast, optional
        If numeric, apply this numeric sigma_contrast window; if a DefaultSigmaContrast enum instance, use its
        underlying value

    Returns
    -------
    None
    """
    data = image_file_to_arr(input_path)
    if sigma_contrast:
        if isinstance(sigma_contrast, DefaultSigmaContrast):
            sigma_contrast = sigma_contrast.value
        data = sigma_contrast_arr(data, sigma=sigma_contrast, new_range=(0, 255))
    arr_to_png(data, output_path)


def draw_gridsquare(canvas, vertices, color="red", linewidth=10,
                    label=None, label_font=None, label_textcolor=None, label_pos=None, label_anchor="mm"):
    canvas.polygon(xy=[tuple(x) for x in vertices],
                   outline=color, width=linewidth)
    if label is not None:
        if label_textcolor is None:
            label_textcolor = color
        canvas.text(xy=label_pos, text=str(label), font=label_font, anchor=label_anchor, fill=label_textcolor)


def draw_hole(canvas, coord, radius, color="red", linewidth=10,
              label=None, label_font=None, label_textcolor=None, label_anchor="md"):
    canvas.ellipse(xy=(coord[0] - radius,
                       coord[1] - radius,
                       coord[0] + radius,
                       coord[1] + radius),
                   outline=color, width=linewidth)
    if label is not None:
        if label_textcolor is None:
            label_textcolor = color
        canvas.text(xy=(coord[0], coord[1] - radius), anchor=label_anchor, font=label_font, fill=label_textcolor,
                    text=str(label))


def maximize_font_to_fit(canvas, font_path, text, max_text_length, min_font_size):
    max_font_size = min_font_size
    font = ImageFont.truetype(font_path, size=max_font_size)
    while canvas.textlength(text=text, font=font) < max_text_length:
        max_font_size += 1
        font = ImageFont.truetype(font_path, size=max_font_size)
    return font
