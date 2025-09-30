# Temporary patch for Flask/Jinja2 compatibility issue
import sys
import jinja2

# Provide the missing escape function for older Flask versions
if not hasattr(jinja2, 'escape'):
    from markupsafe import escape
    jinja2.escape = escape

# Provide the missing Markup class
if not hasattr(jinja2, 'Markup'):
    from markupsafe import Markup
    jinja2.Markup = Markup

# Also provide select_autoescape if missing
if not hasattr(jinja2, 'select_autoescape'):
    def select_autoescape(enabled_extensions=('html', 'htm', 'xml'), disabled_extensions=(), default_for_string=True, default=False):
        def _select_autoescape(template_name):
            if template_name is None:
                return default_for_string
            template_name = template_name.lower()
            if any(template_name.endswith('.' + ext) for ext in disabled_extensions):
                return False
            if any(template_name.endswith('.' + ext) for ext in enabled_extensions):
                return True
            return default
        return _select_autoescape
    jinja2.select_autoescape = select_autoescape