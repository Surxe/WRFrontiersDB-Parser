"""
Global configuration singleton
Import and use OPTIONS directly from this module:

    from config import OPTIONS
    
    def my_function():
        print(OPTIONS.export_dir)
"""

class _OptionsProxy:
    """
    Proxy class that holds the actual OPTIONS instance.
    Allows attribute access while deferring initialization.
    """
    def __init__(self):
        self._options = None
    
    def _set(self, options):
        """Internal method to set the OPTIONS instance. Called by run.py."""
        self._options = options
    
    def __getattr__(self, name):
        """Proxy attribute access to the underlying OPTIONS instance."""
        if self._options is None:
            raise RuntimeError(
                "OPTIONS has not been initialized yet. "
                "Make sure run.py has called config.set_options() before using OPTIONS."
            )
        return getattr(self._options, name)
    
    def __setattr__(self, name, value):
        """Handle setting attributes."""
        if name == '_options':
            # Allow setting the internal _options attribute
            object.__setattr__(self, name, value)
        else:
            # Proxy other attribute sets to the underlying OPTIONS
            if self._options is None:
                raise RuntimeError("OPTIONS has not been initialized yet.")
            setattr(self._options, name, value)
    
    def __bool__(self):
        """Allow truthiness checks like 'if OPTIONS:'"""
        return self._options is not None
    
    def __repr__(self):
        if self._options is None:
            return "<OPTIONS: Not initialized>"
        return repr(self._options)

# Create the singleton instance, import this
OPTIONS = _OptionsProxy()

def set_options(options):
    """
    Set the global OPTIONS instance.
    Should only be called once by run.py during initialization.
    
    Args:
        options: The Options instance from init_options()
    """
    OPTIONS._set(options)