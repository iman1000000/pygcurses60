import pygame, copy
from pygame.locals import *

# TODO - need to profile how pygame renders full string compared to rendering individual chars.


# TODO - speed up - cache letters and colors.

"""
# BUGS:
TODO - cursor blinking
TODO - typing mode
TODO - VER2 Drawing functions and box functions.
TODO - copy and paste plaintext mode (ignores currently set color), also copy/paste between pygcurse windows.
TODO - VER2 field widgets extensability (combo box, radio buttons, checkbox, spinner/progress bar, layout) (basically anything that wxPython provides)
TODO - VER2 sprites - skip this.

TODO - add a "in memory only pygcurse window" flag, so that we don't bother rendering. This could be used for copy/pasting, etc. Wait, is this a good feature?


TODO - input() should work exactly like the python built-in. carry over, backspace, del, arrow keys, shift & caps lock, insert


NOTE - we still need _screenchars to be up to date so that we can call GETCHAR.

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
11) Screen can be resized
12) subwindow printing
13) one-line input (implemented as a widget)
14) Drop in replacement of text-mode games.

DEMOS:
Eliza chat bot/zork. (is there a python version of zork, or some other text adventure?)
Hello world, color change, tint, copy/paste
Hello world, except the pygcurse surface is rotated in an animation. (Allows typing)
Resize window
Maze game
drop-in replacement of our othello game

DOES NOT SUPPORT:
unicode (well, this actually depends on Pygame's support of unicode)
sprite transformation/cropping/scaling
squares of different sizes in the same view.
Font transformation.
Drawing primitives (you can't draw a line of blocks or something such as that).

mapping sprites to characters and then printing them.

don't support input() for now.
"""

DEFAULTFGCOLOR = pygame.Color(164, 164, 164, 255)
DEFAULTBGCOLOR = pygame.Color(0, 0, 0, 255)
ERASECOLOR = pygame.Color(0, 0, 0, 0)

_NEW_WINDOW = 'new_window'
_FULL_SCREEN = 'full_screen'

