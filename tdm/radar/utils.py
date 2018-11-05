from datetime import datetime, timedelta
import itertools as it
import os
import numpy as np

import gdal
from gdal import osr

gdal.UseExceptions()

strptime = datetime.strptime
splitext = os.path.splitext

FMT = "%Y-%m-%d_%H:%M:%S"
MIN_DT, MAX_DT = datetime.min, datetime.max


def get_grid(fname, unit='km', send_raster=False):
    "extract grid information from a geo image"
    raster = gdal.Open(fname)
    gt = raster.GetGeoTransform()
    # FIXME We only deal with rectangular, axis aligned images
    assert gt[2] == 0.0 and gt[4] == 0.0
    oX, oY, pxlW, pxlH = gt[0], gt[3], gt[1], gt[5]
    cols, rows = raster.RasterXSize, raster.RasterYSize
    factor = {'km': 0.001, 'm': 1.0}[unit]
    if send_raster:
        return oX, oY, factor * pxlW, factor * pxlH, cols, rows, raster
    else:
        return oX, oY, factor * pxlW, factor * pxlH, cols, rows


def compute_distance_field(fname):
    oX, oY, pxlW, pxlH, cols, rows = get_grid(fname, unit='km')
    x = pxlW * (np.arange(-(cols/2), (cols/2), 1) + 0.5)
    y = pxlH * (np.arange(-(rows/2), (rows/2), 1) + 0.5)
    xx, yy = np.meshgrid(x, y, sparse=True)
    return 10 * np.log(xx**2 + yy**2)


class GeoAdapter(object):
    def __init__(self, template):
        (self.oX,  self.oY, self.pxlW, self.pxlH,
         self.cols, self.rows, raster) = get_grid(template, unit='m',
                                                  send_raster=True)
        self.wkt = raster.GetProjectionRef()
        self.driver = gdal.GetDriverByName('GTiff')

    def save_as_gtiff(self, fname, data, metadata=None):
        raster = self.driver.Create(fname, self.cols, self.rows,
                                    1, gdal.GDT_Float32)
        raster.SetGeoTransform((self.oX, self.pxlW, 0, self.oY, 0, self.pxlH))
        if isinstance(metadata, dict):
            raster.SetMetadata(metadata)
        band = raster.GetRasterBand(1)
        band.WriteArray(data)
        raster.SetProjection(self.wkt)
        band.FlushCache()


def get_raw_radar_images(root, after=MIN_DT, before=MAX_DT):
    ls = []
    for bn in os.listdir(root):
        dt_string = splitext(bn)[0]
        try:
            dt = strptime(dt_string, FMT)
        except ValueError:
            continue
        if dt < after or dt > before:
            continue
        ls.append((dt, os.path.join(root, bn)))
    ls.sort()
    return ls


def get_grouped_raw_radar_images(root, delta, after=MIN_DT, before=MAX_DT):
    assert isinstance(delta, timedelta)

    def grouper(p):
        return after + delta * ((p[0] - after) // delta)

    return it.groupby(get_raw_radar_images(root, after, before), grouper)


def estimate_rainfall(signal, mask):
    "This is specific to XXX radar signal"
    Z = 10**(0.1*(0.39216 * signal - 8.6))
    return (Z/300)**(1/1.5) * mask


# https://gis.stackexchange.com/questions/139906
def get_wkt(srs_code):
    # checks? we need no stinking checks!
    geo, code = srs_code.split(':')
    srs = osr.SpatialReference()
    # force geo to EPSG for the time being
    srs.ImportFromEPSG(int(code))
    return srs.ExportToWkt()


def warp(in_path, out_path, t_srs, s_srs=None, error_threshold=None):
    src_ds = gdal.Open(in_path)
    dst_wkt = get_wkt(t_srs)
    src_wkt = None if s_srs is None else get_wkt(s_srs)
    error_threshold = error_threshold if error_threshold is not None else 0.125
    resampling = gdal.GRA_NearestNeighbour
    # Call AutoCreateWarpedVRT() to fetch default values for target raster
    # dimensions and geotransform
    tmp_ds = gdal.AutoCreateWarpedVRT(src_ds,
                                      src_wkt,
                                      dst_wkt,
                                      resampling,
                                      error_threshold)
    # Create the final warped raster
    gdal.GetDriverByName('GTiff').CreateCopy(out_path, tmp_ds)
