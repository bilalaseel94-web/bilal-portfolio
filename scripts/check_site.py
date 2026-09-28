"""Validate the public site and build an explicit allowlist of deployable files.

Standard-library only. Run after build_locales.py. A failed check exits nonzero.
"""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse, unquote
import json
import shutil

PROJECT = Path(__file__).resolve().parent.parent
ROOT = PROJECT / 'dist'
OUTPUT = PROJECT / 'site-build'
VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link',
        'meta', 'param', 'source', 'track', 'wbr'}
SOURCE_URL = 'https://github.com/bilalaseel94-web/bilal-portfolio'
# The owner explicitly approved this one public contact address.
PUBLIC_EMAIL = 'bilal.aseel@hotmail.com'


def require(condition, message):
    if not condition:
        raise ValueError(message)


class PageCheck(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack, self.refs, self.controls, self.language_links = [], [], [], []
        self.ids, self.alternates = set(), set()
        self.document = {}
        self.images = []
        self.source_links = 0

    def handle_starttag(self, tag, pairs):
        attrs = dict(pairs)
        if tag not in VOID:
            self.stack.append(tag)
        if tag == 'html':
            self.document = attrs
        if 'id' in attrs:
            require(attrs['id'] not in self.ids, 'Duplicate HTML id: ' + attrs['id'])
            self.ids.add(attrs['id'])
        for key in ('href', 'src'):
            if attrs.get(key):
                self.refs.append(attrs[key])
        if attrs.get('aria-controls'):
            self.controls.append(attrs['aria-controls'])
        if tag == 'img':
            require(all(attrs.get(k) for k in ('alt', 'width', 'height')), 'Image needs accessible text and dimensions')
            self.images.append(attrs)
        if 'data-language-link' in attrs:
            self.language_links.append(attrs)
        if tag == 'link' and attrs.get('hreflang'):
            self.alternates.add(attrs['hreflang'])
        if 'data-product-trigger' in attrs:
            require(all(attrs.get(k) for k in ('data-label-open', 'data-label-closed')), 'Disclosure labels missing')
        if tag == 'a' and attrs.get('href') == SOURCE_URL:
            self.source_links += 1
            require('noopener' in attrs.get('rel', ''), 'External source link needs noopener')

    def handle_endtag(self, tag):
        require(bool(self.stack) and self.stack[-1] == tag, 'Unbalanced HTML: ' + tag)
        self.stack.pop()


def build_site():
    manifest = json.loads((PROJECT / 'public-files.json').read_text(encoding='utf-8'))
    require(len(manifest) == len(set(manifest)), 'Duplicate manifest entries')
    allowed = set(manifest)
    for name in allowed:
        path = Path(name)
        require(not path.is_absolute() and '..' not in path.parts, 'Unsafe manifest path')
        require(path.suffix.lower() in {'.html', '.css', '.js', '.webp', '.jpg', '.svg'} or name == '_redirects', 'Unsupported public asset')
    actual = {p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*') if p.is_file()}
    require(actual == allowed, 'Public files differ from manifest: ' + str(sorted(actual ^ allowed)))
    require(not any(p.is_symlink() for p in ROOT.rglob('*')), 'Public tree must not contain symlinks')
    for locale, filename in [('en', 'index.html'), ('sv', 'sv/index.html'), ('ar', 'ar/index.html')]:
        html = (ROOT / filename).read_text(encoding='utf-8')
        check = PageCheck()
        check.feed(html)
        require(not check.stack, filename + ': unclosed tags')
        require(check.document.get('lang') == locale, filename + ': wrong language')
        require(check.document.get('dir') == ('rtl' if locale == 'ar' else 'ltr'), filename + ': wrong direction')
        require(check.source_links == 1, filename + ': expected one source link')
        require(check.alternates == {'en', 'sv', 'ar', 'x-default'}, filename + ': language metadata incomplete')
        current = [a['data-language-link'] for a in check.language_links if a.get('aria-current') == 'page']
        require(current == [locale], filename + ': wrong current language')
        require(all(c in check.ids for c in check.controls), filename + ': broken accessible control')
        email_links = [ref for ref in check.refs if ref.lower().startswith('mailto:')]
        require(email_links == ['mailto:' + PUBLIC_EMAIL], filename + ': unexpected email link')
        scrubbed = html.lower().replace('mailto:' + PUBLIC_EMAIL, '').replace(PUBLIC_EMAIL, '')
        require(not any(word in scrubbed for word in ('mailto:', 'hotmail', '+44 7883', 'c:\\users\\')), filename + ': unexpected private information')
        for ref in check.refs:
            url = urlparse(ref)
            if url.scheme or url.netloc:
                continue
            if not url.path:
                require(not url.fragment or url.fragment in check.ids, filename + ': broken anchor ' + ref)
                continue
            path = unquote(url.path).lstrip('/')
            if not path or url.path.endswith('/'):
                path += 'index.html'
            require(path in allowed, filename + ': asset not in manifest ' + ref)
    OUTPUT.mkdir(exist_ok=True)
    existing = {p.relative_to(OUTPUT).as_posix() for p in OUTPUT.rglob('*') if p.is_file()}
    require(existing <= allowed, 'Unexpected file in build output; inspect before deploying')
    for name in sorted(allowed):
        target = OUTPUT / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)
    print(f'PASS: three complete languages; {len(allowed)} allowlisted public files ready in site-build/')


if __name__ == '__main__':
    build_site()
