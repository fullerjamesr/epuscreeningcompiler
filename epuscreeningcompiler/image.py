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


def sigma_contrast_arr(data, sigma=3.0, mu=None, std=None, new_range=(0,255), inplace=False):
    """
    Clip all values in ``data`` to within ```mu +/- sigma * std``` then linearly scales the results to
    `new_range`. If `mu` or `std` are not provided, they assume the value of ``np.mean(data)`` or ``np.std(data)``,
    respectively.

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
        The contrast-scaled values. This will have the same shape as ``data``.
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
        return data
    else:
        return np.clip(data_, bottom, top) * slope + b


def clip_extremes(data, low=0.1, high=99.9, inplace=False):
    """
    Clip all values in ``data`` to between ``low`` and ``high`` percentiles. Intended for "hot pixel" removal.

    Parameters
    ----------
    data : np.ndarray
    low : float
        Low end percentile (0-100) to which values are clipped. Use 0 to not clip the low/dark end.
    high : float
        High end percentile (0-100) to which values are clipped. Use 100 to not clip the high/bright end.
    inplace : bool
        If True, clip `data` itself instead of a copy.

    Returns
    -------
    np.ndarray
        If `inplace` is False, a new float64 array (the input is not modified) clipped to the exact, interpolated,
        percentile values. This holds even for integer input, so that the bounds are not rounded.

        If `inplace` is True, `data` itself, with its original dtype. Because an integer array cannot hold fractional
        bounds, for integer arrays the lower bound is rounded down and the upper bound is rounded up to whole numbers
        (i.e., slightly fewer pixels are clipped than the percentiles strictly imply).

    Raises
    ------
    ValueError
        If the percentiles do not satisfy ``0 <= low < high <= 100``.

    Notes
    -----
    If the `low` and `high` percentile values are equal (more than ``high - low`` percent of the pixels share a single
    value) nothing is clipped. In that case the result is `data` itself if `inplace` is True or a float64 copy of
    `data` if not.
    """
    if not 0 <= low < high <= 100:
        raise ValueError(f"Percentiles must satisfy 0 <= low < high <= 100, got low={low}, high={high}")
    bottom, top = np.percentile(data, [low, high])
    if top <= bottom:
        # More than (high - low)% of the pixels share one value, so fall back to the full range of the data
        return data if inplace else data.astype(float)
    if inplace and not np.can_cast(bottom.dtype, data.dtype, casting='same_kind'):
        bottom = np.floor(bottom).astype(data.dtype)
        top = np.ceil(top).astype(data.dtype)
    return np.clip(data, bottom, top, out=data if inplace else None)


def scale_arr(arr, new_range=(0,255), inplace=False):
    """
    Linearly re-scale the values in the input array so that its minimum maps to ``new_range[0]`` and its maximum to
    ``new_range[1]``.

    Parameters
    ----------
    arr : np.ndarray
        Array of finite values to be scaled. The array must not be constant (see Notes).
    new_range : tuple of float
        The new range for the resulting values. E.g., generally `(0, 1)` or `(0, 255)`.
    inplace : bool
        If True, scale `arr` itself instead of a copy.

    Returns
    -------
    np.ndarray
        If `inplace` is False, returns a new float64 array (the input is not modified).

        If `inplace` is True, `arr` itself is returned. A float64 array is scaled directly. Arrays of other
        types are scaled as float64 and then written back.

    Notes
    -----
    For in-place operations on a non float array, a copy of the input in float format is made regardless of `inplace`.
    No check is made that subsequent assignment/truncation back to the original dtype of `arr` will be sensible.

    There is no special handling for constant arrays (maximum equal to minimum): the scale would be
    zero, so the result is NaN everywhere, along with a RuntimeWarning from numpy. Real images are never constant, so
    this indicates a broken or empty image, and the warning is meant to make that visible. Casting those NaNs back into
    an integer array in-place gives platform-dependent values.
    """
    # first scale to [0, 1] as dtype=float ... then re-expand to desired range and dtype
    arr_ = np.asarray(arr, dtype=float)
    # if float conversion did not require a copy but we're not supposed to touch the original, make a copy
    if arr_ is arr and not inplace:
        arr_ = arr_.copy()
    # below this line, arr_ can be safely manipulated in place
    starting_min = np.min(arr_)
    starting_max = np.max(arr_)
    arr_ -= starting_min
    # don't combine the next 2 ops below, or else floating point error can truncate int conversion (e.g. 254 instead
    # of 255)
    arr_ /= (starting_max - starting_min)
    arr_ *= (new_range[1] - new_range[0])
    arr_ += new_range[0]
    # only an array that needed type promotion (e.g. ints) has to be written back (and cast to its dtype)
    # otherwise return the float converted form
    if inplace:
        if arr_ is not arr:
            arr[:] = arr_
        return arr
    return arr_


def auto_contrast_arr(arr, sigma=3.0, new_range=(0,255), inplace=False):
    # apply sigma contrast if unimodal, else fit 2 component gmm and sigma contrast based on the brighter component
    if isinstance(sigma, DefaultSigmaContrast):
        sigma = sigma.value
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
            return mrc.data.copy()
    else:
        raise ValueError(f"Unrecognized file extension: {path_ext}")


def image_file_to_contrasted_arr(path, sigma_contrast, auto_contrast=False):
    raw_data = image_file_to_arr(path)
    if isinstance(sigma_contrast, DefaultSigmaContrast):
        sigma_contrast = sigma_contrast.value
    if auto_contrast:
        return auto_contrast_arr(raw_data, sigma=sigma_contrast, new_range=(0,255))
    else:
        return sigma_contrast_arr(raw_data, sigma=sigma_contrast, new_range=(0,255))


def arr_to_img(data):
    """
    Create a greyscale (mode 'L') Pillow Image object from a 2D numpy array.

    Parameters
    ----------
    data : ndarray
        A 2-D array with pixel values

    Returns
    -------
    PIL.Image.Image
        A mode 'L' Pillow Image object based on `data` after applying any requested transformations.
    """
    return Image.fromarray(np.uint8(data), 'L')


def arr_to_drawable_img(arr):
    img = arr_to_img(arr).convert(mode="RGB")
    draw = ImageDraw.Draw(img, mode="RGB")
    return img, draw


def arr_to_png(arr, output_path):
    arr_to_img(arr).save(output_path, format='png', compress_level=9)


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


def horizontal_chord_through_center(vertices):
    """Length of the horizontal line through the center of a convex polygon, cut off at its edges.

    `vertices` is a sequence of (x, y) points given in order around the polygon (intended as EPU's arbitrarily rotated
    rectangles). The list must be in order! This is inherent to how we calculate the gridsquare vertices in
    epu.py::parse_gridsquare_data_from_atlas(). The center is taken as the mean of the vertices Y coords. A horizontal
    line through the center is intersected with each edge, and the chord length is the max - min of the x-coordinates of
    those intersections.

    Raises ValueError if there are fewer than 3 vertices or the center line crosses fewer than two edges,
    which cannot happen for a valid polygon.
    """
    # this shouldn't be a problem unless the EPU metadata was parsed wrong or corrupted
    # as far as I know all squares in EPU are still treated as rectangles. even hexaufoils.
    n = len(vertices)
    if n < 3:
        raise ValueError(f"Need at least 3 vertices to define a polygon, got {n}")

    TOL = 1e-9
    cy = sum(y for _, y in vertices) / n # cy is the "height" of the square center
    xs = []
    for i in range(n):
        x1, y1 = vertices[i]
        x2, y2 = vertices[(i + 1) % n]
        if abs(y2 - y1) < TOL:
            continue
        t = (cy - y1) / (y2 - y1)
        if -TOL <= t <= 1.0 + TOL:
            xs.append(x1 + t * (x2 - x1))

    # unknown if EPU would ever write a "square" with nearly zero height or width but better safe than sorry
    # this also might suggest corrupted or mis-parsed EPU files
    if len(xs) < 2:
        raise ValueError(f"Horizontal line through center intersects fewer than 2 edges of {vertices}")
    return max(xs) - min(xs)


def maximize_font_to_fit(canvas, font_path, text, max_text_length, min_font_size):
    max_font_size = min_font_size
    font = ImageFont.truetype(font_path, size=max_font_size)
    while canvas.textlength(text=text, font=font) < max_text_length:
        max_font_size += 1
        font = ImageFont.truetype(font_path, size=max_font_size)
    return font
