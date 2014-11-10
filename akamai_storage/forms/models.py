from django.forms.models import BaseModelForm, ErrorList, model_to_dict



class AkamaiBaseModelForm(BaseModelForm):
    def __init__(self, data=None, files=None, auto_id='id_%s', prefix=None,
                 initial=None, error_class=ErrorList, label_suffix=None,
                 empty_permitted=False, instance=None):
        opts = self._meta
        if opts.model is None:
            raise ValueError('ModelForm has no model class specified.')
        if instance is None:
            # if we didn't get an instance, instantiate a new one
            self.instance = opts.model()
            object_data = {}
        else:
            self.instance = instance
            object_data = model_to_dict(instance, opts.fields, opts.exclude)
        # if initial was provided, it should override the values from instance
        if initial is not None:
            object_data.update(initial)
        # self._validate_unique will be set to True by BaseModelForm.clean().
        # It is False by default so overriding self.clean() and failing to call
        # super will stop validate_unique from being called.
        self._validate_unique = False
        super(BaseModelForm, self).__init__(data, files, auto_id, prefix, object_data,
                                            error_class, label_suffix, empty_permitted)
        # Apply ``limit_choices_to`` to each field.
        for field_name in self.fields:
            formfield = self.fields[field_name]
            if hasattr(formfield, 'queryset'):
                limit_choices_to = formfield.limit_choices_to
                if limit_choices_to is not None:
                    if callable(limit_choices_to):
                        limit_choices_to = limit_choices_to()
                    formfield.queryset = formfield.queryset.complex_filter(limit_choices_to)
