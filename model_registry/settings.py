import logging
from django.conf import settings
from django.utils.functional import LazyObject, empty
from django.utils import importlib


USER_SETTINGS = getattr(settings, 'MODEL_REGISTRY', None)

DEFAULTS = {
    'MODEL_REGISTRY_CLASS':
        'model_registry.registries.BaseRegistry',
    'MODEL_REGISTRY__UUID_CLASS':
        'model_registry.uuid.SimpleModelUUID',
    'REGISTRY_HISTORY':
        None
}


# List of settings that may be in string import notation.
IMPORT_STRINGS = (
    'MODEL_REGISTRY_CLASS',
    'MODEL_REGISTRY__UUID_CLASS',
    'REGISTRY_HISTORY',
)


def perform_import(val, setting_name):
    """
    If the given setting is a string import notation,
    then perform the necessary import or imports.
    """
    if isinstance(val, basestring):
        return import_from_string(val, setting_name)
    elif isinstance(val, (list, tuple)):
        return [import_from_string(item, setting_name) for item in val]
    return val


def import_from_string(val, setting_name):
    """
    Attempt to import a class from a string representation.
    """
    parts = val.split('.')
    module_path, class_name = '.'.join(parts[:-1]), parts[-1]
    try:
        # Nod to tastypie's use of importlib.
        module = importlib.import_module(module_path)
        return getattr(module, class_name)
    except AttributeError:
        msg = "Could not import Class '%s' from module '%s' for API setting '%s'" % (class_name, module_path, setting_name)
        raise ImportError(msg)
    except:
        msg = "Could not import '%s' for API setting '%s'" % (val, setting_name)
        raise# ImportError(msg)

class Settings(object):
    """
    """
    def __init__(self, user_settings=None, defaults=None, import_strings=None):
        self.user_settings = user_settings or {}
        self.defaults = defaults or {}
        self.import_strings = import_strings or ()

    def __getattr__(self, attr):
        if attr not in self.defaults.keys():
            raise AttributeError("Invalid Registry setting: '%s'" % attr)

        try:
            # Check if present in user settings
            val = self.user_settings[attr]
        except KeyError:
            # Fall back to defaults
            val = self.defaults[attr]

        # Coerce import strings into classes
        if val and attr in self.import_strings:
            val = perform_import(val, attr)

        self.validate_setting(attr, val)

        # Cache the result
        setattr(self, attr, val)
        return val

    def validate_setting(self, attr, val):
        pass

class UserSettingsHolder(Settings):
    """
    Holder for user configured settings.
    """
    # SETTINGS_MODULE doesn't make much sense in the manually configured
    # (standalone) case.
    SETTINGS_MODULE = None

    def __init__(self, default_settings):
        """
        Requests for configuration variables not in this class are satisfied
        from the module specified in default_settings (if possible).
        """
        self.__dict__['_deleted'] = set()
        self.default_settings = default_settings

    def __getattr__(self, name):
        if name in self._deleted:
            raise AttributeError
        return getattr(self.default_settings, name)

    def __setattr__(self, name, value):
        self._deleted.discard(name)
        return super(UserSettingsHolder, self).__setattr__(name, value)

    def __delattr__(self, name):
        self._deleted.add(name)
        return super(UserSettingsHolder, self).__delattr__(name)

    def __dir__(self):
        return list(self.__dict__) + dir(self.default_settings)

_settings = Settings(USER_SETTINGS, DEFAULTS, IMPORT_STRINGS)


class LazySettings(LazyObject):
    """
    A lazy proxy for either global Django settings or a custom settings object.
    The user can manually configure settings prior to using them. Otherwise,
    Django uses the settings module pointed to by DJANGO_SETTINGS_MODULE.
    """
    def __init__(self, *args, **kwargs):
        super(LazySettings, self).__init__(*args, **kwargs)
        self._wrapped = _settings
        
    def _setup(self, name=None):
        """
        Load the settings module pointed to by the environment variable. This
        is used the first time we need any settings at all, if the user has not
        previously configured the settings manually.
        """
        
        self._wrapped = _settings
        self._configure_logging()

    def __getattr__(self, name):
        if self._wrapped is empty:
            self._setup(name)
        return getattr(self._wrapped, name)

    def _configure_logging(self):
        """
        Setup logging from LOGGING_CONFIG and LOGGING settings.
        """
        try:
            # Route warnings through python logging
            logging.captureWarnings(True)
            # Allow DeprecationWarnings through the warnings filters
            warnings.simplefilter("default", DeprecationWarning)
        except AttributeError:
            # No captureWarnings on Python 2.6, DeprecationWarnings are on anyway
            pass

        if self.LOGGING_CONFIG:
            from django.utils.log import DEFAULT_LOGGING
            # First find the logging configuration function ...
            logging_config_path, logging_config_func_name = self.LOGGING_CONFIG.rsplit('.', 1)
            logging_config_module = importlib.import_module(logging_config_path)
            logging_config_func = getattr(logging_config_module, logging_config_func_name)

            logging_config_func(DEFAULT_LOGGING)

            if self.LOGGING:
                # Backwards-compatibility shim for #16288 fix
                compat_patch_logging_config(self.LOGGING)

                # ... then invoke it with the logging settings
                logging_config_func(self.LOGGING)

    def configure(self, default_settings=_settings, **options):
        """
        Called to manually configure the settings. The 'default_settings'
        parameter sets where to retrieve any unspecified values from (its
        argument must support attribute access (__getattr__)).
        """
        if self._wrapped is not empty:
            raise RuntimeError('Settings already configured.')
        holder = UserSettingsHolder(default_settings)
        for name, value in options.items():
            setattr(holder, name, value)
        self._wrapped = holder
        self._configure_logging()

    @property
    def configured(self):
        """
        Returns True if the settings have already been configured.
        """
        return self._wrapped is not empty

registry_settings = LazySettings()
