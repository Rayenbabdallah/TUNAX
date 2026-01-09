"""Resources package initialization for Flask-Smorest blueprints.

Avoid importing submodules here to prevent circular imports when modules
import the package. Blueprints are imported directly in app.py as needed.
"""

__all__ = []
