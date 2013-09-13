from model_registry.exceptions import *
from model_registry.settings import registry_settings

registry = registry_settings.MODEL_REGISTRY_CLASS()

__all__ = [
    'get_change_handler_for_id',
    'get_class_for_id',
    'get_class_id_choices',
    'register_model_origin',
    'register_model_change_handler',
    'register_model',
    'get_handler_registry',
    'get_model_registry',
    'get_registered_models',
    'get_model_registry',
    'get_id_for_class',
    'get_id_for_instance',
    'get_class_id_by_uuid'
]

get_change_handler_for_id = registry.get_change_handler_for_id

get_class_for_id = registry.get_class_for_id

get_class_id_choices = registry.get_class_id_choices

register_model_origin = registry.register_model_origin

register_model_change_handler = registry.register_model_change_handler

register_model = registry.register_model

get_handler_registry = registry.get_handler_registry

get_model_registry = registry.get_model_registry

get_registered_models = registry.get_registered_models

get_model_registry = registry.get_model_registry

get_id_for_class = registry.get_id_for_class

get_id_for_instance = registry.get_id_for_instance

get_class_id_by_uuid =  lambda id: registry_settings.MODEL_REGISTRY__UUID_CLASS(id).get('class_id')
 