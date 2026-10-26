def invitation(name=''):
    """A small, optional invitation in AJAR's voice."""
    if not isinstance(name, str):
        raise TypeError('name must be text')
    return (name.strip() + '님, ' if name.strip() else '') + '편할 때 들러주세요. 함께해도, 쉬어가도 좋아요.'
