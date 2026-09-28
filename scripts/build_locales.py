"""Build complete static translations from the current English page; reject missing copy."""
from pathlib import Path
from html.parser import HTMLParser
from html import escape
import json, re

PROJECT = Path(__file__).resolve().parent.parent
ROOT = PROJECT / 'dist'
INVARIANT = set(json.loads((PROJECT / 'locales/invariant-text.json').read_text(encoding='utf-8')))
TEXT_ATTRIBUTES = {'alt', 'aria-label', 'data-label-open', 'data-label-closed', 'data-aria-open', 'data-aria-closed', 'data-copy-success', 'data-copy-error'}
VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'}

class Localizer(HTMLParser):
    def __init__(self, locale):
        super().__init__(convert_charrefs=True)
        self.locale = locale
        self.copy = json.loads((PROJECT / f'locales/{locale}.json').read_text(encoding='utf-8'))
        self.output, self.stack, self.missing = [], [], set()

    def translate(self, text):
        if not text or not text.strip(): return text
        match = re.fullmatch(r'(\s*)(.*?)(\s*)', text, re.S)
        before, key, after = match.groups()
        if key in self.copy: return before + self.copy[key] + after
        if key in INVARIANT: return text
        self.missing.add(key)
        return text

    def start(self, tag, attrs, closed=False):
        a = dict(attrs)
        exempt = bool(self.stack and self.stack[-1][1]) or 'data-language-link' in a or tag in {'script', 'style'}
        if tag == 'html': a.update(lang=self.locale, dir='rtl' if self.locale == 'ar' else 'ltr')
        if not exempt:
            for key in TEXT_ATTRIBUTES & a.keys(): a[key] = self.translate(a[key])
        if tag == 'meta':
            if a.get('name') == 'description' or a.get('property') in {'og:title', 'og:description', 'og:image:alt'}:
                a['content'] = self.translate(a['content'])
            if a.get('property') == 'og:url': a['content'] = f'https://bilalaseel.pages.dev/{self.locale}/'
        if tag == 'link' and a.get('rel') == 'canonical': a['href'] = f'https://bilalaseel.pages.dev/{self.locale}/'
        if 'data-language-link' in a:
            a.pop('aria-current', None)
            if a['data-language-link'] == self.locale: a['aria-current'] = 'page'
        rendered = ''.join(' ' + key + ('' if val is None else '="' + escape(val, quote=True) + '"') for key, val in a.items())
        self.output.append('<' + tag + rendered + ('/>' if closed else '>'))
        if not closed and tag not in VOID: self.stack.append((tag, exempt))

    def handle_starttag(self, tag, attrs): self.start(tag, attrs)
    def handle_startendtag(self, tag, attrs): self.start(tag, attrs, True)
    def handle_endtag(self, tag):
        assert self.stack and self.stack[-1][0] == tag, (tag, self.stack[-1:])
        self.stack.pop()
        self.output.append('</' + tag + '>')
    def handle_data(self, data):
        exempt = self.stack and self.stack[-1][1]
        self.output.append(escape(data if exempt else self.translate(data), quote=False))
    def handle_decl(self, decl): self.output.append('<!' + decl + '>')
    def handle_comment(self, text): self.output.append('<!--' + text + '-->')

source = (ROOT / 'index.html').read_text(encoding='utf-8')
for locale in ('sv', 'ar'):
    parser = Localizer(locale)
    parser.feed(source)
    assert not parser.stack
    if parser.missing: raise ValueError(f'{locale}: missing translations: {sorted(parser.missing)}')
    result = ''.join(parser.output)
    if locale == 'sv': result = result.replace('Professionell <span>erfarenhet</span>', 'Yrkes<span>erfarenhet</span>')
    target = ROOT / locale / 'index.html'
    target.parent.mkdir(exist_ok=True)
    target.write_text(result, encoding='utf-8')
    print(f'{locale}: complete static page generated ({len(parser.copy)} translations)')
