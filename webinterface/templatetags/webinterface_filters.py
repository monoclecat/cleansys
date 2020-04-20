from django import template
from django.template.defaultfilters import stringfilter

register = template.Library()


@register.filter(is_safe=True)
@stringfilter
def truncatechars_noellipses(value, arg):
    """Truncate a string after `arg` number of characters."""
    try:
        length = int(arg)
    except ValueError:  # Invalid literal for int().
        return value  # Fail silently.
    return value[:length]


@register.filter(is_safe=True)
@stringfilter
def as_absolute_url(value, arg):
    """Add scheme and host to url, needs the request as an argument"""
    if hasattr(arg, 'scheme') and hasattr(arg, 'get_host'):
        return "{}://{}{}".format(arg.scheme, arg.get_host(), value)
    return
