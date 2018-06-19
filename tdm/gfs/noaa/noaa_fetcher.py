import datetime
import os
import time
from ftplib import FTP
from concurrent import futures
import logging

logging.basicConfig()
LOGGER = logging.getLogger('tdm.gfs.noaa')
LOGGER.setLevel(logging.DEBUG)


class noaa_fetcher(object):
    NOAA_FTP_SERVER = 'ftp.ncep.noaa.gov'
    NOAA_BASE_PATH = '/pub/data/nccf/com/gfs/prod/'
    NOAA_DATASET_FOLDER_SIZE = 196608

    @classmethod
    def list_files_in_path(cls, path):
        entries = {}

        def add_clean_entry(x):
            size, name = [x.split()[i] for i in (4, 8)]
            entries[name] = {'size': int(size), 'name': name}

        with FTP(cls.NOAA_FTP_SERVER) as ftp:
            ftp.login()
            ftp.cwd(path)
            ftp.retrlines('LIST', callback=add_clean_entry)

        return entries

    @classmethod
    def list_available_dataset_groups(cls):
        return cls.list_files_in_path(cls.NOAA_BASE_PATH)

    def __init__(self, year, month, day, hour):
        self.date = datetime.datetime(year, month, day, hour, 0)
        self.ds = 'gfs.%s' % self.date.strftime("%Y%m%d%H")
        LOGGER.info('Initialized for dataset %s', self.ds)

    def is_dataset_ready(self):
        available_groups = self.list_available_dataset_groups()
        return (self.ds in available_groups and
                available_groups[self.ds]['size']
                <= self.NOAA_DATASET_FOLDER_SIZE)

    def fetch_file(self, ds_path, fname, tdir):
        LOGGER.info('Fetching %s/%s into %s', self.ds, fname, tdir)
        target = os.path.join(tdir, fname)
        with FTP(self.NOAA_FTP_SERVER) as ftp:
            ftp.login()
            ftp.cwd(ds_path)
            cmd = 'RETR %s' % fname
            ftp.retrbinary(cmd, open(target, 'wb').write,
                           blocksize=1024*1024)
        return target

    def fetch(self, res, tdir, pattern='gfs.t%Hz.pgrb2b',
              nthreads=4, tsleep=300):
        ds_path = os.path.join(self.NOAA_BASE_PATH, self.ds)
        pre = self.date.strftime(pattern) + '.' + res
        LOGGER.info('Fetching %s/%s into %s', self.ds, pre, tdir)
        while not self.is_dataset_ready():
            LOGGER.info('Dataset %s not ready, sleeping for %d sec', tsleep)
            time.sleep(tsleep)
        files = [f for f in self.list_files_in_path(ds_path)
                 if f.startswith(pre)]

        with futures.ThreadPoolExecutor(max_workers=nthreads) as executor:
            fut_by_fname = {executor.submit(self.fetch_file,
                                            ds_path, fname, tdir): fname
                            for fname in files}
            for fut in futures.as_completed(fut_by_fname):
                fname = fut_by_fname[fut]
                try:
                    res = fut.result()
                except Exception as exc:
                    LOGGER.error('%r generated an exception: %s', fname, exc)
                else:
                    LOGGER.info('%r saved in %s', fname, res)
