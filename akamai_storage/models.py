from __future__ import unicode_literals

import os
import re

from akamai.db.fields import AkamaiFilePathField
from akamai.utils import get_storage_class
from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _
from model_utils.models import TimeStampedModel
from polymorphic_tree.models import PolymorphicMPTTModel, PolymorphicTreeForeignKey
from polymorphic import PolymorphicManager


class FileSystemManager(PolymorphicManager):

    ls_line = re.compile('^(?P<directory>[-d])(?P<permissions>[-r][-w][-x][-r][-w][-x][-r][-w][-x]) {1,}(?P<links>\d+) {1,}(?P<owner>[\w_]{0,30}) {1,}(?P<group>[\w_]{0,30}) {1,}(?P<size>\d+) {1,}(?P<lastmod_month>\w+) {1,}(?P<lastmod_day>\d+) {1,}(?P<lastmod_time_or_year>\d{2}:?\d{2}) {1,}(?P<filename>.+)$')

    def retreive(self, storage_key, path, recursive=True):
        storage = get_storage_class(storage_key)
        lines = storage._get_dir_extra_details(path, recursive)

        items = []

        current_path = path
        stor = FileStorage.objects.get(config_name=storage_key)

        for line in lines:
            print '-'* 25
            if not line:
                print '<blank>'
                # blank line
                continue
            elif line.endswith(":"):
                # switch current directory
                current_path = line[:-1]
                print 'switch to "{}"'.format(current_path)
                continue
            ln = self._split_line(line)
            print ln

            if ln['directory'] == 'd':
                item = self._cache_directory(stor, current_path, ln)
            else:
                item = self._cache_file(stor, current_path, ln)
            items.append(item)

    def _split_line(self, line):
        return self.ls_line.match(line).groupdict()

    def _cache_directory(self, storage, current_path, ln):
        print current_path, ln['filename']
        if not current_path:
            path = ln['filename']
        else:
            path = os.path.normpath('/'.join([current_path, ln['filename']]))
        print path
        try:
            directory = Directory.objects.get(storage=storage, path=path)
        except:
            directory = Directory()
            directory.storage = storage
            directory.parent = self._get_directory(storage, current_path)
            directory.path = path
            directory.name = ln['filename']
            directory.save()
        return directory

    def _cache_file(self, storage, current_path, ln):
        print current_path, ln['filename']
        if not current_path:
            path = ln['filename']
        else:
            path = os.path.normpath('/'.join([current_path, ln['filename']]))
        name, ext = os.path.splitext(ln['filename'])
        print path, name, ext
        try:
            file = File.objects.get(storage=storage, path=path)
        except:
            file = File()
            file.storage = storage
            file.parent = self._get_directory(storage, current_path)
            file.path = path
            file.name = name
            file.file_ext = ext[1:].lower()
            file.save()
        return file

    def _get_directory(self, storage, path):
        print '_get_directory("{}","{}")'.format(storage.config_name, path)
        if path:
            return Directory.objects.get(storage=storage, path=path)
        return None


@python_2_unicode_compatible
class FileStorage(TimeStampedModel):
    name = models.CharField(_('name'), max_length=140)
    config_name = models.CharField(_('config name'), max_length=140)

    def __str__(self):
        return self.name

    @property
    def file_storage_key(self):
        return self.config_name

    def get_storage(self):
        return get_storage_class(self.config_name)

    class Meta:
        verbose_name = _('storage')
        verbose_name_plural = _('storage')
        ordering = ('name', )


@python_2_unicode_compatible
class FileSystem(PolymorphicMPTTModel, TimeStampedModel):

    # Non-DB Fields
    # is_file = False
    # is_directory = False

    # DB Fields
    storage = models.ForeignKey(FileStorage)
    path = AkamaiFilePathField(_('path'), max_length=2048, allow_files=True, allow_folders=True)
    parent = PolymorphicTreeForeignKey('self', null=True, blank=True, related_name='children')

    objects = FileSystemManager()

    def __str__(self):
        return self.path

    class Meta:
        verbose_name = _('file system')
        verbose_name_plural = _('file system')


class File(FileSystem):
    # Non-DB Fields
    # is_file = True

    # DB Fields
    name = models.CharField(_('filename'), max_length=140, blank=True, null=True)
    file_ext = models.CharField(_('extension'), max_length=8, blank=True, null=True)

    def get_filename(self):
        return "{}.{}".format(self.name, self.file_ext)

    def set_filename(self, filename):
        name, ext = os.path.splitext(filename)
        self.name = name
        self.file_ext = ext[1:] if ext.startswith(".") else ext

    filename = property(get_filename, set_filename)

    def get_file(self):
        return self.storage.get_storage().open(self.path)

    class Meta:
        verbose_name = _('file')
        verbose_name_plural = _('files')


class Directory(FileSystem):
    # Non-DB Fields
    is_directory = True

    # DB Fields
    name = models.CharField(_('name'), max_length=140, blank=True, null=True)

    class Meta:
        verbose_name = _('directory')
        verbose_name_plural = _('directories')
