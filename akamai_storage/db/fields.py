from __future__ import unicode_literals
from akamai.forms.fields import AkamaiFilePathField as AkamaiFilePathFormField
from akamai.utils import get_storage_class
from django.core import exceptions
from django.db.models.fields import TextField
from django.utils.translation import ugettext_lazy as _


class AkamaiFilePathField(TextField):
    description = _("Akamai file path")

    def __init__(self, verbose_name=None, name=None, path='', match=None,
                 allow_files=True, allow_folders=False, storage_key=None, **kwargs):
        self.path = path
        self.match = match
        self.allow_files = allow_files
        self.allow_folders = allow_folders
        self.storage_key = storage_key
        self.storage = None
        if storage_key:
            self.storage = get_storage_class(self.storage_key)

        kwargs['max_length'] = kwargs.get('max_length', 2048)

        super(AkamaiFilePathField, self).__init__(verbose_name=verbose_name, name=name, **kwargs)

    def deconstruct(self):
        # TODO
        name, path, args, kwargs = super(AkamaiFilePathField, self).deconstruct()

        if kwargs.get("max_length", None) == 2048:
            del kwargs["max_length"]

        # if self.storage is not default_storage:
        #     kwargs['storage'] = self.storage

        return name, path, args, kwargs

    def validate(self, value, model_instance):
        if not self.editable:
            # Skip validation for non-editable fields.
            return

        if value is None and not self.null:
            raise exceptions.ValidationError(self.error_messages['null'], code='null')

        if not self.blank and value in self.empty_values:
            raise exceptions.ValidationError(self.error_messages['blank'], code='blank')

        # find storage
        storage = get_storage_class('default')
        if not storage.exists(value):
            raise exceptions.ValidationError(
                self.error_messages['invalid_choice'],
                code='invalid_choice',
                params={'value': value},
            )
