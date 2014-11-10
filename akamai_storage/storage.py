import ftplib
import os
import urlparse
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.files import temp as tempfile
from django.core.files.base import File
from django.core.files.storage import Storage
from django.utils import six
from django.utils.encoding import force_bytes
from io import BytesIO


class AkamaiNetStorageException(Exception):
    pass


class AkamaiNetStorage(Storage):
    """Akamai NetStorage class for Django pluggable storage system."""

    def __init__(self, file_storage_key='default'):
        self._config_key = file_storage_key
        self._config = self._get_config(self._config_key)
        self._base_url = self._config['MEDIA_URL']
        self._connection = None

    def _get_config(self, key):
        if settings.FILE_STORAGES and key in settings.FILE_STORAGES:
            return settings.FILE_STORAGES[key]
        raise ImproperlyConfigured('Can not find configuration for Akamai NetStorage with key: {}'.format(key), code='storage_akamai_config')

    # Defined by Storage

    def _open(self, name, mode='rb'):
        self._start_connection()
        memory, file = self._retrieve_file(name)
        if memory:
            ret_file = AkamaiContentFile(file, name, self)
        else:
            ret_file = AkamaiFile(file, name, self)
        return ret_file

    def _save(self, name, content):
        content.open()
        self._start_connection()
        self._put_file(name, content)
        content.close()
        content = self._open(name)
        return name

    def get_available_name(self, name):
        return name

    def delete(self, name):
        if not self.exists(name):
            return
        self._start_connection()
        try:
            self._connection.delete(name)
        except ftplib.all_errors:
            raise AkamaiNetStorageException('Error when removing %s' % name)

    def exists(self, name):
        self._start_connection()
        try:
            if name in self._connection.nlst(os.path.dirname(name) + '/'):
                return True
            else:
                return False
        except ftplib.error_temp:
            return False
        except ftplib.error_perm:
            # error_perm: 550 Can't find file
            return False
        except ftplib.all_errors:
            raise AkamaiNetStorageException('Error when testing existence of %s' % name)

    def listdir(self, path):
        self._start_connection()
        try:
            dirs, files = self._get_dir_details(path)
            return dirs.keys(), files.keys()
        except AkamaiNetStorageException:
            raise

    def size(self, name):
        self._start_connection()
        try:
            dirs, files = self._get_dir_details(os.path.dirname(name))
            if os.path.basename(name) in files:
                return files[os.path.basename(name)]
            else:
                return 0
        except AkamaiNetStorageException:
            return 0

    def url(self, name):
        if self._base_url is None:
            raise ValueError("This file is not accessible via a URL.")
        return urlparse.urljoin(self._base_url, name).replace('\\', '/')

    # TODO Access, created, and modified time methods

    # Akamai NetStorage Storage functions

    def _create_temp_file(self):
        self.stream_class = False
        if settings.FILE_UPLOAD_TEMP_DIR:
            file = tempfile.NamedTemporaryFile(suffix='.akamai', dir=settings.FILE_UPLOAD_TEMP_DIR)
        else:
            file = tempfile.NamedTemporaryFile(suffix='.akamai')
        return file

    def _create_stream(self, content=''):
        stream_class = BytesIO
        if six.PY2:
            content = force_bytes(content)
        return stream_class(content)

    def _start_connection(self):
        # Check if connection is still alive and if not, drop it.
        if self._connection is not None:
            try:
                self._connection.pwd()
            except ftplib.all_errors:
                self._connection = None

        # Real reconnect
        if self._connection is None:
            ftp = ftplib.FTP()
            try:
                ftp.connect(self._config['HOST'], self._config['PORT'])
                ftp.login(self._config['USER'], self._config['PASSWORD'])
                if self._config['PATH'] != '':
                    ftp.cwd(self._config['PATH'])
                self._connection = ftp
                return
            except ftplib.all_errors:
                raise AkamaiNetStorageException('Connection or login error using data %s' % repr(self._config))

    def _end_connection(self):
        """
        Ignore, keep the connection open for as long as possible.
        Use disconnect() to terminate the connection
        """
        pass

    def disconnect(self):
        self._connection.quit()
        self._connection = None

    def _mkremdirs(self, path):
        pwd = self._connection.pwd()
        path_splitted = path.split('/')
        for path_part in path_splitted:
            try:
                self._connection.cwd(path_part)
            except:
                try:
                    self._connection.mkd(path_part)
                    self._connection.cwd(path_part)
                except ftplib.all_errors:
                    raise AkamaiNetStorageException('Cannot create directory chain %s' % path)
        self._connection.cwd(pwd)
        return

    def _put_file(self, name, content):
        # Connection must be open!
        try:
            self._mkremdirs(os.path.dirname(name))
            pwd = self._connection.pwd()
            self._connection.cwd(os.path.dirname(name))
            self._connection.storbinary('STOR ' + os.path.basename(name), content.file, content.DEFAULT_CHUNK_SIZE)
            self._connection.cwd(pwd)
        except ftplib.all_errors:
            raise AkamaiNetStorageException('Error writing file %s' % name)

        # TODO flush

    def _retrieve_file(self, name):
        try:
            pwd = self._connection.pwd()
            self._connection.cwd(os.path.dirname(name))

            if self.size(name) > settings.FILE_UPLOAD_MAX_MEMORY_SIZE:
                file_in_memory = False
                file = self._create_temp_file()
            else:
                file_in_memory = True
                file = self._create_stream()

            self._connection.retrbinary('RETR ' + os.path.basename(name), file.write)
            file.seek(0)
            self._connection.cwd(pwd)

            return file_in_memory, file
        except ftplib.all_errors:
            raise AkamaiNetStorageException('Error retrieving remote file %s' % name)

    def _get_dir_details(self, path, recursive=False, show_folders=True, show_files=True):
        # Connection must be open!
        try:
            lines = []

            command = 'LIST {options} {path}'.format(**{
                'options': '' if not recursive else '-R',
                'path': path,
            })

            self._connection.retrlines(command, lines.append)

            dirs = {}
            files = {}

            current_path = os.path.normpath(path)

            for line in lines:
                if not line:
                    continue
                if line.endswith(":"):
                    current_path = os.path.normpath(line[:-1])
                    continue

                words = line.split()
                if len(words) < 6:
                    continue
                if words[-2] == '->':
                    continue

                if show_folders and words[0][0] == 'd':
                    if not recursive:
                        dirs[words[-1]] = 0
                    else:
                        dirs[os.path.normpath(current_path + '/' + words[-1])] = 0
                elif show_files and words[0][0] == '-':
                    if not recursive:
                        files[words[-1]] = int(words[-5])
                    else:
                        files[os.path.normpath(current_path + '/' + words[-1])] = int(words[-5])

            return dirs, files
        except ftplib.all_errors:
            raise AkamaiNetStorageException('Error getting listing for %s' % path)

    def _get_dir_extra_details(self, path, recursive=True, ):
        self._start_connection()
        try:
            command = 'LIST {options} {path}'.format(**{
                'options': '' if not recursive else '-R',
                'path': path,
            })

            lines = []

            self._connection.retrlines(command, lines.append)

            return lines

        except ftplib.all_errors:
            raise AkamaiNetStorageException('Error getting listing for %s' % path)


class AkamaiContentFile(File):
    def __init__(self, file, name, storage):
        self._storage = storage
        super(AkamaiContentFile, self).__init__(file, name=name)

    def __bool__(self):
        return True

    def __nonzero__(self):      # Python 2 compatibility
        return type(self).__bool__(self)

    def open(self, mode=None):
        self.seek(0)

    def close(self):
        pass


class AkamaiFile(File):
    def __init__(self, file, name, storage):
        self._storage = storage
        super(AkamaiFile, self).__init__(file, name=name)

    def open(self, mode=None):
        if not self.closed:
            self.seek(0)
        elif self.name and self._storage.exists(self.name):
            self.file = self._storage._retrieve_file(self.name)
        else:
            raise ValueError("The file cannot be opened.")

    def _get_size(self):
        if not hasattr(self, '_size'):
            if hasattr(self.file, 'size'):
                self._size = self.file.size
            else:
                self._size = self._storage.size(self.name)
        return self._size

    def _set_size(self, size):
        self._size = size

    size = property(_get_size, _set_size)
