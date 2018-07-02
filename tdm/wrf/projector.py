from gdal import ogr, osr


def project(transform, p):
    q = ogr.Geometry(ogr.wkbPoint)
    q.AddPoint(p[0], p[1])
    q.Transform(transform)
    return (q.GetX(), q.GetY())


class projector(object):
    def __init__(self, geometry):
        self.geometry = geometry
        if self.geometry['map_proj'] == 'lambert':
            self.set_lambert_projection()
        else:
            raise ValueError('Unkown map_proj %s' % self.geometry['map_proj'])

    def set_lambert_projection(self):
        spref = osr.SpatialReference()
        spref.SetProjCS('WRF Lambert projection')
        # World geodetic system (used by GPS)
        spref.SetWellKnownGeogCS('WSG84')
        truelat1 = self.geometry['truelat1']
        truelat2 = self.geometry['truelat2']
        center_lat = self.geometry['ref_lat']
        center_lon = self.geometry['ref_lon']
        center_lon = self.geometry['ref_lon']
        false_easting = 0
        false_northing = 0
        spref.SetLCC(truelat1, truelat2, center_lat, center_lon,
                     false_easting, false_northing)
        ispref = osr.SpatialReference()
        ispref.ImportFromEPSG(4326)
        self.c_transform = osr.CoordinateTransformation(ispref, spref)
        self.i_transform = osr.CoordinateTransformation(spref, ispref)
        self.ispref = ispref
        self.spref = spref

    def project_to_coord(self, lonlat):
        return project(self.c_transform, lonlat)

    def project_to_lonlat(self, p):
        return project(self.i_transform, p)
