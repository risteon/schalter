#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""

"""

import os
import logging
import pathlib
import inspect
import typing
from contextlib import ContextDecorator
from decorator import decorate
from ruamel.yaml import YAML

from .config_scope import ConfigScope

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
formatter = logging.Formatter(
    fmt="%(asctime)s - %(levelname)s - %(module)s - %(message)s"
)
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
        return cls._getitem(arg)

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
            raise ValueError(
                "Param '{}' already set to a different default value.".format(key)
            )


class Schalter(object, metaclass=_SchalterMeta):

    DEFAULT_ENV_VAR_NAME = "SCHALTER_CONFIG_LOC"
    _configurations = {}
    Unset = object()
    _scope = ConfigScope()

    def __init__(self, name="default"):
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

    def _load_config(
        self, config_name: str, only_update: bool = False, env_var_name: str = None
    ):
        try:
            env_var_name = (
                env_var_name
                if env_var_name is not None
                else Schalter.DEFAULT_ENV_VAR_NAME
            )
            config_base_folder = os.environ[env_var_name]
        except KeyError:
            config_base_folder = os.path.expanduser("~/.schalter")
            if not pathlib.Path(config_base_folder).is_dir():
                raise RuntimeError("Cannot determine configuration base location")

        if not config_name.endswith(".yaml"):
            config_name += ".yaml"

        config_file: pathlib.Path = config_base_folder / pathlib.Path(config_name)

        if config_file.is_file():
            logger.info("Loading/appending config from {}".format(str(config_file)))
            self._update(config_file, only_update)

        elif config_file.exists():
            raise FileExistsError(
                "Cannot create empty config with name '{}'.".format(str(config_file))
            )

        else:
            raise FileNotFoundError(
                "Cannot find config file '{}'.".format(str(config_file))
            )

    def set_config(self, config: str):
        """
        Example string: "{some_key: True, another_key: 4}"
        """
        logger.info("Loading/appending config string {}".format(config))
        yaml = YAML(typ="safe")
        config_data = yaml.load(config)
        self._raw_configs.append(("<str>", config_data))
        self._config.update(config_data)

    def load_config_from_file(
        self, path_config: pathlib.Path, only_update: bool = False
    ):
        logger.info("Loading/appending config from {}".format(str(path_config)))
        self._update(path_config, only_update)

    def write_config_file(self, path_config: pathlib.Path):
        yaml = YAML()
        yaml.default_flow_style = False
        yaml.dump(self._config, path_config)

    def _update(self, config_file, only_update: bool = False):
        if only_update:
            raise NotImplementedError()

        yaml = YAML(typ="safe")  # default, if not specified, is 'rt' (round-trip)
        config_data = yaml.load(config_file)
        self._raw_configs.append((config_file, config_data))
        self._config.update(config_data)

    def set_default(self, param: str, value):
        self.default_values[param] = value
        if param not in self._config:
            self._config[param] = value

    def set_manual(self, param: str, value):
        self._config[param] = value

    def make_call_decorated_function(self, mapping: {str: (str, typing.Any, bool)}):
        """

        :param mapping: keyword args to be configured or mapped to a specific key.
        {LOCAL_NAME (name in func kwargs):
            (CONFIG_NAME, value if not supplied, is_scoped)}

        :return:
        """

        def call_decorated_function(f, *args, **kw):
            # save all supplied args that are marked as to be configured
            # this first line also contains default values
            manual_params = set(kw.keys()).intersection(mapping.keys())
            # filter out all params that are actually default values
            if f.__kwdefaults__ is not None:
                supplied_by_default = set(
                    p
                    for p in manual_params
                    if (p in f.__kwdefaults__ and kw[p] is f.__kwdefaults__[p])
                )
            else:
                supplied_by_default = set()

            manual_params = manual_params - supplied_by_default

            current_scope = self._scope.fullname
            scoped_mapping = {
                k: (current_scope + "/" + v[0] if v[2] else v[0], v[1])
                for k, v in mapping.items()
            }

            for p in manual_params:
                self.set_manual(scoped_mapping[p][0], kw[p])

            kwargs_to_add = mapping.keys() - manual_params
            try:
                kw.update({k: self.config[scoped_mapping[k][0]] for k in kwargs_to_add})
            except KeyError as e:
                raise KeyError("Value missing in configuration: {}.".format(str(e)))

            # replace defaults with actual value if:
            # * key is configured (== in mapping)
            # * key has a function default value (== in __kwdefaults__)
            # * value IS the actual function default value (not user supplied)
            if f.__kwdefaults__ is not None:
                default_values = {
                    k: v.value
                    for k, v in kw.items()
                    if k in mapping
                    and k in f.__kwdefaults__
                    and v is f.__kwdefaults__[k]
                }
                kw.update(default_values)
            return f(*args, **kw)

        return call_decorated_function

    @staticmethod
    def clear():
        Schalter._configurations.clear()

    @staticmethod
    def get_config(name="default"):
        if name not in Schalter._configurations:
            Schalter._configurations[name] = Schalter(name=name)
        return Schalter._configurations[name]

    @staticmethod
    def get(*args, **kw):
        return Schalter.get_config().config.get(*args, **kw)

    @staticmethod
    def _getitem(item):
        return Schalter.get_config().config[item]

    @staticmethod
    def set(key, value):
        Schalter.get_config().config[key] = value

    @staticmethod
    def load_config(
        config_name: str, only_update: bool = False, env_var_name: str = None
    ):
        Schalter.get_config()._load_config(config_name, only_update, env_var_name)

    @staticmethod
    def load_config_from_file_default(
        path_config: pathlib.Path, only_update: bool = False
    ):
        Schalter.get_config().load_config_from_file(path_config, only_update)

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

    def _decorate_function_with_mapping(self, f, m, force_update: bool = False):

        try:
            # try to update the mapping of an already decorated function
            mapping = f.schalter_mapping

            if force_update:
                mapping.update(m)
            else:

                updates = {
                    k for k in mapping.keys() & m.keys() if mapping[k][0] != m[k][0]
                }
                for k in updates:
                    # introduce a strict mode where this raises an error?
                    msg = (
                        "Replacing original mapping of argument '{}' "
                        "to config entry '{}' with new mapping to '{}'.".format(
                            k, m[k][0], mapping[k][0]
                        )
                    )
                    logger.warning("Function '{}': {}".format(f.__name__, msg))

                mapping.update({k: v for k, v in m.items() if k not in updates})

            f.schalter_f.__kwdefaults__ = f.__kwdefaults__
        except AttributeError:
            # first decoration of function. Save mapping and original function
            setattr(f, "schalter_mapping", m)

            decorated = decorate(f, self.make_call_decorated_function(m))
            setattr(decorated, "schalter_f", f)
            f = decorated

        try:
            if id(f.schalter_config) != id(self):
                raise NotImplementedError()
        except AttributeError:
            setattr(f, "schalter_config", self)

        return f

    @staticmethod
    def _make_decorator(
        mapping: typing.Union[typing.Dict[str, typing.Tuple[str, bool]], bool]
    ):
        """

        :param mapping: LOCAL_NAME -> (CONFIG_NAME, is_scoped)
        :return:
        """

        def _decorator(f):
            argspec = inspect.getfullargspec(f)
            kwonly = set(argspec.kwonlyargs)
            defaults = argspec.kwonlydefaults

            if not kwonly:
                logger.warning("Empty keyword-only arguments.")

            if isinstance(mapping, bool):
                # try to fill in all arguments
                if defaults is None:
                    defaults = {}
                m = {x: (x, defaults.get(x, Schalter.Unset), mapping) for x in kwonly}
            else:
                if set(mapping.keys()) > kwonly:
                    raise ValueError(
                        "Argument to configure not in function keyword-only args."
                    )

                if defaults is None:
                    defaults = {}
                # for each value to be configured, see if a default is given
                m = {
                    k: (v[0], defaults.get(k, Schalter.Unset), v[1])
                    for k, v in mapping.items()
                }

            # replace original function defaults with proxy objects
            # -> enables to check later if a param was supplied or a default used
            if m and f.__kwdefaults__ is None:
                f.__kwdefaults__ = {}
            if f.__kwdefaults__ is not None:
                for k, (_, v, _) in m.items():
                    if v is not Schalter.Unset:
                        f.__kwdefaults__[k] = Schalter.Default(v)
                    else:
                        f.__kwdefaults__[k] = Schalter.Unset

            # Register defaults.
            # Make sure defaults for the same parameter are consistent
            config_obj: Schalter = Schalter.get_config()
            for _, (config_name, default_value, _is_scoped) in m.items():
                if default_value is not Schalter.Unset:
                    config_obj.set_default(config_name, default_value)

            # recreate the same mapping.
            # Now all new defaults are set in the configuration
            # and consistent
            m = {
                k: (v[0], config_obj.config.get(v[0], Schalter.Unset), v[2])
                for k, v in m.items()
            }

            return config_obj._decorate_function_with_mapping(f, m)

        return _decorator

    @staticmethod
    def prefix(prefix: str):
        def _decorator(f):
            try:
                c: Schalter = f.schalter_config
                m = f.schalter_mapping
                f = f.schalter_f

                # no prefix with configured function defaults allowed
                defaults = inspect.getfullargspec(f).kwonlydefaults
                if defaults is not None:
                    if any(type(defaults[k]) == Schalter.Default for k in m.keys()):
                        raise NotImplementedError()

            except AttributeError:
                logger.warning("Prefix without any configurations.")
                return f

            # add prefix to mapping and re-decorate (update mapping)
            m = {k: (prefix + "/" + v[0], v[1], v[2]) for k, v in m.items()}
            return c._decorate_function_with_mapping(f, m, force_update=True)

        return _decorator

    @staticmethod
    def configure(*decorator_args, **decorator_kwargs):
        """ Configuring only keyword-only args.
        This is a decorator factory.

        :param decorator_args:
        :param decorator_kwargs:
        :return:
        """
        # determine if this decorator is used without arguments
        if decorator_args and callable(decorator_args[0]):
            # mapping is empty and will be interpreted to configure all kwonly args
            return Schalter._make_decorator(False)(decorator_args[0])
        else:
            s = set(decorator_args)
            if len(s) != len(decorator_args):
                raise ValueError("Doubled values in 'args'.")
            if bool(s.intersection(decorator_kwargs.keys())):
                raise ValueError("Value from 'args' in 'kwargs'.")
            if not all(isinstance(x, str) for x in s) or not all(
                isinstance(x, str) for x in decorator_kwargs.values()
            ):
                raise ValueError("Only strings as config names allowed.")
            mapping = {k: (v, False) for k, v in decorator_kwargs.items()}
            mapping.update({x: (x, False) for x in s})
            if not mapping:
                mapping = False
            # return caller
            return Schalter._make_decorator(mapping)

    @staticmethod
    def scoped_configure(*decorator_args, **decorator_kwargs):
        """ Configuring only keyword-only args.
                This is a decorator factory.

                :param decorator_args:
                :param decorator_kwargs:
                :return:
                """
        # determine if this decorator is used without arguments
        if decorator_args and callable(decorator_args[0]):
            # mapping is empty and will be interpreted to configure all kwonly args
            return Schalter._make_decorator(True)(decorator_args[0])
        else:
            s = set(decorator_args)
            if len(s) != len(decorator_args):
                raise ValueError("Doubled values in 'args'.")
            if bool(s.intersection(decorator_kwargs.keys())):
                raise ValueError("Value from 'args' in 'kwargs'.")
            if not all(isinstance(x, str) for x in s) or not all(
                isinstance(x, str) for x in decorator_kwargs.values()
            ):
                raise ValueError("Only strings as config names allowed.")
            mapping = {k: (v, False) for k, v in decorator_kwargs.items()}
            mapping.update({x: (x, False) for x in s})
            if not mapping:
                mapping = True
            # return caller
            return Schalter._make_decorator(mapping)

    class Scope(ContextDecorator):
        def __init__(self, name: str):
            self.name = name

        def __enter__(self) -> ConfigScope:
            return Schalter._scope.make_scope(self.name)

        def __exit__(self, exc_type, exc, exc_tb):
            Schalter._scope.release_scope()