class PygcurseSurface():
    def __init__(self, width=80, height=25, font=None, fgcolor=DEFAULTFGCOLOR, bgcolor=DEFAULTBGCOLOR, windowsurface=None):
        self._cursorx = 0
        self._cursory = 0
        self._width = width
        self._height = height
        self._screenchars = [[' '] * height for i in range(width)]

        # intialize the foreground and background colors of each cell
        self._screenfgcolor = [[None] * height for i in range(width)]
        self._screenbgcolor = [[None] * height for i in range(width)]
        for x in range(width):
            for y in range(height):
                self._screenfgcolor[x][y] = DEFAULTFGCOLOR
                self._screenbgcolor[x][y] = DEFAULTBGCOLOR
        self._screendirty = [[True] * height for i in range(width)]
        #self._screenRdelta = [[0] * height for i in range(width)]
        #self._screenGdelta = [[0] * height for i in range(width)]
        #self._screenBdelta = [[0] * height for i in range(width)]


        if font is None:
            self._font = pygame.sysfont.SysFont('freesansbold', 18, fgcolor)
        else:
            self._font = font
        self._fgcolor = fgcolor
        self._bgcolor = bgcolor

        self._cellwidth, self._cellheight = calcfontsize(self._font)

        self._autoupdate = True
        if windowsurface == _NEW_WINDOW:
            self._windowsurface = pygame.display.set_mode((self._cellwidth * width, self._cellheight * height))
            self._managesDisplay = True
        elif windowsurface == _FULL_SCREEN:
            self._windowsurface = pygame.display.set_mode((self._cellwidth * width, self._cellheight * height), pygame.FULLSCREEN)
            self._managesDisplay = True
        else:
            self._windowsurface = windowsurface
            self._managesDisplay = False

        self._autowindowupdate = self._windowsurface is not None # TODO - do we really need this? shouldn't .windowsurface not being None be enough?
        self._tabsize = 8 # TODO - need to implement tabs

        self._pixelwidth = self._width * self._cellwidth
        self._pixelheight = self._height * self._cellheight
        self._surfobj = pygame.Surface((self._pixelwidth, self._pixelheight))
        self._surfobj = self._surfobj.convert_alpha() # TODO - This is needed for erasing, but does this have a performance hit?


    def print(self, obj, *objs, sep=' ', end='\n', font=None, fgcolor=None, bgcolor=None):
        # NOTE - not thread safe
        writefgcolor = (fgcolor is not None) and fgcolor or self._fgcolor
        writebgcolor = (bgcolor is not None) and bgcolor or self._bgcolor

        text = [str(obj)]
        if objs:
            text.append(str(sep) + str(sep).join([str(x) for x in objs]))
        text.append(str(end))

        self.write(''.join(text), writefgcolor, writebgcolor)


    def blitTo(self, surfaceObj, dest=(0, 0)):
        return surfaceObj.blit(self._surfobj, dest)

    """
    FORVERSION2 - put this off until the next version
    def loadsprites(self, spriteMapping, spritefontname='__default', setToThisSpriteFont=False):
        # sanity check
        for key in spriteMapping():
            assert len(key) == 1 or key is None, 'TODO - key %s must be a single char' % (key)

            if type(key) == type(''):
                spriteMapping[key] = pygame.image.load(key)
        self._spriteMaps[spritemapname] = spriteMapping
    """


    def update(self):
        """
        There are three types of updating:
            1) Updating the PygcurseSurface surface object to match the backend data.
                (Enabled by default by setting self._autoupdate == True)
            2) Blitting the PygcurseSurface surface object to the main window
                (Enabled by setting self._windowsurface to the main window)
            3) Calling pygame.display.update()
                (Enabled by default if _windowsurface is set, happens if _autowindowupdate == True)
        """
        # TODO - as an efficency improvememt I should probably have one 'dirty' variable track if ANY cell has been changed.
        _changed = 0
        # draw to the surfobj all the dirty cells.
        for x in range(self._width):
            for y in range(self._height):
                if self._screendirty[x][y]:
                    _changed += 1
                    self._screendirty[x][y] = False

                    # fill in the entire background of the cell
                    cellrect = pygame.Rect(self._cellwidth * x, self._cellheight * y, self._cellwidth, self._cellheight)

                    if self._screenchars[x][y] is None:
                        self._surfobj.fill(ERASECOLOR, cellrect)
                        continue

                    self._surfobj.fill(self._screenbgcolor[x][y], cellrect)

                    if self._screenchars[x][y] == ' ':
                        continue # don't need to render anything if it is just a space character.

                    # render the character and draw it to the surface
                    charsurf = self._font.render(self._screenchars[x][y], 1, self._screenfgcolor[x][y], self._screenbgcolor[x][y])
                    charrect = charsurf.get_rect()
                    charrect.centerx = self._cellwidth * x + int(self._cellwidth / 2)
                    charrect.bottom = self._cellheight * (y+1) # TODO - not correct, this would put stuff like g, p, q higher than normal.
                    self._surfobj.blit(charsurf, charrect)
        #if _changed:
        #    print('PygcurseSurface has been updated, %s cells redrawn.' % _changed)
        if self._windowsurface is not None:
            self._windowsurface.blit(self._surfobj, self._surfobj.get_rect())
            if self._autowindowupdate:
                pygame.display.update()

    _debugcolorkey = {(255,0,0): 'R',
                      (0,255,0): 'G',
                      (0,0,255): 'B',
                      (0,0,0): 'b',
                      (255, 255, 255): 'w'}


    def _debug(self, returnstr=False, fn=None):
        text = ['+' + ('-' * self._width) + '+\n']
        for y in range(self._height):
            line = ['|']
            for x in range(self._width):
                line.append(fn(x, y))
            line.append('|\n')
            text.append(''.join(line))
        text.append('+' + ('-' * self._width) + '+\n')
        if returnstr:
            return ''.join(text)
        else:
            print(''.join(text))


    def _debugfgFn(self, x, y):
        r, g, b = self._screenfgcolor[x][y].r, self._screenfgcolor[x][y].g, self._screenfgcolor[x][y].b
        if (r, g, b) in PygcurseSurface._debugcolorkey:
            return PygcurseSurface._debugcolorkey[(r, g, b)]
        else:
            return'.'
    def _debugfg(self, returnstr=False):
        return self._debug(returnstr=returnstr, fn=self._debugfgFn)


    def _debugbgFn(self, x, y):
        r, g, b = self._screenbgcolor[x][y].r, self._screenbgcolor[x][y].g, self._screenbgcolor[x][y].b
        if (r, g, b) in PygcurseSurface._debugcolorkey:
            return PygcurseSurface._debugcolorkey[(r, g, b)]
        else:
            return '.'
    def _debugbg(self, returnstr=False):
        return self._debug(returnstr=returnstr, fn=self._debugbgFn)


    def _debugcharsFn(self, x, y):
        if self._screenchars[x][y] in (None, '\n', '\t'):
            return '.'
        else:
            return self._screenchars[x][y]
    def _debugchars(self, returnstr=False):
        return self._debug(returnstr=returnstr, fn=self._debugcharsFn)

    def _debugdirtyFn(self, x, y):
        if self._screendirty[x][y]:
            return 'O'
        else:
            return '.'
    def _debugdirty(self, returnstr=False):
        return self._debug(returnstr=returnstr, fn=self._debugdirtyFn)

    def gettopleftpixel(self, cellx, celly):
        return (cellx * self._cellwidth, celly * self._cellheight)

    def gettoppixel(self, celly):
        return celly * self._cellheight

    def getleftpixel(self, cellx):
        return cellx * self._cellwidth

    def getcoordinatesatpixel(self, pixelx, pixely):
        """Given the pixel x and y coordinates relative to the PygCurse screen's
        origin, return the cell x and y coordinates that it is over. (Useful
        for finding what cell the mouse cursor is over.) Returns (None, None)
        if the pixel coordinates are not over the screen."""
        if pixelx < 0 or pixelx >= self._width * self._cellwidth:
            return (None, None)
        if pixely < 0 or pixely >= self._height * self._cellheight:
            return (None, None)
        return int(pixelx / self._cellwidth), int(pixely / self._cellheight)


    def getcharatpixel(self, pixelx, pixely):
        x, y = self.getcoordinatesatpixel(pixelx, pixely)
        if (x, y) == (None, None):
            return (None, None)
        return self._screenchars[x][y]

    # getrect is relative to the pygcurse surface. How about a getAbsoluteRect? We'd have to bind the pygcurse surface ccloser to the window
    def getrect(self, x=None, y=None, width=None, height=None):
        x, y, width, height = self.getregion(x, y, width, height)

        return pygame.Rect(x * self._cellwidth, y * self._cellheight, width * self._cellwidth, height * self._cellheight)




    def resize(self, newwidth=None, newheight=None, fgcolor=None, bgcolor=None):
        if newwidth == self._width and newheight == self._height:
            return
        if fgcolor is None:
            fgcolor = self._fgcolor
        fgcolor = getPygameColor(fgcolor)

        if bgcolor is None:
            bgcolor = self._bgcolor
        bgcolor = getPygameColor(bgcolor)

        # create new _screen* data structures
        newchars = [[None] * newheight for i in range(newwidth)]
        newfg = [[None] * newheight for i in range(newwidth)]
        newbg = [[None] * newheight for i in range(newwidth)]
        newdirty = [[True] * newheight for i in range(newwidth)]
        for x in range(newwidth):
            for y in range(newheight):
                if x >= self._width or y >= self._height:
                    # Create new color objects
                    newfg[x][y] = fgcolor
                    newbg[x][y] = bgcolor
                else:
                    newchars[x][y] = self._screenchars[x][y]
                    newdirty[x][y] = self._screendirty[x][y]
                    # Copy over old color objects
                    newfg[x][y] = self._screenfgcolor[x][y]
                    newbg[x][y] = self._screenbgcolor[x][y]

        # set new dimensions
        self._width = newwidth
        self._height = newheight
        self._pixelwidth = self._width * self._cellwidth
        self._pixelheight = self._height * self._cellheight
        self._cursorx = 0
        self._cursory = 0
        newsurf = pygame.Surface((self._pixelwidth, self._pixelheight))
        newsurf.blit(self._surfobj, (0, 0))
        self._surfobj = newsurf

        self._screenchars = newchars
        self._screenfgcolor = newfg
        self._screenbgcolor = newbg
        self._screendirty = newdirty

        if self._managesDisplay:
            # resize the pygame window itself
            self._windowsurface = pygame.display.set_mode((self._pixelwidth, self._pixelheight))
            self.update()
        elif self._autoupdate:
            self.update()


    def setfgcolor(self, fgcolor, x=None, y=None, width=None, height=None, rect=None):
        if x == y == width == height == rect == None:
            self._fgcolor = fgcolor
            return
        x, y, width, height = self.getregion(x, y, width, height, rect)
        changed = False
        for ix in range(x, x+width):
            for iy in range(y, y+height):
                #if sameColor(self._screenfgcolor[ix][iy], fgcolor) # TODO - run profiler to see if this is actually faster
                self._screenfgcolor[ix][iy] = fgcolor
                self._screendirty[ix][iy] = True


    def setbgcolor(self, bgcolor, x=None, y=None, width=None, height=None, rect=None):
        if x == y == width == height == rect == None:
            self._bgcolor = bgcolor
            return
        x, y, width, height = self.getregion(x, y, width, height, rect)
        for ix in range(x, x+width):
            for iy in range(y, y+height):
                self._screenbgcolor[ix][iy] = fgcolor
                self._screendirty[ix][iy] = True


    def setcolors(self, fgcolor=None, bgcolor=None, x=None, y=None, width=None, height=None, rect=None):
        pass
        if fgcolor is None and bgcolor is None:
            return

        x, y, width, height = self.getregion(x, y, width, height, rect)
        for ix in range(x, x+width):
            for iy in range(y, y+height):
                self._screenfgcolor[ix][iy] = fgcolor
                self._screenfgcolor[ix][iy] = fgcolor
                self._screendirty[ix][iy] = True



    def reversecolors(self, x=None, y=None, width=None, height=None, rect=None):
        x, y, width, height = self.getregion(x, y, width, height, rect)
        if x == y == width == height == None:
            return

        for ix in range(x, x+width):
            for iy in range(y, y+height):
                # TODO - cache pygame.Color objects? Would that speed things up?
                self._screenfgcolor[ix][iy], self._screenbgcolor[ix][iy] = self._screenbgcolor[ix][iy], self._screenfgcolor[ix][iy]
                self._screendirty[ix][iy] = True
        if self._autoupdate:
            self.update()


    def _invertfg(self, x, y):
        fgcolor = self._screenfgcolor[x][y]
        invR, invG, invB = 255 - fgcolor.r, 255 - fgcolor.g, 255 - fgcolor.b
        self._screenfgcolor[x][y] = pygame.Color(invR, invG, invB, fgcolor.a)

    def _invertbg(self, x, y):
        bgcolor = self._screenbgcolor[x][y]
        invR, invG, invB = 255 - bgcolor.r, 255 - bgcolor.g, 255 - bgcolor.b
        self._screenbgcolor[x][y] = pygame.Color(invR, invG, invB, bgcolor.a)

    def invertcolors(self, x=None, y=None, width=None, height=None, rect=None):
        x, y, width, height = self.getregion(x, y, width, height, rect)
        if x == y == width == height == None:
            return

        for ix in range(x, x+width):
            for iy in range(y, y+height):
                # TODO - cache pygame.Color objects? Would that speed things up?
                self._invertfg(ix, iy)
                self._invertbg(ix, iy)
                self._screendirty[ix][iy] = True
        if self._autoupdate:
            self.update()


    def invertfgcolor(self, x=None, y=None, width=None, height=None, rect=None):
        x, y, width, height = self.getregion(x, y, width, height, rect)
        if x == y == width == height == None:
            return

        for ix in range(x, x+width):
            for iy in range(y, y+height):
                # TODO - cache pygame.Color objects? Would that speed things up?
                self._invertfg(ix, iy)
                self._screendirty[ix][iy] = True
        if self._autoupdate:
            self.update()


    def invertbgcolor(self, x=None, y=None, width=None, height=None, rect=None):
        x, y, width, height = self.getregion(x, y, width, height, rect)
        if x == y == width == height == None:
            return

        for ix in range(x, x+width):
            for iy in range(y, y+height):
                # TODO - cache pygame.Color objects? Would that speed things up?
                self._invertbg(ix, iy)
                self._screendirty[ix][iy] = True
        if self._autoupdate:
            self.update()


    def copy(self, copychars=False, copyfgcolor=False, copybgcolor=False, x=None, y=None, width=None, height=None, rect=None):
        # TODO - fuck all this subsurf stuff, just make a new PygcurseSurface object.

        # TODO - If None is in _screenchars, it should mean "just skip this" because we need that behavior for the paste() functions. Same applies to screenfgcolor and screenbgcolor

        # doc - copies the chars, fg, and bg color. if you just want to copy the chars, use getchars
        x, y, width, height = self.getregion(x, y, width, height, rect)
        if x == y == width == height == None:
            return None

        copysurf = PygcurseSurface(width=width, height=height, font=self._font)
        for ix in range(width):
            for iy in range(height):
                # TODO - this copies references, we need it to copy the values
                if copychars:
                    copysurf._screenchars[ix][iy] = self._screenchars[ix + x][iy + y]
                if copyfgcolor:
                    copysurf._screenfgcolor[ix][iy] = self._screenfgcolor[ix + x][iy + y]
                if copybgcolor:
                    copysurf._screenbgcolor[ix][iy] = self._screenbgcolor[ix + x][iy + y]
        return copysurf


    def copychars(self, x=None, y=None, width=None, height=None, rect=None):
        return self.copy(True, False, False, x, y, width, height, rect)


    def copyfgcolor(self, x=None, y=None, width=None, height=None, rect=None):
        return self.copy(False, True, False, x, y, width, height, rect)


    def copybgcolor(self, x=None, y=None, width=None, height=None, rect=None):
        return self.copy(False, False, True, x, y, width, height, rect)


    def paste(self, srcsurf, pastechars=False, pastefgcolor=False, pastebgcolor=False, x=None, y=None, width=None, height=None, rect=None):
        if type(copysurf) != type(self): # TODO - is this the right way to do this?
            return None

        x, y, width, height = self.getregion(x, y, width, height, rect)
        if x == y == width == height == None:
            return None

        for ix in range(width):
            for iy in range(height):
                # TODO - this copies references, we need it to copy the values
                if pastechars and srcsurf._screenchars[x][y] is not None:
                    self._screenchars[x+ix][y+iy] = srcsurf._screenchars[ix][iy]
                if pastefgcolor and srcsurf._screenfgcolor[x][y] is not None:
                    self._screenfgcolor[x+ix][y+iy] = srcsurf._screenfgcolor[ix][iy]
                if pastebgcolor and srcsurf._screenbgcolor[x][y] is not None:
                    self._screenbgcolor[x+ix][y+iy] = srcsurf._screenbgcolor[ix][iy]
        return True

    def pastechars(self, srcsurf, x=None, y=None, width=None, height=None, rect=None):
        return self.paste(srcsurf, True, False, False, x, y, width, height, rect)


    def pastefgcolor(self, srcsurf, x=None, y=None, width=None, height=None, rect=None):
        return self.paste(srcsurf, False, True, False, x, y, width, height, rect)


    def pastebgcolor(self, srcsurf, x=None, y=None, width=None, height=None, rect=None):
        return self.paste(srcsurf, False, False, True, x, y, width, height, rect)




    """
    # VER2
    def lighten(self, amount=51, x=None, y=None, width=None, height=None, rect=None):
        self.tint(amount, amount, amount)


    def darken(self, amount=51, x=None, y=None, width=None, height=None, rect=None):
        self.tint(-amount, -amount, -amount)

    def tint(self, r=0, g=0, b=0):
        x, y, width, height = self.getregion(x, y, width, height, rect)
        for xindex in range(x, x+width):
            for yindex in range(y, y+height):
                self._screenRdelta[xindex][yindex] += r
                self._screenGdelta[xindex][yindex] += g
                self._screenBdelta[xindex][yindex] += b
                self._screendirty[xindex][yindex] = True
    """

    def getchar(self, x, y):
        x, y, width, height = self.getregion(x, y)
        if x == y == width == height == None:
            return None

        return self._screenchars[x][y]

    def getchars(self, x=None, y=None, width=None, height=None, rect=None, gapChar=' '):
        x, y, width, height = self.getregion(x, y, width, height, rect)
        if x == y == width == height == rect == None:
            return []

        lines = []
        for iy in range(y, y + height):
            line = []
            for ix in range(x, x + width):
                if self._screenchars[ix][iy] is None:
                    line.append(gapChar)
                else:
                    line.append(self._screenchars[ix][iy])
            lines.append(''.join(line))
        return lines


    def putchar(self, char, x=None, y=None, fgcolor=None, bgcolor=None):
        if x is None:
            x = self._cursorx
        if y is None:
            y = self._cursory
        x, y, width, height = self.getregion(x, y)
        if x == y == width == height == None:
            return None

        if fgcolor is not None:
            self._screenfgcolor[x][y] = getPygameColor(fgcolor)
        if bgcolor is not None:
            self._screenbgcolor[x][y] = getPygameColor(bgcolor)

        self._screenchars[x][y] = char[0]
        self._screendirty[x][y] = True

        if self._autoupdate:
            self.update()

        return char

    def putchars(self, chars, x=None, y=None, width=None, height=None, rect=None, fgcolor=None, bgcolor=None):
        # doc - does not modify the cursor. That's how putchars is different from print() or write()
        # doc - also, putchars does not wrap or cause shifts. TODO!
        if x is None:
            x = self._cursorx
        if y is None:
            y = self._cursory

        # TODO - wait, what if we just want to start at a certain x, y and continue printing. oh yeah, just use write()
        if width is None:
            width = self._width # this will be truncated at the right edge of the screen
        if height is None:
            height = self._height # this will be truncated at the bottom edge of the screen

        x, y, width, height = self.getregion(x, y, width, height)
        if x == y == width == height == rect == None:
            return None

        if type(chars) in (list, tuple):
            # convert a list/tuple of strings to a single string (this is so that putchars() can work with the return value of getchars())
            chars = '\n'.join(chars)

        tempcurx = x
        tempcury = y
        for i in range(len(chars)):
            if tempcurx >= x+width or chars[i] in ('\n', '\r'): # TODO - wait, this isn't right. We should be ignoring one of these newlines.
                tempcurx = x
                tempcury += 1
            if tempcury >= y+height:
                break

            self._screenchars[tempcurx][tempcury] = chars[i]
            self._screendirty[tempcurx][tempcury] = True
            if fgcolor is not None:
                self._screenfgcolor[tempcurx][tempcury] = fgcolor
            if bgcolor is not None:
                self._screenbgcolor[tempcurx][tempcury] = bgcolor
            tempcurx += 1

        if self._autoupdate:
            self.update()

    def erase(self, x=None, y=None, width=None, height=None, rect=None):
        self.fill(None, None, None, x, y, width, height, rect)

    def fill(self, char=' ', fgcolor=None, bgcolor=None, x=None, y=None, width=None, height=None, rect=None):
        x, y, width, height = self.getregion(x, y, width, height, rect)
        if x == y == width == height == rect == None:
            return

        for ix in range(x, x+width):
            for iy in range(y, y+height):
                self._screenchars[ix][iy] = char
                if fgcolor is not None:
                    self._screenfgcolor[ix][iy] = fgcolor
                if bgcolor is not None:
                    self._screenbgcolor[ix][iy] = bgcolor
                self._screendirty[ix][iy] = True

        if self._autoupdate:
            self.update()


    def _shift(self):
        """Shift the content of the entire screen up one row. This is done when
        characters are printed to the screen that go past the end of the last
        row."""
        for x in range(self._width):
            for y in range(self._height - 1):
                self._screenchars[x][y] = self._screenchars[x][y+1]
                self._screenfgcolor[x][y] = self._screenfgcolor[x][y+1]
                self._screenbgcolor[x][y] = self._screenbgcolor[x][y+1]
            self._screenchars[x][self._height-1] = ' ' # bottom row is blanked
            self._screenfgcolor[x][self._height-1] = self._fgcolor
            self._screenbgcolor[x][self._height-1] = self._bgcolor
        self._screendirty = [[True] * self._height for i in range(self._width)]


    def getregion(self, x=None, y=None, width=None, height=None, rect=None):
        # parameter validation
        if rect is None:
            if (width is None) ^ (height is None):
                raise Exception('Bad argument passed to getregion(), width and height parameters must both be set or both not set.')
            if (x is None) ^ (y is None):
                raise Exception('Bad argument passed to getregion(), x and y parameters must both be set or both not set.')
            if (x is None or y is None) and (width is not None or height is not None):
                raise Exception('Bad argument passed to getregion(), x and y parameters must be set if width and height are set.')

        # interpret the parameters
        if rect is not None:
            # Supplying a rect parameter overrides the x, y, width, height parameters
            x, y, width, height = rect.left, rect.top, rect.width, rect.height
        elif width is None and height is None:
            if x is not None and y is not None:
                # only x & y were specified, assume this is a 1x1 space
                width = height = 1
            else:
                # all five parameters are None, return the full size of the surface
                return 0, 0, self._width, self._height

        if x + width < 0 or y + height < 0 or x >= self._width or y >= self._height:
            # If x or y are outside the boundaries, then return None
            return None, None, None, None

        # Truncate width or height if they extend past the boundaries
        if x + width > self._width:
            width -= (x + width) - self._width
        if y + height > self._height:
            height -= (y + height) - self._height
        if x < 0:
            width += x # subtracts, since x is negative
            x = 0
        if y < 0:
            height += y # subtracts, since y is negative
            y = 0

        return x, y, width, height

    # File-like Object methods:
    def writekeyevent(self, keyevent, fgcolor=None, bgcolor=None):
        char = interpretKeyEvent(keyevent)
        if char is not None:
            self.write(char, fgcolor=fgcolor, bgcolor=bgcolor)


    def write(self, text, fgcolor=None, bgcolor=None):
        text = str(text)
        if fgcolor is None:
            fgcolor = self._fgcolor
        elif type(fgcolor) == tuple:
            fgcolor = pygame.Color(*fgcolor)
        if bgcolor is None:
            bgcolor = self._bgcolor
        elif type(bgcolor) == tuple:
            bgcolor = pygame.Color(*bgcolor)

        # TODO - we can calculate in advance what how many shifts to do.


        # replace tabs with appropriate number of spaces
        i = 0
        tempcursorx = self._cursorx - 1
        while i < len(text):
            if text[i] == '\n':
                tempcursorx = 0
            elif text[i] == '\t':
                numspaces = self._tabsize - ((i+1) + tempcursorx % self._tabsize)
                if tempcursorx + numspaces >= self._width:
                    # tabbed past the edge, just go to first
                    # TODO - this doesn't work at all.
                    text = text[:i] + (' ' * (self._width - tempcursorx + 1)) + text[i+1:]
                    tempcursorx += (self._width - tempcursorx + 1)
                else:
                    text = text[:i] + (' ' * numspaces) + text[i+1:]
                    tempcursorx += numspaces
            else:
                tempcursorx += 1

            if tempcursorx >= self._width:
                tempcursorx = 0
            i += 1

        #text = text.replace('\t', ' ' * self._tabsize) # TODO - replace with proper tab code one day

        """
        # create a cache of surface objects for each letter in text
        letterSurfs = {}
        for letter in text:
            if ord(letter) in range(33, 128) and letter not in letterSurfs:
                letterSurfs[letter] = self._font.render(letter, 1, fgcolor, bgcolor)
                #letterSurfs[letter] = letterSurfs[letter].convert_alpha() # TODO - wait a sec, I don't think pygame lets fonts have transparent backgrounds.
            elif letter == ' ':
                continue
            elif letter not in letterSurfs and '?' not in letterSurfs:
                letterSurfs['?'] = self._font.render('?', 1, fgcolor, bgcolor)
                #letterSurfs['?'] = letterSurfs['?'].convert_alpha()
        """

        for i in range(len(text)):
            if text[i] in ('\n', '\r'): # TODO - wait, this isn't right. We should be ignoring one of these newlines. Otherwise \r\n shows up as two newlines.
                self._cursory += 1
                self._cursorx = 0
            else:
                if ord(text[i]) not in range(32, 128):
                    text = text[:i] + '?' + text[i:] # handle unprintable characters # TODO - fix for unicode and fonts missing characters.
                # set the backend data structures that track the screen state
                self._screenchars[self._cursorx][self._cursory] = text[i]
                self._screenfgcolor[self._cursorx][self._cursory] = fgcolor
                self._screenbgcolor[self._cursorx][self._cursory] = bgcolor
                self._screendirty[self._cursorx][self._cursory] = True

                """
                r = pygame.Rect(self._cellwidth * self._cursorx, self._cellheight * self._cursory, self._cellwidth, self._cellheight)
                self._surfobj.fill(bgcolor, r)
                charsurf = letterSurfs[text[i]]
                charrect = charsurf.get_rect()
                charrect.centerx = self._cellwidth * self._cursorx + int(self._cellwidth / 2)
                charrect.bottom = self._cellheight * (self._cursory+1)
                self._surfobj.blit(charsurf, charrect)
                self._screendirty[self._cursorx][self._cursory] = False
                """

                # Move cursor over (and to next line if it moves past the right edge)
                self._cursorx += 1
                if self._cursorx >= self._width:
                    self._cursorx = 0
                    self._cursory += 1
            if self._cursory >= self._height:
                # shift up a line if we try to print on the line after the last one
                self._shift()
                self._cursory = self._height - 1

        if self._autoupdate:
            self.update()


    def read(self):
        return '\n'.join(self.getchars())


    # Properties:
    def _propgetcursorx(self):
        return self._cursorx

    def _propsetcursorx(self, value):
        x = int(value)
        if x >= self._width or x <= -self._width:
            return # no-op

        if x < 0:
            x = self._width - x

        self._cursorx = x


    def _propgetcursory(self):
        return self._cursory

    def _propsetcursory(self, value):
        y = int(value)
        if y >= self._height or y <= -self._height:
            return # no-op

        if y < 0:
            y = self._height - y

        self._cursory = y


    def _propgetcursor(self):
        return (self._cursorx, self._cursory)

    def _propsetcursor(self, value):
        x = int(value[0])
        y = int(value[1])
        if x >= self._width or x <= -self._width or y >= self._height or y <= -self._height:
            return # no-op

        if x < 0:
            x = self._width - x
        self._cursorx = x

        if y < 0:
            y = self._height - y
        self._cursory = y


    """
    # VER2
    def _propgetfont(self):
        return self._font

    def _propsetfont(self, value):
        self._font = value # TODO
    """

    def _propgetfgcolor(self):
        return self._fgcolor

    def _propsetfgcolor(self, value):
        self._fgcolor = getPygameColor(value)


    def _propgetbgcolor(self):
        return self._bgcolor

    def _propsetbgcolor(self, value):
        self._bgcolor = getPygameColor(value)

    def _propgetcolors(self):
        return (self._fgcolor, self._bgcolor)

    def _propsetcolors(self, value):
        self._fgcolor = getPygameColor(value[0])
        self._bgcolor = getPygameColor(value[1])


    def _propgetautoupdate(self):
        return self._autoupdate

    def _propsetautoupdate(self, value):
        self._autoupdate = bool(value)


    def _propgetautowindowupdate(self):
        return self._autowindowupdate

    def _propsetautowindowupdate(self, value):
        if self._windowsurface is not None:
            self._autowindowupdate = bool(value)
        elif bool(value):
            # TODO - this should be a raised exception, not an assertion.
            assert False, 'Window Surface object must be set to a surface before autowindowupdate can be enabled.'



    def _propgetheight(self):
        return self._height

    def _propsetheight(self, value):
        newheight = int(value)
        if newheight != self._height:
            self._height = newheight
            self.resize()


    def _propgetwidth(self):
        return self._width

    def _propsetwidth(self, value):
        newwidth = int(value)
        if newwidth != self._width:
            self._width = newwidth
            self.resize()


    def _propgetsize(self):
        return (self._width, self._height)

    def _propsetsize(self, value):
        newwidth = int(value[0])
        newheight = int(value[1])
        if newwidth != self._width or newheight != self._height:
            self._width = newwidth
            self._height = newheight
            self.resize()


    def _propgetpixelwidth(self):
        return self._width * self._cellwidth

    def _propsetpixelwidth(self, value):
        newwidth = int(int(value) / self._cellwidth)
        if newwidth != self._width:
            self._width = newwidth
            self.resize()


    def _propgetpixelheight(self):
        return self._height * self._cellheight

    def _propsetpixelheight(self, value):
        newheight = int(int(value) / self._cellheight)
        if newheight != self._height:
            self._height = newheight
            self.resize()


    def _propgetpixelsize(self):
        return (self._width * self._cellwidth, self._height * self._cellheight)

    def _propsetpixelsize(self, value):
        newwidth = int(int(value) / self._cellwidth)
        newheight = int(int(value) / self._cellheight)
        if newwidth != self._width or newheight != self._height:
            self._width = newwidth
            self._height = newheight
            self.resize()


    def _propgetcellwidth(self):
        return self._cellwidth

    #def _propsetcellwidth(self, value): # VER2


    def _propgetcellheight(self):
        return self._cellheight

    #def _propsetcellheight(self, value): # VER2

    def _propgetcellsize(self):
        return (self._cellwidth, self._cellheight)

    #def _propsetcellsize(self, value): # VER2

    def _propgetfont(self):
        return self._font

    #def _propsetfont(self, value): # VER2

    def _propgetsurface(self):
        return self._surfobj


    def _propgetleft(self):
        return 0
    def _propgetright(self):
        return self._width - 1 # note: this behavior is different from pygame Rect objects, which do not have the -1.
    def _propgettop(self):
        return 0
    def _propgetbottom(self):
        return self._height - 1 # note: this behavior is different from pygame Rect objects, which do not have the -1.
    def _propgetcenterx(self):
        return int(self._width / 2)
    def _propgetcentery(self):
        return int(self._height / 2)
    def _propgettopleft(self):
        return (0, 0)
    def _propgettopright(self):
        return (self._width - 1, 0)
    def _propgetbottomleft(self):
        return (0, self._height - 1 )
    def _propgetbottomright(self):
        return (self._width - 1, self._height - 1 )
    def _propgetmidleft(self):
        return (0, int(self._height / 2))
    def _propgetmidright(self):
        return (self._width - 1, int(self._height / 2))
    def _propgetmidtop(self):
        return (int(self._width / 2), 0)
    def _propgetmidbottom(self):
        return (int(self._width / 2), self._height - 1 )


    cursorx = property(_propgetcursorx, _propsetcursorx)
    cursory = property(_propgetcursory, _propsetcursory)
    cursor = property(_propgetcursor, _propsetcursor)
    fgcolor = property(_propgetfgcolor, _propsetfgcolor)
    bgcolor = property(_propgetbgcolor, _propsetbgcolor)
    colors = property(_propgetcolors, _propsetcolors)
    autoupdate = property(_propgetautoupdate, _propsetautoupdate)
    autowindowupdate = property(_propgetautowindowupdate, _propsetautowindowupdate)
    width = property(_propgetwidth, _propsetwidth)
    height = property(_propgetheight, _propsetheight)
    size = property(_propgetsize, _propsetsize)
    pixelwidth = property(_propgetpixelwidth, _propsetpixelwidth)
    pixelheight = property(_propgetpixelheight, _propsetpixelheight)
    pixelsize = property(_propgetpixelsize, _propsetpixelsize)
    font = property(_propgetfont, None) # Set func will be in VER2
    cellwidth = property(_propgetcellwidth, None) # Set func will be in VER2
    cellheight = property(_propgetcellheight, None) # Set func will be in VER2
    cellsize = property(_propgetcellsize, None) # Set func will be in VER2
    surface = property(_propgetsurface, None)

    left = property(_propgetleft, None)
    right = property(_propgetright, None)
    top = property(_propgettop, None)
    bottom = property(_propgetbottom, None)
    centerx = property(_propgetcenterx, None)
    centery = property(_propgetcentery, None)
    topleft = property(_propgettopleft, None)
    topright = property(_propgettopright, None)
    bottomleft = property(_propgetbottomleft, None)
    bottomright = property(_propgetbottomright, None)
    midleft = property(_propgetmidleft, None)
    midright = property(_propgetmidright, None)
    midtop = property(_propgetmidtop, None)
    midbottom = property(_propgetmidbottom, None)


