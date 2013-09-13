from django.db.models import fields
import uuid
import base64
from model_registry.registry import get_class_id_choices
from django.db.models.fields.related import ForeignObject, CASCADE, ForeignObjectRel

class ModelIDField(fields.IntegerField):
    """
    def __init__(self, *args, **kwargs):
    
        if 'db_index' not in kwargs:
            kwargs['db_index'] = True
            
        super(ModelIDField, self).__init__(*args, **kwargs)

    def get_attname(self):
        return '%s_id' % self.name

    def get_attname_column(self):
        attname = self.get_attname()
        column = self.db_column or attname
        return attname, column
    
    def contribute_to_class(self, cls, name, virtual_only=False):
        sup = super(ModelIDField, self)

        # Store the opts for related_query_name()
        self.opts = cls._meta

        if hasattr(sup, 'contribute_to_class'):
            sup.contribute_to_class(cls, name, virtual_only=virtual_only)
            
        setattr(cls, self.name, )
        \"""
        if not cls._meta.abstract and self.rel.related_name:
            related_name = self.rel.related_name % {
                'class': cls.__name__.lower(),
                'app_label': cls._meta.app_label.lower()
            }
            self.rel.related_name = related_name
        other = self.rel.to
        if isinstance(other, six.string_types) or other._meta.pk is None:
            def resolve_related_class(field, model, cls):
                field.rel.to = model
                field.do_related_class(model, cls)
            add_lazy_relation(cls, self, other, resolve_related_class)
        else:
            self.do_related_class(other, cls)
        """

    
    def _get_choices(self, ):
        """ choices are every registered Model """
        return get_class_id_choices()
    
    def _set_choices(self, choices):
        """ choices are every registered Model """
        pass
    
    _choices = property(_get_choices, _set_choices)
    


class UuidField(fields.Field):
        
    def get_internal_type(self):
        return 'CharField'
    
    def db_type(self, connection):
        if connection.settings_dict['ENGINE'] == 'django.db.backends.postgresql_psycopg2':
            return 'uuid'
        elif connection.settings_dict['ENGINE'] == 'django.db.backends.mysql':
            return 'char(36)'#32??
        else:
            return 'char(36)'
    
    def to_python(self,value):
        """
        @brief returns a uuid version 1
        """
        if isinstance(value, uuid.UUID):
            return value
        else:
            return uuid.UUID(value) if value else None
        
    
    def get_prep_value(self, value):
        """
        @brief returns the raw value of the data container
        """
        if value is None:
            return None
        if not isinstance(value, basestring):
            value = str(value)
        if len(value) == 36:
            return value
        
        return None