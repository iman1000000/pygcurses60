import pygame
from pygame.locals import *

# TODO - need to profile how pygame renders full string compared to rendering individual chars.

"""
# BUGS:
1 - need to fill entire field before drawing the color
2 - each cell needs its own fg/bg color and font info.
3 - handle shift keys and characters not in the font
4 - need to add "dirty bits" so that we don't update things that don't need to be updated.
5 - don't shift until we try to write on the row after the end of the screen
"""


"""
The point of using this is that Windows does not have a curses module built in, and it is not code-compatible with Linux curses.

FEATURES:
1) Variable sized cwindow with width/height.
2) Variable sized fonts.
3) Foreground/background color.
4) Supports tabs and newlines.
5) Supports autowrapping with print()
6) Supports setting the cursor at a certain point.
7) Supports multiple fonts (for wingdings)
8) Can work as a base for extensions (menus, borders, etc)
9) Follows the API of the curses library as close as possible
10) Supports stdout and stdin file object actions

DOES NOT SUPPORT:
unicode (well, this actually depends on Pygame's support of unicode)
sprite transformation/cropping/scaling
squares of different sizes in the same view.
Font transformation.
Drawing primitives (you can't draw a line of blocks or something such as that).

mapping sprites to characters and then printing them.

don't support input() for now.
"""

