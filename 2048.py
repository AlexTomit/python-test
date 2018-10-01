import curses
import sqlite3
from random import  randrange,choice
from collections import defaultdict

conn = sqlite3.connect('2048.db')
c = conn.cursor()
l_codes = [ord(ch) for ch in 'WASDRQwasdrq']
actions = ['Up','Left','Down','Right','Restart','Exit','continue']
#action_dict = dict(zip(l_codes,actions*2))
#加入方向键
action_dict = {260:'Left',259:'Up',261:'Right',258:'Down',87: 'Up', 65: 'Left', 83: 'Down', 68: 'Right', 82: 'Restart', 81: 'Exit', 119: 'Up', 97: 'Left', 115: 'Down', 100: 'Right', 114: 'Restart', 113: 'Exit',ord('n'):'Exit',ord('y'):'continue'}
#获取键盘输入
def get_user_action(keyboard):
    char = 'N'
    while char not in action_dict:
        char = keyboard.getch()

    return action_dict[char]
#将矩阵上下倒置
def transpose(field):
    return [list(row) for row in zip(*field)]
#将矩阵左右倒置
def invert(field):
    return [row[::-1] for row in field]


class GameField(object):
    def __init__(self, height=4, width=4, win=32):
        self.height = height
        self.width = width
        self.win_value = win
        self.score = 0
        self.highscore = c.execute("SELECT last from score WHERE id == 0;")
        for row in self.highscore:
            self.highscore = row[0]
        self.reset()
#刷新
    def reset(self):
        self.highscore = c.execute("SELECT last from score WHERE id == 0;")
        for row in self.highscore:
            self.highscore = row[0]
        if self.score > self.highscore:
            self.highscore = self.score
        self.score = 0
        self.field = [[0 for i in range(self.width)] for j in range(self.height)]
        self.spawn()
        self.spawn()
#挑选空地填字
    def spawn(self):
        new_element = 4 if randrange(100) > 89 else 2
        (i, j) = choice([(i, j) for i in range(self.width) for j in range(self.height) if self.field[i][j] == 0])
        self.field[i][j] = new_element
#实现移动操作
    def move(self, direction):
        #定义左移操作，两步，先统统左移，在合并
        def move_row_left(row):
            def tighten(row):  # 左移聚集非零
                new_row = [i for i in row if i != 0]
                new_row += [0 for i in range(len(row) - len(new_row))]
                return new_row
            #合并
            def merge(row):
                pair = False
                new_row = []
                for i in range(len(row)):
                    if pair:
                        new_row.append(2 * row[i])
                        self.score += 2 * row[i]
                        pair = False
                    else:
                        if i + 1 < len(row) and row[i] == row[i + 1]:
                            pair = True
                            new_row.append(0)
                        else:
                            new_row.append(row[i])
                return new_row

            return tighten(merge(tighten(row)))

        moves = {}
        moves['Left'] = lambda field: [move_row_left(row) for row in field]
        moves['Right'] = lambda field:  invert(moves['Left'](invert(field)))
        moves['Up'] = lambda field:  transpose(moves['Left'](transpose(field)))
        moves['Down'] = lambda field: transpose(moves['Right'](transpose(field)))

        if direction in moves:
            if self.move_is_possible(direction):
                self.field = moves[direction](self.field)
                self.spawn()
                return True
            else:
                return False

    def is_win(self):
        return any(any(i >= self.win_value for i in row) for row in self.field)

    def is_gameover(self):
        return not any(self.move_is_possible(move) for move in actions)

    def draw(self, screen):
        help_string1 = '(W)Up (S)Down (A)Left (D)Right'
        help_string2 = '     (R)Restart (Q)Exit'
        gameover_string = '           GAME OVER'
        win_string = '          YOU WIN!\nＡＲＥ　ＹＯＵ　ＣＯＮＴＩＮＵＥ　？（ｙ／ｎ）'

        def cast(string):
            screen.addstr(string + '\n')
        #边框
        def draw_hor_separator():
            line = '+' + ('+------' * self.width + '+')[1:]
            cast(line)

        def draw_row(row):
            cast(''.join('|{: ^5} '.format(num) if num > 0 else '|      ' for num in row) + '|')

        screen.clear()
        cast('SCORE: ' + str(self.score))
        if 0 != self.highscore:
            cast('HIGHSCORE: ' + str(self.highscore))
        for row in self.field:
            draw_hor_separator()
            draw_row(row)
        draw_hor_separator()
        if self.is_win():
            cast(win_string)
        else:
            if self.is_gameover():
                cast(gameover_string)
            else:
                cast(help_string1)
        cast(help_string2)
    #能动不？
    def move_is_possible(self, direction):
        def row_is_left_movable(row):
            def change(i):  # true if there'll be change in i-th tile
                if row[i] == 0 :  # Move
                    return True
                if row[i] != 0 and row[i + 1] == row[i]:  # Merge
                    return True
                return False

            return any(change(i) for i in range(len(row) - 1))
        check = {}
        check['Left'] = lambda field:    any(row_is_left_movable(row) for row in field)
        check['Right'] = lambda field:   check['Left'](invert(field))
        check['Up'] = lambda field: check['Left'](transpose(field))
        check['Down'] = lambda field: check['Right'](transpose(field))
        if direction in check:
            return check[direction](self.field)
        else:
            return False

def main(stdscr):
    def init():
        #重置游戏
        game_field.reset()
        return 'Game'

    def not_game(state):
        # 画出 GameOver 或者 Win 的界面
        heigh_score = c.execute("SELECT last from score WHERE id == 0;")
        for row in heigh_score:
            heigh_score = row[0]
        if game_field.score > heigh_score:
            c.execute("update score set last="+str(game_field.score)+" WHERE id == 0;")
            conn.commit()
        game_field.draw(stdscr)
        game_field.win_value = 2048
        # 读取用户输入得到action，判断是重启游戏还是结束游戏
        action = get_user_action(stdscr)
        responses = defaultdict(lambda: state)  # 默认是当前状态，没有行为就会一直在当前界面循环
        responses['Restart'], responses['Exit'],responses['continue']  = 'Init', 'Exit' ,'Game' # 对应不同的行为转换到不同的状态
        return responses[action]
    def game():
        game_field.draw(stdscr)
        action = get_user_action(stdscr)
        if action == 'Restart':
            return 'Init'
        if action == 'Exit':
            return 'Exit'
        if game_field.move(action):  # move successful
            if game_field.is_win():
                return 'Win'
            if game_field.is_gameover():
                return 'Gameover'
        return 'Game'

    state_actions = {
        'Init': init,
        'Win': lambda: not_game('Win'),
        'Gameover': lambda: not_game('Gameover'),
        'Game': game
    }

    curses.use_default_colors()

    # 设置终结状态最大数值为 32
    game_field = GameField()

    state = 'Init'

    # 状态机开始循环
    while state != 'Exit':
        state = state_actions[state]()
    conn.close()

curses.wrapper(main)

