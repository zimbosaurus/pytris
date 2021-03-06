import pygame
import sys
import random
import math


class Mino:
    DOWN = (0, 1)

    @staticmethod
    def draw(screen, pos, size, color):
        r = pygame.Rect(pos[0], pos[1], size, size)
        pygame.draw.rect(screen, color, r)

    def __init__(self, pos, color):
        self.pos = pos
        self.move_pos = pos
        self.color = color
        self.frozen = False
        self.matrix = None

    def place(self, matrix):
        if self.matrix is None:
            self.matrix = matrix
        matrix.set(self.pos, self.make_cell())

    def move(self, direction):
        if self.matrix is None:
            return

        if self.pos != self.move_pos:
            return

        dx, dy = direction
        can = self.can_move(direction)
        if can:
            self.matrix.set(self.pos, None)
            self.move_pos = (self.pos[0] + dx, self.pos[1] + dy)
        return can

    def update(self):
        self.pos = self.move_pos
        self.matrix.set(self.pos, self.make_cell())

    def make_cell(self):
        return self.color, self.frozen

    def can_move(self, direction):
        if self.matrix is None:
            return

        dx, dy = direction
        cell = self.matrix.get((self.pos[0] + dx, self.pos[1] + dy))
        return cell is None or not cell[1]


class Tetromino:
    fall_speed = 400
    FREEZE_TIME = 2

    @staticmethod
    def rotate_structure_cc(structure):
        rotated = []
        for x in range(len(structure[0])):
            row = []
            for y in reversed(range(len(structure))):
                row.append(structure[y][x])
            rotated.append(row)
        return rotated

    @staticmethod
    def get_start_pos(structure):
        return math.floor(Tetris.matrix_width / 2) - math.floor(len(structure[0]) / 2), 0

    def __init__(self, piece, pos):
        self.type = piece[2]
        self.structure = piece[0]
        self.color = piece[1]
        self.minos = []
        self.frozen = False
        self.last_fall = 0
        self.pos = pos
        self.matrix = None
        self._create()
        self.freeze_timer = 0

    def _create(self):
        structure = self.structure
        pos = self.pos
        color = self.color
        for y in range(len(structure)):
            for x in range(len(structure[0])):
                if structure[y][x] == 1:
                    self.minos.append(Mino((x + pos[0], y + pos[1]), color))

    def _destroy(self):
        self.clear()
        self.minos = []

    def clear(self):
        for mino in self.minos:
            mino.matrix.set(mino.pos, None)

    def place(self, matrix):
        self.matrix = matrix
        for mino in self.minos:
            mino.place(matrix)

    def move(self, direction):
        for mino in self.minos:
            if not mino.can_move(direction):
                return False

        self.pos = (self.pos[0] + direction[0], self.pos[1] + direction[1])
        for mino in self.minos:
            mino.move(direction)

        return True

    def set_pos(self, pos):
        if pos is None:
            return
        self._destroy()
        self.pos = pos
        self.pos = self.inside_bounds_delta(self.structure)
        self._create()
        self.place(self.matrix)

    def update(self):
        keys = pygame.key.get_pressed()
        fall_speed = int(Tetromino.fall_speed / 3) if keys[pygame.K_s] else Tetromino.fall_speed

        if pygame.time.get_ticks() - self.last_fall >= fall_speed:
            self.fall()
            self.last_fall = pygame.time.get_ticks()
        for mino in self.minos:
            mino.update()

    def fall(self):
        if self.frozen:
            return False

        if not self.move(Mino.DOWN):
            self.freeze()
            return False

        return True

    def instant_fall(self):
        i = 0
        self.freeze_timer = self.FREEZE_TIME
        while self.fall():
            for mino in self.minos:
                mino.update()
            if i >= Tetris.matrix_height:
                break
            i += 1

    def inside_bounds_delta(self, structure):
        dx_outside, dy_outside = 0, 0
        for y in range(len(structure)):
            for x in range(len(structure[0])):
                abs_pos = (x + self.pos[0], y + self.pos[1])

                # check if colliding with other minos
                cell = self.matrix.get(abs_pos)
                if cell is not None and cell != Matrix.OUT_OF_BOUNDS and cell[1]:
                    continue

                # check if outside and how far outside
                outside = not self.matrix.test_bounds(abs_pos)
                if outside:
                    if abs(x) > abs(dx_outside):
                        dx_outside = x
                    if abs(y) > abs(dy_outside):
                        dy_outside = y
        moved_pos = self.pos[0] - dx_outside, self.pos[1]
        return moved_pos

    def rotate_cc(self):
        # rotate structure
        rotated = Tetromino.rotate_structure_cc(self.structure)

        # move tetromino back inside bounds (if neccessary), or abort rotation if other minos are in the way
        moved_pos = self.inside_bounds_delta(rotated)

        # remove from matrix
        self._destroy()

        # update position and rotation
        self.pos = moved_pos
        self.structure = rotated

        # add new structure to matrix
        self._create()

        # re-place tetromino
        for mino in self.minos:
            mino.place(self.matrix)

        # reset freeze_timer
        self.freeze_timer = 0

    def draw_landing_column(self, screen):
        xf, yf = self.matrix.matrix_scale_factor()
        rect = pygame.Rect(0, 0, round(len(self.structure[0]) * xf), Tetris.window_height)
        s = pygame.Surface((rect.width, rect.height))
        s.set_alpha(30)
        s.fill(Tetris.WHITE)
        screen.blit(s, (self.pos[0] * xf, 0))

    def draw(self, screen, pos, scale):
        for sy, row in enumerate(self.structure):
            for sx, cell in enumerate(row):
                if cell == 0:
                    continue
                x, y = (scale * sx) + pos[0], (scale * sy) + pos[1]
                Mino.draw(screen, (x, y), scale, self.color)

    def get_piece(self):
        return self.structure, self.color, self.type

    def get_width(self):
        return len(self.structure[0])

    def freeze(self):
        if self.freeze_timer < self.FREEZE_TIME:
            self.freeze_timer += 1
            return

        self.frozen = True
        for mino in self.minos:
            mino.frozen = True


