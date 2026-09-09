"""Start the game from the main menu, without seeing it.

    python start_game.py            find the button, say where it is, ask first
    python start_game.py --go       click it without asking
    python start_game.py --look     read the whole screen aloud, click nothing

The main menu is a client screen: no accessibility tree, no simulation behind
it, nothing for the mod to rebuild from. So this reads it the only way left -
Windows' own OCR - finds the button by its text rather than by a memorised
position, and says what it found before touching anything.

Text-first matters. A fixed coordinate breaks the first time a patch moves a
button by ten pixels, and breaks silently. Matching the word "Continue" still
finds it after it moves, and when the word genuinely is not there, this says so
instead of clicking whatever happens to be at that spot.

Once the game is loading, the mod takes over: it announces itself when the lot
is up, and Ctrl+Alt+W says what to press next.
"""
import sys
import time

import companion

# In the order we would try them. Continue opens whatever a11yscan's save
# picker queued up, which is why it comes first.
BUTTONS = ('Continue', 'Load Game', 'New Game')


def look(words):
    """Everything readable on the menu right now, one line per line of text."""
    lines = []
    for word in words:
        line = word.get('line') or word.get('text')
        if line and line not in lines:
            lines.append(line)
    if not lines:
        companion.say('Nothing readable on screen. Is the game running and '
                      'in front?')
        return 1
    companion.say('{} lines on screen:'.format(len(lines)))
    for line in lines:
        companion.say('  {}'.format(line))
    return 0


def main(argv):
    speaking = companion.start_speech()
    if not speaking:
        print('(no screen reader found through Prism - printing only)')

    words, error = companion.read_screen()
    if error:
        companion.say('Could not read the screen: {}'.format(error))
        return 1
    if companion.last_source != 'the game window':
        companion.say('Reading {} - the game window was not found, so what '
                      'follows may not be the game.'.format(
                          companion.last_source))
    if '--look' in argv:
        return look(words)

    found = None
    for label in BUTTONS:
        hit = companion.find_text(words, label)
        if hit:
            found = (label,) + hit
            break

    if found is None:
        companion.say('No main menu button found. I read {} words but none of '
                      'them were {}. Try --look to hear what is on '
                      'screen.'.format(len(words), ' or '.join(BUTTONS)))
        return 1

    label, x, y, seen = found
    companion.say('{} found at {}, {}{}.'.format(
        label, x, y,
        ', read as "{}"'.format(seen) if seen.lower() != label.lower() else ''))

    if '--go' not in argv:
        try:
            answer = input('Press Enter to click it, or Control C to stop. ')
        except (EOFError, KeyboardInterrupt):
            companion.say('Stopped. Nothing was clicked.')
            return 1
        if answer.strip().lower() in ('n', 'no', 'q', 'quit'):
            companion.say('Stopped. Nothing was clicked.')
            return 1

    companion.focus_game()
    time.sleep(0.3)
    if not companion.click(x, y):
        companion.say('Windows refused the click.')
        return 1
    companion.say('Clicked {}. The game is loading. When the lot is up the '
                  'scanner says so; press Control Alt W if it does '
                  'not.'.format(label))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