class PygCurseWindow():
    def __init__(self, display=None, width=80, height=25, font=None, fgcolor=pygame.Color(192, 192, 192), bgcolor=pygame.Color(0, 0, 0)):
        self._cursorx = 0
        self._cursory = 0
        self._width = width
        self._height = height
        self._screen = [[None] * height for i in range(width)]
        if font is None:
            self._font = pygame.sysfont.SysFont('freesansbold', 24, fgcolor)
        else:
            self._font = font
        self._fgcolor = fgcolor
        self._bgcolor = bgcolor

        self._charwidth, self._charheight = calcfontsize(self._font) # TODO - needs improvements

        self._surfobj = pygame.Surface((self._width * self._charwidth, self._height * self._charheight))
        self._rectobj = self._surfobj.get_rect()

        self._allownonmonofonts = False # TODO
        self._autoupdate = (display is not None) and True or False
        self._displaysurf = display
        self._tabsize = 8 # TODO - need to implement tabs


    def print(self, obj, *objs, sep=' ', end='\n', font=None, fgcolor=None, bgcolor=None):
        # not thread safe
        print(objs)
        if fgcolor is not None:
            oldfgcolor = self._fgcolor
            self._fgcolor = fgcolor
        if bgcolor is not None:
            oldbgcolor = self._bgcolor
            self._bgcolor = bgcolor
        if font is not None:
            oldfont = self._font
            self._font = font

        text = [str(obj)]
        text.append(str(sep).join([str(x) for x in objs]))
        text.append(str(end))

        print('Writing: %s' % (''.join(text)))
        self.write(''.join(text))

        if fgcolor is not None:
            self._fgcolor = oldfgcolor
        if bgcolor is not None:
            self._bgcolor = oldbgcolor
        if font is not None:
            self._font = oldfont

        print(self._debugscreen())

    def update(self):
        for x in range(self._width):
            for y in range(self._height):
                if self._screen[x][y] is not None:
                    r = pygame.Rect(self._charwidth * x, self._charheight * y, self._charwidth, self._charheight)
                    self._surfobj.fill(self._bgcolor, r)
                    charsurf = self._font.render(self._screen[x][y], 1, self._fgcolor, self._bgcolor)
                    charrect = charsurf.get_rect()
                    charrect.centerx = self._charwidth * x + int(self._charwidth / 2)
                    charrect.bottom = self._charheight * (y+1)
                    self._surfobj.blit(charsurf, charrect)
        if self._displaysurf is not None:
            self._displaysurf.blit(self._surfobj, self._surfobj.get_rect())
            pygame.display.update()


    def _debugscreen(self):
        text = ''
        for y in range(self._height):
            for x in range(self._width):
                if self._screen[x][y] is None:
                    text += ' '
                else:
                    text += self._screen[x][y]
            text += '\n'
        return text


    def getlocationatpixel(self, pixelx, pixely):
        return (None, None) # if pixel coordinates are outside of the window


    def getrect(self, x=None, y=None, width=None, height=None):
        x, y, width, height = self._constrainsize(x, y, width, height)

        return pygame.Rect(x * self._charwidth, y * self._charheight, self._charwidth, self._charheight)


    def setcolor(self, fgcolor=None, bgcolor=None, x=None, y=None, width=None, height=None, rect=None):
        pass
        x, y, width, height = self._constrainsize(x, y, width, height, rect)


    def reversecolor(self, x=None, y=None, width=None, height=None, rect=None):
        pass
        x, y, width, height = self._constrainsize(x, y, width, height, rect)


    def copy(self, dstwindow, x=None, y=None, width=None, height=None, rect=None):
        pass
        x, y, width, height = self._constrainsize(x, y, width, height, rect)


    def lighten(self, amount=None, x=None, y=None, width=None, height=None, rect=None):
        pass
        x, y, width, height = self._constrainsize(x, y, width, height, rect)


    def darken(self, amount=None, x=None, y=None, width=None, height=None, rect=None):
        pass
        x, y, width, height = self._constrainsize(x, y, width, height, rect)


    def erase(self, length=None, x=None, y=None, width=None, height=None, rect=None):
        pass # TODO - technically, printing a space and erasing are different (but only when you call read())

        # note: this method does not change the cursor, nor does it cause a screen shift (it just ends)

        if length is not None:
            # erase a certain number of characters, starting from the cursor
            tempcursorx, tempcursory = self._cursorx, self._cursory
            for i in range(length):
                self._screen[tempcursorx][tempcursory] = None
                tempcursorx += 1
                if tempcursorx >= self._width:
                    tempcursorx = 0
                    tempcursory += 1
                    if tempcursory >= self._height:
                        break
        else:
            # erase a rectangular area of the screen
            x, y, width, height = self._constrainsize(x, y, width, height, rect)
            for indx in range(x, width):
                for indy in range(y, height):
                    self._screen[indx][indy] = None


        if self._autoupdate:
            self.update()

    def fill(self, x=None, y=None, width=None, height=None, rect=None):
        pass
        x, y, width, height = self._constrainsize(x, y, width, height, rect)

        if self._autoupdate:
            self.update()


    def _shift(self):
        for x in range(self._width):
            for y in range(self._height - 1):
                self._screen[x][y] = self._screen[x][y+1]
            self._screen[x][self._height-1] = ' ' # bottom row is blanked



    def _checkbounds(self, x=None, y=None):
        if x is None:
            x = 0
        if y is None:
            y = 0

        if x >= self._width or y < -self._width:
            raise IndexError('x index %s out of range (width %s)' % (x, self._width))
        if y >= self._height or y < -self._height:
            raise IndexError('y index %s out of range (height %s)' % (y, self._height))

        if x < 0:
            x = self._width - x
        if y < 0:
            y = self._height - y

        return (x, y)


    def _constrainsize(self, x=0, y=0, width=None, height=None, rect=None):
        x, y = self._checkbounds(x, y)

        # TODO: Handle rect arg
        # TODO: if x and y are set, but width and height are not, then width and height should be 1, not the full size

        if width is None:
            width = 1
        if height is None:
            height = 1

        width = (width + x <= self._width) and (width) or (width - x)
        height = (height + y <= self._height) and (height) or (height - y)

        return (x, y, width, height)


    # File Object methods:

    def write(self, text):
        if type(text) != type(''):
            raise TypeError('argument 1 must be a string, not %s' % (type(text)))

        for i in range(len(text)):
            if text[i] in ('\n', '\r'):
                self._cursory += 1
                self._cursorx = -1
            elif text[i] == '\t':
                self._screen[self._cursorx][self._cursory] = ' ' # TODO - implement tabs
            else:
                self._screen[self._cursorx][self._cursory] = text[i]

            self._cursorx += 1
            if self._cursorx >= self._width:
                self._cursorx = 0
                self._cursory += 1
            if self._cursory >= self._height:
                self._shift() # TODO - we can calculate in advance what how many shifts to do.
                self._cursory = self._height - 1

        if self._autoupdate:
            self.update()


    def read(self):
        # returns the entire current contents of the window as a string (color & font info is lost)
        pass


    # Properties:

    def getcursorx(self):
        return self._cursorx

    def setcursorx(self, value):
        self._cursorx, y = self._checkbounds(int(value), None)

    cursorx = property(getcursorx, setcursorx)

    def getcursory(self):
        return self._cursory

    def setcursory(self, value):
        x, self._cursorx = self._checkbounds(None, int(value))

    cursory = property(getcursory, setcursory)

    def getcursor(self):
        return (self._cursorx, self._cursory)

    def setcursor(self, value):
        self._cursorx, self._cursory = self._checkbounds(int(value[0]), int(value[1]))

    cursor = property(getcursor, setcursor)

    def getfont(self):
        return self._font

    def setfont(self, value):
        self._font = value # TODO

    def getfgcolor(self):
        return self._fgcolor

    def setfgcolor(self, value):
        alpha = len(value) > 3 and value[3] or 255
        self._fgcolor = pygame.Color(value[0], value[1], value[2], alpha)

    fgcolor = property(getfgcolor, setfgcolor)

    def getbgcolor(self):
        return self._bgcolor

    def setbgcolor(self, value):
        alpha = len(value) > 3 and value[3] or 255
        self._bgcolor = pygame.Color(value[0], value[1], value[2], alpha)

    bgcolor = property(getbgcolor, setbgcolor)

    def getautoupdate(self):
        return _autoupdate

    def setautoupdate(self, value):
        self._autoupdate = bool(value)

    autoupdate = property(getautoupdate, setautoupdate)







def calcfontsize(font):
    z = font.render('Z', 1, (0,0,0))
    w = font.render('w', 1, (0,0,0))
    return w.get_width(), z.get_height()


def ismonofont(font):
    i = font.render('i', 1, (0,0,0))
    w = font.render('w', 1, (0,0,0))
    print('i: %s, w: %s' % (i.get_width(), w.get_width()))
    return i.get_width() == w.get_width() # cheesy, but probably works