class Matrix:
    OUT_OF_BOUNDS = "OUT_OF_BOUNDS"

    @staticmethod
    def create_matrix(w, h, val_fn):
        return [[val_fn(x, y) for x in range(w)] for y in range(h)]

    def __init__(self, w, h):
        self.width = w
        self.height = h
        self.cells = Matrix.create_matrix(w, h, lambda x, y: None)
        self.screen_offset = (0, 0)
        self.surface = pygame.Surface(self.matrix_screen_size())

    def test_bounds(self, pos):
        return 0 <= pos[0] < self.width and 0 <= pos[1] < self.height

    def set(self, pos, val):
        if self.test_bounds(pos):
            self.cells[pos[1]][pos[0]] = val
        else:
            return Matrix.OUT_OF_BOUNDS

    def get(self, pos):
        if self.test_bounds(pos):
            return self.cells[pos[1]][pos[0]]
        else:
            return Matrix.OUT_OF_BOUNDS

    def get_size(self):
        return self.width, self.height

    def matrix_screen_size(self):
        """The size in pixels of the matrix on screen."""
        height = Tetris.window_height * 0.95
        m_ratio = self.width / self.height
        s_size = height * m_ratio, height
        return s_size

    def matrix_scale_factor(self):
        """The screen-size of one cell on the matrix."""
        x, y = self.matrix_screen_size()
        x = x / self.width
        y = y / self.height
        return x, y

    def cell_screen_rect(self, pos):
        """Get the size in screen-pixels for a cell in the matrix at the specified position."""
        xf, yf = self.matrix_scale_factor()
        return pygame.Rect(round(pos[0] * xf), round(pos[1] * yf), round(xf), round(yf))

    def draw_background(self):
        self.surface.fill(Tetris.BLACK)

    def draw_cells(self):
        for cy in range(self.height):
            for cx in range(self.width):
                cell = self.get((cx, cy))
                if cell is not None:
                    c_col, c_frozen = cell
                    c_rect = self.cell_screen_rect((cx, cy))
                    col = Tetris.BLACK if c_col is None else c_col
                    pygame.draw.rect(self.surface, col, c_rect)

    def blit(self, screen):
        screen.blit(self.surface, self.screen_offset)


