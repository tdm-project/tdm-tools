# Copyright 2018-2019 CRS4
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""\
Convert a sequence of grib2 files to a single NetCDF4 dataset using the
NetCDF Climate and Forecast (CF) Metadata Conventions
(http://cfconventions.org) Version 1.6.
"""

import os
import sys
import cdo
import subprocess
import shutil
import tempfile
import uuid


def get_files(files_dir, ext):
    files = []
    for name in os.listdir(files_dir):
        if not name.endswith(ext):
            continue
        files.append(os.path.join(files_dir, name))
    return files


def convert_to_nc(gribs, writable_dir):
    ncs_dir = tempfile.mkdtemp(dir=writable_dir)
    for g in gribs:
        nc = os.path.join(ncs_dir,
                          os.path.splitext(os.path.basename(g))[0] + '.nc')
        subprocess.run(["wgrib2", g, '-nc4', '-netcdf', nc])
    return ncs_dir


def concatenate(ncs_dir, output_nc):
    ncs = sorted(get_files(ncs_dir, '.nc'))
    c = cdo.Cdo()
    c.cat(input=' '.join(ncs), output=output_nc,  options='-r -f nc')


def annotate(ncfile, annotations):
    pass


def main(args):
    gribs = get_files(args.input, '.grib2')
    print("'%s': %d files" % (args.input, len(gribs)))
    if not gribs:
        sys.exit("no files selected, aborting")
    try:
        os.makedirs(args.output)
    except FileExistsError:
        pass
    ncs_dir = convert_to_nc(gribs, args.output)
    if args.product_class and args.name and args.instance_uid:
        tag = '{}_{}_{}'.format(args.product_class, args.name,
                                args.instance_uid)
    else:
        tag = '{}_{}'.format(os.path.basename(args.input), uuid.uuid4())
    out_fn = os.path.join(args.output, "%s.nc" % tag)
    concatenate(ncs_dir, out_fn)
    shutil.rmtree(ncs_dir)
    # annotations = {'product': 'meteosim',
    #                'product_class': args.product_class,
    #                'uid': args.instance_uid}
    # annotate(out_fn, annotations)


def add_parser(subparsers):
    parser = subparsers.add_parser("grib2cf", description=__doc__)
    parser.add_argument('-i', '--input', metavar="DIR", default=".")
    parser.add_argument('-o', '--output', metavar="DIR", default=".")
    parser.add_argument("--product-group", metavar="PRODUCT_GROUP",
                        help="e.g., meteosim", default='meteosim')
    parser.add_argument("--product-class", metavar="PRODUCT_CLASS",
                        help="e.g., moloch")
    parser.add_argument('--name', metavar="STRING")
    parser.add_argument("--instance-uid", metavar="UID",
                        help="an unique identifier for this dataset")
    parser.set_defaults(func=main)
