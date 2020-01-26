#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import logging
import pathlib
import inspect
import typing
from ruamel.yaml import YAML

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
formatter = logging.Formatter(fmt='%(asctime)s - %(levelname)s - %(module)s - %(message)s')
handler = logging.StreamHandler()
handler.setFormatter(formatter)
handler.setLevel(logging.INFO)
logger.addHandler(handler)


class _SchalterMeta(type):

    def get(self, arg):
        raise NotImplementedError()

    def set(cls, key, value):
        raise NotImplementedError()
    
    def get_config(cls, *_args, **_kwargs):
        raise NotImplementedError()

    def __getitem__(cls, arg):
        return cls.get(arg)

    def __setitem__(cls, key, value):
        return cls.set(key, value)

    def __contains__(cls, item):
        return cls.get_config().__contains__(item)


class ImmutableValues:
    def __init__(self):
        self._x = {}

    def __getitem__(self, item):
        return self._x[item]

    def __setitem__(self, key, value):
        return self.set(key, value)

    def set(self, key, value):
        if key not in self._x:
            self._x[key] = value
        elif self._x[key] != value:
            raise ValueError("Param '{}' already set to a different default value.".format(key))


class Schalter(object, metaclass=_SchalterMeta):

    DEFAULT_ENV_VAR_NAME = 'SCHALTER_CONFIG_LOC'
    _configurations = {}
    Unset = object()

    def __init__(self, name='default'):
        self._raw_configs = []
        self._config = {}
        # default values can only be set once and are immutable
        self.default_values = ImmutableValues()
        self._overrides_manual = {}
        self.name = name

    def __new__(cls, *args, **kwargs):
        instance = super().__new__(cls)
        return instance

    def __contains__(self, item):
        return self._config.__contains__(item)

    @property
    def config(self):
        return self._config

    def _load_config(self, config_name: str, only_update: bool = False):
        try:
            config_base_folder = os.environ[Schalter.DEFAULT_ENV_VAR_NAME]
        except KeyError:
            config_base_folder = os.path.expanduser('~/.schalter')
            if not pathlib.Path(config_base_folder).is_dir():
                raise RuntimeError("Cannot determine configuration base location")

        config_file: pathlib.Path = config_base_folder / pathlib.Path(config_name + '.yaml')

        if config_file.is_file():
            logger.info("Loading/appending config from {}".format(str(config_file)))
            self._update(config_file, only_update)

        elif config_file.exists():
            raise FileExistsError("Cannot create empty config with name '{}'."
                                  .format(str(config_file)))

        else:
            config_file.parent.mkdir(parents=True, exist_ok=True)
            yaml = YAML()
            yaml.default_flow_style = False
            yaml.dump({}, config_file)

    def load_config_from_file(self, path_config_doc: pathlib.Path, only_update: bool = False):
        logger.info("Loading/appending config from {}".format(str(path_config_doc)))
        self._update(path_config_doc, only_update)

    def write_config_file(self, path_config: pathlib.Path):
        yaml = YAML()
        yaml.default_flow_style = False
        yaml.dump(self._config, path_config)

    def _update(self, config_file, only_update: bool = False):
        yaml = YAML(typ='safe')  # default, if not specified, is 'rt' (round-trip)
        config_data = yaml.load(config_file)
        self._raw_configs.append((config_file, config_data))
        self._config.update(config_data)

    def set_default(self, param: str, value):
        self.default_values[param] = value
        if param not in self._config:
            self._config[param] = value

    def set_manual(self, param: str, value):
        if param not in self._overrides_manual:
            self._overrides_manual[param] = value
        elif self._overrides_manual[param] != value:
            raise ValueError("Param '{}' already set to a different value.".format(param))
        self._config[param] = value

    def make_call_decorated_function(self, decorated, mapping: {str: (str, typing.Any)}):
        """

        :param decorated: original function to be configured
        :param mapping: keyword args to be configured or mapped to a specific key.
        {LOCAL_NAME (name in func kwargs): (CONFIG_NAME, value if not supplied)}

        :return:
        """
        def call_decorated_function(*args, **kwargs):
            # save all supplied args that are marked as to be configured
            manual_params = set(kwargs.keys()).intersection(mapping.keys())
            for p in manual_params:
                self.set_manual(mapping[p][0], kwargs[p])

            kwargs_to_add = mapping.keys() - kwargs.keys()
            try:
                kwargs.update({k: self.config[mapping[k][0]] for k in kwargs_to_add})
            except KeyError as e:
                raise KeyError("Value missing in configuration: {}.".format(str(e)))
            return decorated(*args, **kwargs)
        return call_decorated_function

    @staticmethod
    def clear():
        Schalter._configurations.clear()

    @staticmethod
    def get_config(name='default'):
        if name not in Schalter._configurations:
            Schalter._configurations[name] = Schalter(name=name)
        return Schalter._configurations[name]

    @staticmethod
    def get(arg):
        return Schalter.get_config().config[arg]

    @staticmethod
    def set(key, value):
        Schalter.get_config().config[key] = value

    @staticmethod
    def load_config(config_name: str, only_update: bool = False):
        Schalter.get_config()._load_config(config_name, only_update)

    @staticmethod
    def write_config(path_config: pathlib.Path):
        if len(Schalter._configurations) > 1:
            raise ValueError("More than one configuration.")
        Schalter.get_config().write_config_file(path_config)

    @staticmethod
    def configure(*args, **kwargs):
        """ Configuring only keyword-only args.

        :param args:
        :param kwargs:
        :return:
        """

        mapping = {}

        def inner_conf(decorated):
            argspec = inspect.getfullargspec(decorated)
            kwonly = set(argspec.kwonlyargs)
            defaults = argspec.kwonlydefaults

            if set(mapping.keys()) > kwonly:
                raise ValueError("Argument to configure not in function keyword-only args.")

            if not mapping:
                if not kwonly:
                    logger.warning('Empty keyword-only arguments.')
                # try to fill in all arguments
                if defaults is None:
                    defaults = {}
                m = {x: (x, defaults.get(x, Schalter.Unset)) for x in kwonly}
            else:
                if defaults is None:
                    defaults = {}
                # for each value to be configured, see if a default is given
                m = {k: (v, defaults.get(k, Schalter.Unset)) for k, v in mapping.items()}

            # Register defaults. Make sure defaults for the same parameter are consistent
            config_obj: Schalter = Schalter.get_config()
            for _, (config_name, default_value) in m.items():
                if default_value is not Schalter.Unset:
                    config_obj.set_default(config_name, default_value)

            # recreate the same mapping. Now all new defaults are set in the configuration
            # and consistent
            m = {k: (v[0], config_obj.config.get(v[0])) for k, v in m.items()}
            return config_obj.make_call_decorated_function(decorated, m)

        # determine if this decorator is used without arguments
        if args and callable(args[0]):
            # mapping is empty and will be interpreted to configure all kwonly args
            return inner_conf(args[0])
        else:
            s = set(args)
            if len(s) != len(args):
                raise ValueError("Doubled values in 'args'.")
            if bool(s.intersection(kwargs.keys())):
                raise ValueError("Value from 'args' in 'kwargs'.")
            if not all(isinstance(x, str) for x in s) or \
                    not all(isinstance(x, str) for x in kwargs.values()):
                raise ValueError("Only strings as config names allowed.")
            mapping.update(kwargs)
            mapping.update({x: x for x in s})

            return inner_conf
