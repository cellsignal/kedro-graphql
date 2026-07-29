class DataSetConfigError(Exception):
    """``DataSetConfigError`` raised when dataset configuration is invalid or cannot be parsed. 
    """

    pass


class DataSetError(Exception):
    """``DataSetError`` raised when dataset operations fail.
    """

    pass


class InvalidPipeline(Exception):
    """Raised when a pipeline cannot be staged or executed safely."""

    pass