def calcfontsize(font):
    maxwidth = 0
    maxheight = 0
    for i in range(32, 128):
        surf = font.render(chr(i), True, (0,0,0))
        if surf.get_width() > maxwidth:
            maxwidth = surf.get_width()
        if surf.get_height() > maxheight:
            maxheight = surf.get_height()

    return maxwidth, maxheight


def ismonofont(font):
    minwidth = 0
    minheight = 0
    for i in range(32, 128):
        surf = font.render(chr(i), True, (0,0,0))
        if surf.get_width() < minwidth:
            minwidth = surf.get_width()
        if surf.get_height() < minheight:
            minheight = surf.get_height()

    maxwidth, maxheight = calcfontsize(font)
    return maxwidth - minwidth <= 3 and maxheight - minheight <= 3


def isSameColor(color1, color2):
    c1 = getPygameColor(color1)
    c2 = getPygameColor(color2)
    return (c1.r == c2.r) and (c1.g == c2.g) and (c1.b == c2.b) and (c1.a == c2.a)

def getPygameColor(value):
    if type(value) in (tuple, list):
        alpha = len(value) > 3 and value[3] or 255
        return pygame.Color(value[0], value[1], value[2], alpha)
    elif str(type(value)) == "<type 'pygame.Color'>":
        return value
    else:
        raise Exception('Color set to invalid value.')

    if type(color) in (tuple, list):
        return pygame.Color(*color)
    return color


