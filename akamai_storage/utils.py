from akamai.storage import AkamaiNetStorage
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.files import storage as django_storage


def get_storage_class(key):
    try:
        # Quick default check
        if key == 'default':
            return django_storage.default_storage

        # Check if settings exist
        if not hasattr(settings, 'FILE_STORAGES'):
            raise

        # Check if requested storage is setup
        storages = getattr(django_storage, 'storages', {})
        if key in storages:
            raise

        # Get the config for the key
        if key not in settings.FILE_STORAGES:
            raise

        # Try to setup the storage
        config = settings.FILE_STORAGES[key]

        if config['FILE_STORAGE'] != 'akamai.storage.AkamaiNetStorage':
            raise

        storage = storages[key] = AkamaiNetStorage(file_storage_key=key)
        return storage

    except:
        raise ImproperlyConfigured('Could not get storage class for key: ' + key)
