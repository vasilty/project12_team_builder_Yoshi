import markdown2
import bleach

bleach.ALLOWED_TAGS.extend(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'hr',
                            'pre', 'img'])

def markdownify(content):
    attrs = {
        '*': ['class'],
        'a': ['href', 'rel'],
        'img': ['alt', 'src'],
    }
    return bleach.clean(markdown2.markdown(content), attributes=attrs)

