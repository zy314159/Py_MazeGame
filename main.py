import pygame
import random
import sys
from collections import deque
import heapq
import sqlite3

# 定义常量
TILE_SIZE = 20  # 缩小单元格大小
MAZE_WIDTH = 40  # 增加迷宫的宽度
MAZE_HEIGHT = 40  # 增加迷宫的高度
WINDOW_WIDTH = MAZE_WIDTH * TILE_SIZE
WINDOW_HEIGHT = MAZE_HEIGHT * TILE_SIZE

# 定义颜色
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
BLUE = (0, 0, 255)
GREEN = (0, 255, 0)
RED = (255, 0, 0)
YELLOW = (255, 255, 0)
PURPLE = (128, 0, 128)

# 初始化Pygame
pygame.init()
screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
pygame.display.set_caption("Maze Game")

# 生成迷宫
def generate_maze():
    maze = [[1 for _ in range(MAZE_WIDTH)] for _ in range(MAZE_HEIGHT)]
    stack = [(1, 1)]
    maze[1][1] = 0

    while stack:
        x, y = stack[-1]
        neighbors = []

        for dx, dy in [(-2, 0), (2, 0), (0, -2), (0, 2)]:
            nx, ny = x + dx, y + dy
            if 0 < nx < MAZE_WIDTH - 1 and 0 < ny < MAZE_HEIGHT - 1 and maze[ny][nx] == 1:
                neighbors.append((nx, ny))

        if neighbors:
            nx, ny = random.choice(neighbors)
            maze[(y + ny) // 2][(x + nx) // 2] = 0
            maze[ny][nx] = 0
            stack.append((nx, ny))
        else:
            stack.pop()

    # 增加随机通路
    for _ in range(MAZE_WIDTH * MAZE_HEIGHT // 5):
        x, y = random.randint(1, MAZE_WIDTH - 2), random.randint(1, MAZE_HEIGHT - 2)
        maze[y][x] = 0

    return maze

# 确保迷宫有解
def ensure_maze_has_solution(maze, entrance, exit):
    path = find_path(maze, entrance, exit)
    while not path:
        maze = generate_maze()
        path = find_path(maze, entrance, exit)
    return maze

# 从文件中加载迷宫
def load_maze_from_file(filename):
    with open(filename, 'r') as file:
        width, height = map(int, file.readline().split())
        entrance = tuple(map(int, file.readline().split()))
        exit = tuple(map(int, file.readline().split()))
        maze = [list(map(int, file.readline().split())) for _ in range(height)]
    return maze, entrance, exit

# 保存迷宫到文件
def save_maze_to_file(filename, maze, entrance, exit):
    with open(filename, 'w') as file:
        file.write(f"{MAZE_WIDTH} {MAZE_HEIGHT}\n")
        file.write(f"{entrance[0]} {entrance[1]}\n")
        file.write(f"{exit[0]} {exit[1]}\n")
        for row in maze:
            file.write(" ".join(map(str, row)) + "\n")

# 从数据库中加载迷宫
def load_maze_from_db(db_name):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute("SELECT width, height, entrance_x, entrance_y, exit_x, exit_y FROM maze_info")
    width, height, entrance_x, entrance_y, exit_x, exit_y = cursor.fetchone()
    entrance = (entrance_x, entrance_y)
    exit = (exit_x, exit_y)
    cursor.execute("SELECT row, col, value FROM maze_data")
    maze = [[1 for _ in range(width)] for _ in range(height)]
    for row, col, value in cursor.fetchall():
        maze[row][col] = value
    conn.close()
    return maze, entrance, exit

# 保存迷宫到数据库
def save_maze_to_db(db_name, maze, entrance, exit):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS maze_info (width INTEGER, height INTEGER, entrance_x INTEGER, entrance_y INTEGER, exit_x INTEGER, exit_y INTEGER)")
    cursor.execute("DELETE FROM maze_info")
    cursor.execute("INSERT INTO maze_info (width, height, entrance_x, entrance_y, exit_x, exit_y) VALUES (?, ?, ?, ?, ?, ?)",
                   (MAZE_WIDTH, MAZE_HEIGHT, entrance[0], entrance[1], exit[0], exit[1]))
    cursor.execute("CREATE TABLE IF NOT EXISTS maze_data (row INTEGER, col INTEGER, value INTEGER)")
    cursor.execute("DELETE FROM maze_data")
    for row in range(MAZE_HEIGHT):
        for col in range(MAZE_WIDTH):
            cursor.execute("INSERT INTO maze_data (row, col, value) VALUES (?, ?, ?)", (row, col, maze[row][col]))
    conn.commit()
    conn.close()

# 保存游戏数据到数据库
def save_game_data_to_db(db_name, player_moves, monster_moves):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS game_data (id INTEGER PRIMARY KEY, player_x INTEGER, player_y INTEGER, monster_x INTEGER, monster_y INTEGER)")
    cursor.execute("DELETE FROM game_data")
    for i in range(len(player_moves)):
        cursor.execute("INSERT INTO game_data (player_x, player_y, monster_x, monster_y) VALUES (?, ?, ?, ?)",
                       (player_moves[i][0], player_moves[i][1], monster_moves[i][0], monster_moves[i][1]))
    conn.commit()
    conn.close()

# 寻找路径
def find_path(maze, entrance, exit):
    directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    queue = deque([entrance])
    visited = set()
    visited.add(entrance)
    parent = {entrance: None}

    while queue:
        current = queue.popleft()
        if current == exit:
            path = []
            while current:
                path.append(current)
                current = parent[current]
            path.reverse()
            return path

        for dx, dy in directions:
            neighbor = (current[0] + dx, current[1] + dy)
            if 0 <= neighbor[0] < MAZE_WIDTH and 0 <= neighbor[1] < MAZE_HEIGHT and maze[neighbor[1]][neighbor[0]] == 0 and neighbor not in visited:
                queue.append(neighbor)
                visited.add(neighbor)
                parent[neighbor] = current

    return []

# A*算法
def heuristic(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])

def a_star(maze, start, goal):
    directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    open_set = []
    heapq.heappush(open_set, (0, start))
    came_from = {}
    g_score = {start: 0}
    f_score = {start: heuristic(start, goal)}

    while open_set:
        _, current = heapq.heappop(open_set)

        if current == goal:
            path = []
            while current in came_from:
                path.append(current)
                current = came_from[current]
            path.reverse()
            return path

        for dx, dy in directions:
            neighbor = (current[0] + dx, current[1] + dy)
            if 0 <= neighbor[0] < MAZE_WIDTH and 0 <= neighbor[1] < MAZE_HEIGHT and maze[neighbor[1]][neighbor[0]] == 0:
                tentative_g_score = g_score[current] + 1
                if neighbor not in g_score or tentative_g_score < g_score[neighbor]:
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g_score
                    f_score[neighbor] = tentative_g_score + heuristic(neighbor, goal)
                    heapq.heappush(open_set, (f_score[neighbor], neighbor))

    return []

# 绘制迷宫
def draw_maze(screen, maze, path, entrance, exit, player_pos, monster, lives, show_path):
    screen.fill(WHITE)
    for y in range(MAZE_HEIGHT):
        for x in range(MAZE_WIDTH):
            rect = pygame.Rect(x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE)
            if maze[y][x] == 1:
                pygame.draw.rect(screen, BLUE, rect)
            elif show_path and (x, y) in path:
                pygame.draw.rect(screen, GREEN, rect)
                if (x, y) != entrance and (x, y) != exit:
                    next_pos = path[path.index((x, y)) + 1]
                    draw_arrow(screen, (x, y), next_pos)
            else:
                pygame.draw.rect(screen, WHITE, rect)
            pygame.draw.rect(screen, BLACK, rect, 1)

    pygame.draw.rect(screen, YELLOW, (entrance[0] * TILE_SIZE, entrance[1] * TILE_SIZE, TILE_SIZE, TILE_SIZE))
    pygame.draw.rect(screen, PURPLE, (exit[0] * TILE_SIZE, exit[1] * TILE_SIZE, TILE_SIZE, TILE_SIZE))
    pygame.draw.rect(screen, RED, (player_pos[0] * TILE_SIZE, player_pos[1] * TILE_SIZE, TILE_SIZE, TILE_SIZE))
    pygame.draw.rect(screen, BLACK, (monster[0] * TILE_SIZE, monster[1] * TILE_SIZE, TILE_SIZE, TILE_SIZE))

    font = pygame.font.SysFont(None, 36)
    text = font.render(f"Lives: {lives}", True, BLACK)
    screen.blit(text, (10, 10))

    auto_path_button = pygame.Rect(10, 50, 150, 40)
    pygame.draw.rect(screen, BLACK, auto_path_button)
    text = font.render("Show Path", True, WHITE)
    screen.blit(text, (20, 55))

    pygame.display.flip()

# 绘制箭头
def draw_arrow(screen, start, end):
    start_pos = (start[0] * TILE_SIZE + TILE_SIZE // 2, start[1] * TILE_SIZE + TILE_SIZE // 2)
    end_pos = (end[0] * TILE_SIZE + TILE_SIZE // 2, end[1] * TILE_SIZE + TILE_SIZE // 2)
    pygame.draw.line(screen, RED, start_pos, end_pos, 3)
    angle = pygame.math.Vector2(end_pos[0] - start_pos[0], end_pos[1] - start_pos[1]).angle_to((1, 0))
    arrow_head = pygame.transform.rotate(pygame.Surface((10, 10), pygame.SRCALPHA), -angle)
    pygame.draw.polygon(arrow_head, RED, [(0, 0), (10, 5), (0, 10)])
    screen.blit(arrow_head, (end_pos[0] - 5, end_pos[1] - 5))

# 移动怪物
def move_monster(maze, monster, player_pos, move_counter):
    if move_counter % 2 == 0:  # 降低怪物移动速度
        path = a_star(maze, tuple(monster), tuple(player_pos))
        if path:
            monster[0], monster[1] = path[0]

# 重生怪物
def respawn_monster(maze):
    while True:
        x, y = random.randint(1, MAZE_WIDTH - 2), random.randint(1, MAZE_HEIGHT - 2)
        if maze[y][x] == 0:
            return [x, y]

def main():
    maze = generate_maze()
    entrance = (1, 1)
    exit = (MAZE_WIDTH - 2, MAZE_HEIGHT - 2)
    maze[entrance[1]][entrance[0]] = 0
    maze[exit[1]][exit[0]] = 0
    maze = ensure_maze_has_solution(maze, entrance, exit)
    save_maze_to_file("maze.txt", maze, entrance, exit)
    maze, entrance, exit = load_maze_from_file("maze.txt")
    path = find_path(maze, entrance, exit)

    player_pos = list(entrance)
    monster = respawn_monster(maze)
    lives = 3
    show_path = False

    player_moves = []
    monster_moves = []

    clock = pygame.time.Clock()
    move_counter = 0

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                save_game_data_to_db("game_data.db", player_moves, monster_moves)
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key in [pygame.K_w, pygame.K_UP] and maze[player_pos[1] - 1][player_pos[0]] == 0:
                    player_pos[1] -= 1
                elif event.key in [pygame.K_s, pygame.K_DOWN] and maze[player_pos[1] + 1][player_pos[0]] == 0:
                    player_pos[1] += 1
                elif event.key in [pygame.K_a, pygame.K_LEFT] and maze[player_pos[1]][player_pos[0] - 1] == 0:
                    player_pos[0] -= 1
                elif event.key in [pygame.K_d, pygame.K_RIGHT] and maze[player_pos[1]][player_pos[0] + 1] == 0:
                    player_pos[0] += 1
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    mouse_pos = event.pos
                    if 10 <= mouse_pos[0] <= 160 and 50 <= mouse_pos[1] <= 90:
                        show_path = not show_path

        if tuple(player_pos) == exit:
            print("You win!")
            save_game_data_to_db("game_data.db", player_moves, monster_moves)
            pygame.quit()
            sys.exit()

        move_monster(maze, monster, player_pos, move_counter)
        move_counter += 1

        player_moves.append(tuple(player_pos))
        monster_moves.append(tuple(monster))

        if tuple(player_pos) == tuple(monster):
            lives -= 1
            player_pos = list(entrance)  # 玩家重生在起点
            monster = respawn_monster(maze)  # 怪物随机重生
            if lives == 0:
                print("Game over!")
                save_game_data_to_db("game_data.db", player_moves, monster_moves)
                pygame.quit()
                sys.exit()

        draw_maze(screen, maze, path, entrance, exit, player_pos, monster, lives, show_path)
        clock.tick(10)

if __name__ == "__main__":
    main()