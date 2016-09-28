import markdown2
import bleach


bleach.ALLOWED_TAGS.extend(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'hr',
                            'pre', 'img'])


def markdownify(content):
    """Apply Markdown rendering to the text content."""
    attrs = {
        '*': ['class'],
        'a': ['href', 'rel'],
        'img': ['alt', 'src'],
    }
    return bleach.clean(markdown2.markdown(content), attributes=attrs)


def make_url(**kwargs):
    """Makes GET query to search by whatever kwargs are passed."""
    alls = ['all needs', 'all applications', 'all projects']
    url = ''
    for key, value in kwargs.items():
        if value and value not in alls:
            value = value.lower()
            if not url:
                url += '?'
            else:
                url += '&'
            url += key + '=' + value
    return url
