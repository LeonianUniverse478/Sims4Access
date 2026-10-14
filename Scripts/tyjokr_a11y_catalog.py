"""The Buy catalog as a tree of pickers, and catalog search (Build mode).

Ctrl+Alt+O opens the tree: Search the catalog, By room, By function. A room or
function lists the Buy panel's own subcategories (tyjokr_a11y_catalogtree, made
from EA's BuildBuyNavigation movie), and a subcategory lists its items with
price and colours. Enter on an item picks it up exactly as clicking it in the
catalog does, so the Build cursor (Ctrl+Alt+B) places it as usual. Escape goes
back up one level. Ctrl+Alt+D goes straight to search.

Every level is a native picker, so the picker owns the keyboard: Build mode's
own hotkeys never see the keys pressed in it. Item lists and selection use the
TS4 Access Plus catalog bridge in TooltipManager (A11yCatalogBrowse for lists
and searches, A11yPlusSelect to pick up), and its replies (a11yplus.flash).
"""
import threading
from urllib.parse import quote

import tyjokr_a11y_catalogtree as tree

_TAG = 'catalogtree'
_TIMEOUT = 5.0
_HINT = 'Press Ctrl+Alt+B to place it with the Build cursor, or Ctrl+Alt+O to choose something else.'


def _core():
    import tyjokr_a11y_plus_core as core
    return core


def _build():
    import tyjokr_a11y_plus_build as build
    return build


def _label(key):
    import tyjokr_a11y_menu as menu
    return menu._ls_hash(key)


def _ready():
    """In Build mode with an active Sim; otherwise says why not."""
    core = _core()
    if not _build().in_build_mode():
        core.speak('Open Build mode first with F2, then press Ctrl+Alt+O.')
        return False
    return True


def open_tree():
    if not _ready():
        return False
    rows = [('Search the catalog', 'Type a word, such as bed or fridge, and choose from what matches.', ('find',)),
            ('By room', 'Kitchen, bathroom, bedroom and other rooms, then what goes in them.', ('group', 'room')),
            ('By function', 'Comfort, surfaces, plumbing, lighting and other kinds of object.', ('group', 'function'))]

    def picked(value):
        if value[0] == 'find':
            find()
        else:
            _groups(value[1])
    return _core().choose('Catalog', 'Choose how to look, or search. Escape closes.', rows, picked, tag=_TAG)


def _groups(kind):
    groups = tree.ROOMS if kind == 'room' else tree.FUNCTIONS
    rows = [(_label(label), None, i) for (i, (label, _subs)) in enumerate(groups)]
    _core().choose('By room' if kind == 'room' else 'By function', 'Choose one. Escape goes back.', rows,
                   lambda i: _subcategories(kind, i), tag=_TAG, on_cancel=open_tree)


def _subcategories(kind, index):
    (label, subs) = (tree.ROOMS if kind == 'room' else tree.FUNCTIONS)[index]
    rows = [(_label(sub[0]), None, j) for (j, sub) in enumerate(subs)]
    _core().choose(_label(label), 'Choose a kind of item. Escape goes back.', rows,
                   lambda j: _browse(subs[j], back=lambda: _subcategories(kind, index)),
                   tag=_TAG, on_cancel=lambda: _groups(kind))


class _Arrived(object):
    """The Plus reply handler calls set() when a list has fully arrived."""

    def __init__(self, on_done):
        self.on_done = on_done
        self.done = False

    def set(self):
        if not self.done:
            self.done = True
            _core().post(self.on_done)


def _request(product_type, tags, priority, search, on_done):
    """Ask the bridge for a list; on_done(items) on the game thread."""
    build = _build()
    build._cat['serial'] += 1
    serial = build._cat['serial']
    arrived = _Arrived(lambda: on_done(list(build._cat['items'])))
    build._cat.update(items=[], total=0, name='', next='tree', quiet=arrived)
    build._send_ui('A11y|plus|browse|{}|{}|{}|{}|{}'.format(product_type, tags, priority, serial, quote(search, safe='')))

    def timeout():
        if not arrived.done and build._cat['serial'] == serial:
            arrived.done = True
            _core().speak('The catalog did not answer. Open Build mode with F2 and try again.')
    threading.Timer(_TIMEOUT, lambda: _core().post(timeout)).start()


def _browse(sub, back):
    (label, product_type, tags, priority) = sub

    def arrived(items):
        if not items:
            _core().speak('There is nothing here in your game.')
            back()
            return
        _items(_label(label), items, back)
    _core().speak('Loading.')
    _request(product_type, tags, priority, '', arrived)


def _describe(price, colours):
    text = '{:,} simoleons'.format(price)
    if colours > 1:
        text += ', {} colours'.format(colours)
    return text


def _items(title, items, back):
    rows = [(name, _describe(price, colours), i) for (i, (name, price, colours)) in enumerate(items)]
    _core().choose(title, '{} items. Enter picks one up to place. Escape goes back.'.format(len(items)), rows,
                   _pick, tag=_TAG, on_cancel=back)


def _pick(index):
    build = _build()
    build._NEXT_HINT['tree'] = _HINT
    build._cat['next'] = 'tree'
    build._cat['chosen'] = index
    build._send_ui('A11y|plus|select|{}'.format(index))


def find():
    if not _ready():
        return False

    def typed(text):
        text = (text or '').strip()
        if not text:
            open_tree()
            return
        search(text)
    return _core().ask_text('Search the catalog', 'Type what you are looking for, for example bed, fridge or lamp.', '', typed)


def search(text):
    def arrived(items):
        if not items:
            _core().speak('Nothing found for {}. Try another word.'.format(text))
            find()
            return
        _items('Results for {}'.format(text), items, open_tree)
    _core().speak('Searching.')
    _request(2, '', '', text, arrived)
