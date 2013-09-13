from model_registry.exceptions import *
from django.conf import settings
from model_registry.settings import registry_settings
from model_registry.signals import class_registered


class BaseRegistry(object):
    """The registry keeps track of models used in this project."""

    def __init__(self):
        self.model_registry = {}
        self.handler_registry = {}
        self.origin_registry = {}
        self.known_model_ids = {}
        
    def get_model_registry(self, ):
        return self.model_registry
    
    def get_registered_models(self, ):
        return [value for value in self.get_model_registry().values() if not getattr(value, '_virtual_model', False)]
    
        
    def get_model_registry(self, ):
        return self.origin_registry
    
    def get_handler_registry(self, ):
        return self.handler_registry
    
    def get_class_id(self, cls):
        if not hasattr(cls, "_class_id"):
            raise Exception, "{cls} has no _class_id defined!".format(cls=str(cls))
        
        return getattr(cls, "_class_id")
    
    
    def register_model(self, cls):
        model_registry = self.get_model_registry()
        
        if getattr(cls, "_registered_model", False):
            return cls
        
        class_id    =   self.get_class_id(cls)
        hash_val    =   class_id
        
        if hash_val in model_registry:
            if cls.__name__ == model_registry[hash_val].__name__ and cls.__module__ == model_registry[hash_val].__module__:
                return cls
            #from django.conf import settings
            raise Exception, "already registered class_id '%s': \n\
                            '%s, %s' - conflicted by \n\
                            '%s, %s' \n" % (str(class_id), str(model_registry[hash_val].__name__), str(model_registry[hash_val].__module__), str(cls.__name__), str(cls.__module__))
        
        model_registry[hash_val] = cls
        setattr(cls, "_registered_model", True)
        
        class_registered.send(sender=self, cls=cls)
        return cls
    
    def register_model_change_handler(self, class_id, func=None):
        def inner(func):
            model_handler_registry = self.get_handler_registry()
            class_hash_val    =   class_id
            
            if class_hash_val not in model_handler_registry:
                model_handler_registry[class_hash_val] = []
            
            model_handler_registry[class_hash_val].append(func)
            
            return func
        
        if not func:
            return inner
        else:
            return inner(func)
    
    def register_model_origin(self, cls, origin, description):        
        class_id    =   self.get_class_id(cls)
        
        model_origin_registry = self.get_origin_registry()
        
        class_hash_val    =   hash(class_id)
        origin_hash_val    =   hash(origin)
        
        if origin_hash_val in origin_registry:
            raise Exception, "a origin cant be set twice"
        
        if hash_val not in model_origin_registry:
            model_origin_registry[hash_val] = {}
        
        model_origin_registry[hash_val][description] = origin
    
    

    def get_change_handler_for_id(self, class_id):
        handler_registry = self.get_handler_registry()
        if not (class_id in handler_registry or '*' in handler_registry):
            raise ModelStore_NoHandlerRegistered, str(class_id)
        return handler_registry.get(class_id, []) + handler_registry.get('*', [])
    
    def get_class_for_id(self, class_id):
        try:
            return self.get_model_registry()[hash(class_id)]
        except KeyError:
            raise ModelStore_ModelUnknown, str(class_id)
    
    def get_known_model_ids(self, ):
        registry_history = registry_settings.REGISTRY_HISTORY
        if registry_history and not self.known_model_ids:
            for key in registry_history.keys():
                self.known_model_ids[key] = self._generate_history_entry_name(registry_history, key)
        
        # make sure that a ModelID is just present in either registered OR known
        for key in  self.get_model_registry().keys():
            self.known_model_ids.pop(key, None)
        
        return self.known_model_ids
    
    
    def get_class_id_choices(self):
        return (
                ('registered', [(key, self._generate_entry_name(key, value)) for key, value in self.get_model_registry().items()]   ),
                ('known', [(key, self._generate_entry_name(key, value)) for key, value in self.get_known_model_ids().items()]   ),
            )
    
    def _generate_history_entry_name(self, registry, key):
        uuid_class = registry_settings.MODEL_REGISTRY__UUID_CLASS
        current_uuid_version_str = uuid_class._get_latest_uuid_class().get_uuid_version_str()
        
        if current_uuid_version_str in registry[key]:
            entry = registry[key][current_uuid_version_str]
            assert(isinstance(entry, (tuple, list)))
            return "%s.%s" % (entry[0], entry[1])
    
    
    def _generate_entry_name(self, key, cls=None):
        registry_history = registry_settings.REGISTRY_HISTORY
        
        if isinstance(cls, basestring):
            return cls
        
        if registry_history:
            ret = self._generate_history_entry_name(registry_history, key)
            if ret:
                return ret
            
        if cls is None:
            return str(key)
        
        if hasattr(cls, '_meta'):
            return '%s.%s' % (cls._meta.app_label, cls._meta.model_name)
        
        return str(cls.__name__)
    

    def get_id_for_class(self, cls):
        return getattr(cls, "_class_id")
    
    def get_id_for_instance(self, instance):
        return get_class_id_for_class(instance.__class__)   