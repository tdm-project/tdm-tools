from distutils.core import setup

setup(
    name='tdm',
    version='0.0',
    description='tdm modules and tools',
    author='ALfred E. Neumann',
    author_email='aen@gmail.com',
    packages=['tdm', 'tdm.gfs', 'tdm.gfs.noaa', 'tdm.radar', 'tdm.wrf'],
    scripts=[
        'bin/gfs_fetch',
        'bin/link_grib',
        'bin/radar_events',
        'bin/radar_nc_to_geo',
        'bin/rainfall',
        'bin/wrf_configurator',
        'bin/grib2cf',
    ],
)
