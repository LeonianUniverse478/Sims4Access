"""Click a button the game draws and the mod cannot reach.

    python click_text.py Done          find "Done", say where, click on Enter
    python click_text.py Done --go     click without asking
    python click_text.py --look        read the screen, click nothing

Some client panels answer to nothing the simulation can send. The age-up screen
is the clearest case: the mod answers its dialog server-side and the game
applies the age-up, but the panel itself stays on screen, exactly as the map
screen does. Responding, the client's own close request and a synthesized
Escape have all been tried on that class of panel and all ignored.

What those panels do have is a button with a WORD on it. So this finds the word
and clicks it, which is the one route left.

Matching is fuzzy, because Windows OCR reads Documents as Docurnents, and it
says out loud what it found before touching anything.
"""
import sys
import time

import companion


def main(argv):
    words_wanted = [a for a in argv if not a.startswith('--')]
    speaking = companion.start_speech()
    if not speaking:
        print('(no screen reader found through Prism - printing only)')

    words, error = companion.read_screen()
    if error:
        companion.say('Could not read the screen: {}'.format(error))
        return 1
    if companion.last_source != 'the game window':
        companion.say('Reading {} - the game window was not found.'.format(
            companion.last_source))

    if '--look' in argv or not words_wanted:
        lines = []
        for word in words:
            line = word.get('line') or word.get('text')
            if line and line not in lines:
                lines.append(line)
        companion.say('{} lines on screen:'.format(len(lines)))
        for line in lines:
            companion.say('  {}'.format(line))
        return 0

    target = ' '.join(words_wanted)
    hit = companion.find_text(words, target)
    if hit is None:
        companion.say('No "{}" on screen. I read {} words. Run with --look to '
                      'hear them.'.format(target, len(words)))
        return 1

    x, y, seen = hit
    companion.say('{} found at {}, {}{}.'.format(
        target, x, y,
        ', read as "{}"'.format(seen) if seen.lower() != target.lower() else ''))

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
    companion.say('Clicked {}.'.format(target))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