class Tetris:
    BLACK = (0, 0, 0)
    GRAY = (25, 25, 25)
    WHITE = (255, 255, 255)

    BLUE = (3, 65, 174)
    GREEN = (114, 203, 59)
    YELLOW = (255, 213, 0)
    ORANGE = (255, 151, 28)
    RED = (255, 50, 19)
    LIGHT_BLUE = 0, 238, 255
    PURPLE = (171, 35, 235)

    FONT = None

    SCORE_INCREMENTS = [50, 100, 200, 300]
    ROW_COMBO_TIME = 3000

    QUEUE_SIZE, QUEUE_VISIBLE_SIZE = 14, 5

    T_PIECE = [[0, 1, 0], [1, 1, 1]], PURPLE, "T_PIECE"
    L_PIECE = [[1, 0, 0], [1, 1, 1]], BLUE, "L_PIECE"
    L_PIECE_M = [[0, 0, 1], [1, 1, 1]], ORANGE, "L_PIECE_M"
    SQUARE_PIECE = [[1, 1], [1, 1]], YELLOW, "SQUARE_PIECE"
    LONG_PIECE = [[1], [1], [1], [1]], LIGHT_BLUE, "LONG_PIECE"
    ZIG_PIECE = [[0, 1, 1], [1, 1, 0]], GREEN, "ZIG_PIECE"
    ZIG_PIECE_M = [[1, 1, 0], [0, 1, 1]], RED, "ZIG_PIECE_M"

    ALL_PIECES = [T_PIECE, L_PIECE, L_PIECE_M, SQUARE_PIECE, LONG_PIECE, ZIG_PIECE, ZIG_PIECE_M]

    matrix_width, matrix_height = 10, 24
    window_width, window_height = 800, 800
    framerate = 30
    window_label = "Tetris"
    window_icon = "tetris-logo.png"

    @staticmethod
    def init():
        pygame.init()
        Tetris.FONT = pygame.font.SysFont("Monospace", 30)

    @staticmethod
    def screen_scale_factor(dim):
        x = (Tetris.window_height / dim[0])
        y = (Tetris.window_height / dim[1])
        return x, y

    @staticmethod
    def mouse_pos():
        x, y = pygame.mouse.get_pos()
        scale = Tetris.screen_scale_factor((Tetris.matrix_width, Tetris.matrix_height))
        x = math.floor(x / scale[0])
        y = math.floor(y / scale[1])
        return x, y

    def __init__(self):
        self.matrix: Matrix = None
        self.piece_queue = None
        self.piece_hold = None
        self.cur_piece: Tetromino = None

        self.cursor_x = 0
        self.row_combo = 0
        self.score = 0
        self.screen = None
        self.running = False
        self.clock = pygame.time.Clock()
        self.paused = True
        self.reset()
        self.last_row_complete = 0

    def init_display(self):
        self.screen = pygame.display.set_mode((Tetris.window_width, Tetris.window_height))
        pygame.display.set_caption(Tetris.window_label)
        pygame.display.set_icon(pygame.image.load(Tetris.window_icon))

    def queue_count(self, piece):
        count = 0
        if piece is None:
            return count
        for tm in self.piece_queue:
            if tm.type == piece[2]:
                count += 1
        return count

    def make_piece(self):
        piece = None
        while piece is None or self.queue_count(piece) >= 2:
            piece = random.choice(Tetris.ALL_PIECES)
        return Tetromino(piece, (self.cursor_x, 0))

    def get_piece(self):
        self.piece_queue.insert(0, self.make_piece())
        return self.piece_queue.pop()

    def get_score_increase(self, first_row):
        score = self.SCORE_INCREMENTS[max(0, min(self.row_combo, len(self.SCORE_INCREMENTS)-1))]

        if first_row and pygame.time.get_ticks() - self.last_row_complete <= self.ROW_COMBO_TIME:
            self.row_combo += 1

        self.last_row_complete = pygame.time.get_ticks()
        print("SCORE + %s" % score)
        return score

    def complete_rows(self):
        first_row = True
        for y, row in enumerate(self.matrix.cells):
            complete = True
            for cell in row:
                if cell is None or not cell[1]:
                    complete = False
                    break
            if complete:
                self.score += self.get_score_increase(first_row)
                first_row = False
                self.matrix.cells.pop(y)
                self.matrix.cells.insert(0, [None for _ in range(self.matrix.width)])

    def center(self, size):
        return self.window_width / 2 - size[0] / 2, self.window_height / 2 - size[1] / 2

    def draw_hud(self):
        # draw queue
        scale, padding, spacing = 12, 12, 6
        x_off = padding
        for i, piece in enumerate(reversed(self.piece_queue)):
            if i >= Tetris.QUEUE_VISIBLE_SIZE:
                break
            piece.draw(self.screen, (x_off, padding), scale)
            x_off += len(piece.structure[0]) * scale + spacing
        # draw hold
        if self.piece_hold is not None:
            self.piece_hold.draw(self.screen, (Tetris.window_width - padding - self.piece_hold.get_width() * scale, padding), scale)
        # draw score
        score_text = Tetris.FONT.render("SCORE: %s" % self.score, True, Tetris.WHITE)
        self.screen.blit(score_text, (padding, self.window_height - score_text.get_size()[1] - padding))
        # score debug
        # debug_text = Tetris.FONT.render(("CURSOR_X: %s" % self.cursor_x), True, Tetris.WHITE)
        # self.screen.blit(debug_text, (padding, self.window_height - score_text.get_size()[1] - debug_text.get_size()[1] - padding))

    def reset(self):
        self.matrix = Matrix(Tetris.matrix_width, Tetris.matrix_height)
        m_s_size = self.matrix.matrix_screen_size()
        matrix_offset = self.center(m_s_size)
        self.matrix.screen_offset = matrix_offset

        self.score = 0
        self.piece_hold = None
        self.cur_piece = None
        self.piece_queue = []
        for i in range(1, Tetris.QUEUE_SIZE):
            self.piece_queue.append(self.make_piece())

    def delete_tetromino(self, t):
        t.clear()
        self.cur_piece = None

    def use_tetromino(self, t):
        pos = Tetromino.get_start_pos(t.structure)
        newt = Tetromino(t.get_piece(), pos)
        newt.place(self.matrix)
        self.cur_piece = newt

    def move_current_piece(self, direction):
        if self.cur_piece:
            self.cur_piece.move(direction)

    def run(self):
        self.init_display()
        self.running = True

        # main loop
        while self.running:
            # poll window events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    sys.exit()
                if event.type == pygame.KEYDOWN:
                    if self.cur_piece:
                        # move tetromino
                        if event.key == pygame.K_a or event.key == pygame.K_LEFT:
                            self.move_current_piece((-1, 0))
                        elif event.key == pygame.K_d or event.key == pygame.K_RIGHT:
                            self.move_current_piece((1, 0))
                        # drop tetromino
                        elif event.key == pygame.K_SPACE:
                            self.cur_piece.instant_fall()
                        # rotate tetromino
                        elif event.key == pygame.K_w or event.key == pygame.K_UP:
                            self.cur_piece.rotate_cc()
                        # hold tetromino
                        elif event.key == pygame.K_c:
                            # hold current piece
                            hold = self.piece_hold
                            self.piece_hold = self.cur_piece
                            self.delete_tetromino(self.piece_hold)
                            # place holded piece
                            if hold is not None:
                                self.use_tetromino(hold)
                    # reset
                    if event.key == pygame.K_r:
                        self.reset()
                    # pause
                    if event.key == pygame.K_ESCAPE:
                        self.paused = not self.paused
                    # pick piece
                    try:
                        key_num = int(pygame.key.name(event.key)) - 1
                        piece = self.ALL_PIECES[max(0, min(key_num, len(self.ALL_PIECES)-1))]
                        t = Tetromino(piece, Tetromino.get_start_pos(piece[0]))
                        if self.cur_piece and self.cur_piece.type != t.type:
                            self.delete_tetromino(self.cur_piece)
                            self.use_tetromino(t)
                        else:
                            self.piece_queue.append(t)
                            self.piece_queue.pop(0)
                    except ValueError:
                        pass

            # render pause
            if self.paused:
                self.screen.fill(Tetris.BLACK)
                text = Tetris.FONT.render("PRESS ESCAPE (PAUSED)", True, Tetris.WHITE)
                self.screen.blit(text, self.center(text.get_size()))

                pygame.display.flip()
                self.clock.tick(Tetris.framerate)
                continue

            # spawn pieces
            if self.cur_piece is None:
                self.cur_piece: Tetromino = self.get_piece()
                self.cur_piece.place(self.matrix)
                self.cur_piece.set_pos((self.cursor_x, 0))

            # update cursor pos
            if self.cur_piece:
                self.cursor_x = self.cur_piece.pos[0]

            # update minos
            self.cur_piece.update()
            if self.cur_piece.frozen:
                self.cur_piece = None

            # remove complete rows
            self.complete_rows()

            # check lose
            for cell in self.matrix.cells[0]:
                if cell is not None and cell[1]:
                    self.paused = True
                    self.reset()

            # update combo
            if pygame.time.get_ticks() - self.last_row_complete > self.ROW_COMBO_TIME:
                self.row_combo = 0

            # clear screen
            self.screen.fill(Tetris.GRAY)

            # draw background
            self.matrix.draw_background()
            # draw landing
            if self.cur_piece is not None:
                self.cur_piece.draw_landing_column(self.matrix.surface)
            # draw cells
            self.matrix.draw_cells()
            # blit matrix
            self.matrix.blit(self.screen)
            # draw hud
            self.draw_hud()

            # draw screen
            pygame.display.flip()

            self.clock.tick(Tetris.framerate)
