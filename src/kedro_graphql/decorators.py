import os
import importlib
PLUGINS = {}
WORKING_DIR = os.path.dirname(os.path.abspath(__file__))

class NameConflictError(BaseException):
    """Raise for errors in adding plugins do to the same name."""

def gql(name):
    """
    """

    if name in PLUGINS:
        raise NameConflictError(
            f"Plugin name conflict: '{name}'. Double check" \
            " that all plugins have unique names."
        )
    def register_plugin(plugin_class):
        plugin = plugin_class()
        PLUGINS[name] = plugin
        return plugin

    return register_plugin


def import_modules(dir_name):
    direc = os.path.join(WORKING_DIR, dir_name)
    for f in os.listdir(direc):
        path = os.path.join(direc, f)
        if (
            not f.startswith('_')
            and not f.startswith('.')
            and f.endswith('.py')
        ):
            file_name = f[:f.find('.py')]
            module = importlib.import_module(
                f'{dir_name}.{file_name}'
            )

#import_modules("plugins")