class PygcurseWindow(PygcurseSurface):
    def __init__(self, width=80, height=25, font=None, fgcolor=DEFAULTFGCOLOR, bgcolor=DEFAULTBGCOLOR, fullscreen=False):
        pygame.init()
        fullscreen = fullscreen and _FULL_SCREEN or _NEW_WINDOW
        super().__init__(width, height, font, fgcolor, bgcolor, fullscreen)


class PygcurseLayers():
    pass # VER2 - TODO - a layer management system so it's easy to draw PygcurseSurface objects on top of each other.


_shiftchars = {'`':'~', '1':'!', '2':'@', '3':'#', '4':'$', '5':'%', '6':'^', '7':'&', '8':'*', '9':'(', '0':')', '-':'_', '=':'+', '[':'{', ']':'}', '\\':'|', ';':':', "'":'"', ',':'<', '.':'>', '/':'?'}

def interpretKeyEvent(keyevent):
    key = keyevent.key
    if (key >= 32 and key < 128) or key in (ord('\n'), ord('\r'), ord('\t')):
        caps = bool(keyevent.mod & KMOD_CAPS)
        shift = bool(keyevent.mod & KMOD_LSHIFT or keyevent.mod & KMOD_RSHIFT)
        char = chr(key)
        if char.isalpha() and (caps ^ shift):
            char = char.upper()
        elif shift and char in PygcurseSurface._shiftchars:
            char = PygcurseSurface._shiftchars[char]
        return char
    return None

class InputEmu():
    def __init__(self):
        self.buffer = []
        self.cursor = 0
        self.insertMode = False

    def backspace(self):
        if self.cursor == 0:
            return
        self.cursor -= 1
        del self.buffer[self.cursor]


    def delete(self):
        if self.cursor == len(self.buffer):
            return
        del self.buffer[self.cursor]


    def home(self):
        self.cursor = 0


    def end(self):
        self.cursor = len(self.buffer)


    def leftarrow(self):
        if self.cursor > 0:
            self.cursor -= 1


    def rightarrow(self):
        if self.cursor <= len(self.buffer):
            self.cursor += 1

    def paste(text):
        # TODO - account for insertMode

        if self.cursor == len(self.buffer):
            # append to end
            self.buffer.extend(list(str(text)))
            return


        if self.cursor == 0:
            # prepend to beginning
            self.buffer = list(str(text)) + self.buffer
        else:
            self.buffer = self.buffer[self.cursor:] + list(str(text)) + self.buffer[:self.cursor]

    def interpretkey(self, key, mod):
        pass # TODO - meant to work with pygame

    def __len__(self):
        return len(self.buffer)
