#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import logging
import pathlib
import inspect
import typing
from decorator import decorate
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
        # Todo currently unused
        # if param not in self._overrides_manual:
        #     self._overrides_manual[param] = value
        # elif self._overrides_manual[param] != value:
        #     raise ValueError("Param '{}' already set to a different value.".format(param))
        self._config[param] = value

    def make_call_decorated_function(self, mapping: {str: (str, typing.Any)}):
        """

        :param decorated: original function to be configured
        :param mapping: keyword args to be configured or mapped to a specific key.
        {LOCAL_NAME (name in func kwargs): (CONFIG_NAME, value if not supplied)}

        :return:
        """
        def call_decorated_function(f, *args, **kw):
            # save all supplied args that are marked as to be configured
            # this first line also contains default values
            manual_params = set(kw.keys()).intersection(mapping.keys())
            # filter out all params that are actually default values
            if f.__kwdefaults__ is not None:
                supplied_by_default = set(p for p in manual_params
                                          if (p in f.__kwdefaults__
                                              and kw[p] is f.__kwdefaults__[p]))
            else:
                supplied_by_default = set()

            manual_params = manual_params - supplied_by_default
            for p in manual_params:
                self.set_manual(mapping[p][0], kw[p])

            kwargs_to_add = mapping.keys() - manual_params
            try:
                kw.update({k: self.config[mapping[k][0]] for k in kwargs_to_add})
            except KeyError as e:
                raise KeyError("Value missing in configuration: {}.".format(str(e)))

            # replace defaults with actual value if:
            # * key is configured (== in mapping)
            # * key has a function default value (== in __kwdefaults__)
            # * value IS the actual function default value (not user supplied)
            if f.__kwdefaults__ is not None:
                default_values = {k: v.value for k, v in kw.items()
                                  if k in mapping and k in f.__kwdefaults__ and
                                  v is f.__kwdefaults__[k]}
                kw.update(default_values)

            return f(*args, **kw)
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

    class Default:
        def __repr__(self):
            return "Default Value: {} ({})".format(self.value, type(self.value))

        def __init__(self, value):
            self.value = value

    @staticmethod
    def configure(*decorator_args, **decorator_kwargs):
        """ Configuring only keyword-only args.
        This is a decorator factory.

        :param decorator_args:
        :param decorator_kwargs:
        :return:
        """

        mapping = {}

        # create actual decorator
        def _decorator(f):
            argspec = inspect.getfullargspec(f)
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

            # replace original function defaults with proxy objects
            # -> enables to check later if a param was supplied or a default used
            if m and f.__kwdefaults__ is None:
                f.__kwdefaults__ = {}
            if f.__kwdefaults__ is not None:
                for k, (_, v) in m.items():
                    if v is not Schalter.Unset:
                        f.__kwdefaults__[k] = Schalter.Default(v)
                    else:
                        f.__kwdefaults__[k] = Schalter.Unset

            # Register defaults. Make sure defaults for the same parameter are consistent
            config_obj: Schalter = Schalter.get_config()
            for _, (config_name, default_value) in m.items():
                if default_value is not Schalter.Unset:
                    config_obj.set_default(config_name, default_value)

            # recreate the same mapping. Now all new defaults are set in the configuration
            # and consistent
            m = {k: (v[0], config_obj.config.get(v[0], Schalter.Unset)) for k, v in m.items()}
            return decorate(f, config_obj.make_call_decorated_function(m))

        # determine if this decorator is used without arguments
        if decorator_args and callable(decorator_args[0]):
            # mapping is empty and will be interpreted to configure all kwonly args
            return _decorator(decorator_args[0])
        else:
            s = set(decorator_args)
            if len(s) != len(decorator_args):
                raise ValueError("Doubled values in 'args'.")
            if bool(s.intersection(decorator_kwargs.keys())):
                raise ValueError("Value from 'args' in 'kwargs'.")
            if not all(isinstance(x, str) for x in s) or \
                    not all(isinstance(x, str) for x in decorator_kwargs.values()):
                raise ValueError("Only strings as config names allowed.")
            mapping.update(decorator_kwargs)
            mapping.update({x: x for x in s})

            # return caller
            return _decorator
