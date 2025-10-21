class DataSetConfigError(Exception):
    """``DataSetConfigError`` raised by ``DataSetConfigError`` implementations
    in case of failure.
    ``DataSetConfigError`` implementations should provide instructive
    information in case of failure.
    """

    pass


class DataSetError(Exception):
    """``DataSetError`` raised by ``DataSetError`` implementations
    in case of failure.
    ``DataSetError`` implementations should provide instructive
    information in case of failure.
    """

    pass
