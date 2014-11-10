from django.contrib import admin
from akamai.models import FileStorage, FileSystem, File, Directory
from polymorphic_tree.admin import PolymorphicMPTTParentModelAdmin, PolymorphicMPTTChildModelAdmin


@admin.register(FileStorage)
class FileStorageAdmin(admin.ModelAdmin):
    list_display = ('name', 'config_name', )
    list_display_links = ('name', )

    fieldsets = (
        (None, {'fields': ('name', 'config_name', ), }),
    )


class FileSystemChildAdmin(PolymorphicMPTTChildModelAdmin):
    GENERAL_FIELDSET = (None, {
        'fields': ('storage', 'path', 'parent', ),
    })

    base_model = FileSystem
    base_fieldsets = (
        GENERAL_FIELDSET,
    )


class FileAdmin(FileSystemChildAdmin):
    other_fields = ('name', 'file_ext', )


class DirectoryAdmin(FileSystemChildAdmin):
    other_fields = ('name', )


@admin.register(FileSystem)
class FileSystemAdmin(PolymorphicMPTTParentModelAdmin):
    base_model = FileSystem
    child_models = (
        (File, FileAdmin),
        (Directory, DirectoryAdmin),
    )

    list_display = ('path', 'actions_column',)
