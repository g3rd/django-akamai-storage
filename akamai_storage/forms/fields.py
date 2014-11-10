from __future__ import unicode_literals

import re

from akamai.storage import AkamaiNetStorage
from akamai.utils import get_storage_class
from django.core.exceptions import ImproperlyConfigured
from django.core.files import storage as django_storage
from django.forms import fields


class AkamaiFilePathField(fields.ChoiceField):
    def __init__(self, path='', match=None, recursive=False, allow_files=True,
                 allow_folders=False, required=True, widget=None, label=None,
                 initial=None, help_text='', storage_key=None, storage_field=None, *args, **kwargs):

        self.path, self.match, self.recursive = path, match, recursive
        self.allow_files, self.allow_folders = allow_files, allow_folders
        self.storage_key, self.storage_field = storage_key, storage_field

        super(AkamaiFilePathField, self).__init__(choices=(), required=required,
            widget=widget, label=label, initial=initial, help_text=help_text,
            *args, **kwargs)

        if storage_key:
            storage = get_storage_class(storage_key)
        elif storage_field:
            storage = django_storage.default_storage
        else:
            storage = django_storage.default_storage

        if storage.__class__ != AkamaiNetStorage:
            raise ImproperlyConfigured('AkamaiFilePathField only works with AkamaiNetStorage storage.')

        if self.required:
            self.choices = []
        else:
            self.choices = [("", "---------")]

        storage._start_connection()
        dirs, files = storage._get_dir_details(path, recursive=recursive, show_folders=allow_folders, show_files=allow_files)

        lines = sorted(dirs.keys() + files.keys(), key=str)

        if self.match is not None:
            self.match_re = re.compile(self.match)

        for line in lines:
            if self.match is None or self.match_re.search(line):
                self.choices.append((line, line))

        self.widget.choices = self.choices
