"""Preserve reviewed UI Cheats right-click quantity behavior in the cart.

Generate from the shared accessible cell; never change the standard class.
UI Cheats v1.59.1 uses MouseEvent.CLICK and ten native quantity calls on
right-click. The normal one-item path and all accessibility hooks remain.
"""
from pathlib import Path
import sys


def prepare(source):
    event = 'PushButtonEvent.CLICK'
    if source.count(event) != 6:
        raise ValueError('Purchase click listener shape changed; review required')
    source = source.replace('import olympus.events.PushButtonEvent;', 'import olympus.utils.InputUtils;')
    source = source.replace(event, 'MouseEvent.CLICK')
    for direction in ('Increase', 'Decrease'):
        old = ('protected function On%sClick(param1:PushButtonEvent) : void\n'
               '      {\n         this.%sAmount();\n      }') % (direction, direction)
        calls = '\n'.join('            this.%sAmount();' % direction for _ in range(10))
        new = ('protected function On%sClick(param1:MouseEvent) : void\n'
               '      {\n         if(InputUtils.IsRightMouseButton(param1))\n'
               '         {\n%s\n         }\n         else\n         {\n'
               '            this.%sAmount();\n         }\n      }') % (direction, calls, direction)
        if source.count(old) != 1:
            raise ValueError('Purchase %s handler changed; review required' % direction)
        source = source.replace(old, new)
    return source


if __name__ == '__main__':
    source = Path(__file__).resolve().parent / 'extra-classes/PurchasePickerCellView.as'
    Path(sys.argv[1]).write_text(prepare(source.read_text(encoding='utf-8-sig')), encoding='utf-8')
