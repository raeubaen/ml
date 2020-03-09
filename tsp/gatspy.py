##THE GREAT G.A.T.S.PY
# Genetic Algoritm for Travelling Salesman problem in PYthon

import random
import pandas as pd
import matplotlib.pyplot as plt
import PySimpleGUI as sg
import numpy as np
import sys
import argparse
import os


if not os.path.exists("data"):
    os.makedirs("data")
data_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __sub__(self, point2):
        dx = self.x - point2.x
        dy = self.y - point2.y
        dist = np.sqrt((dx ** 2) + (dy ** 2))
        return dist


class Path(list):
    @property
    def length(self):
        length = 0
        cities_num = len(self)
        for i in range(cities_num):
            prev_city = self[i]
            if i != cities_num - 1:
                next_city = self[i + 1]
            else:
                next_city = self[0]
            length += prev_city - next_city
        return length

    @property
    def loss(self):
        return -1 / self.length

    # returns child - ordered crossover;
    # gene taken from parent1 is inserted within parent2 and remanining basis are shifted without changing the order
    def __and__(self, parent2):
        child, temp = [], []
        ind1 = int(random.random() * len(self))
        ind2 = int(random.random() * len(self))
        start_ind = min(ind1, ind2)
        end_ind = max(ind1, ind2)
        for i in range(start_ind, end_ind):
            temp.append(self[i])
        child = temp + [item for item in parent2 if item not in temp]
        return self.__class__(child)

    def mutate(self, mutation_rate):
        for swapped in range(len(self)):
            if random.random() < mutation_rate:
                swap_with = int(random.random() * len(self))
                temp = self[swap_with]
                self[swap_with] = self[swapped]
                self[swapped] = temp
        return self


#bound to Population class
def modify_path_list(f):
        def wrapper(self):
            self.pl = f(self, self.pl)
            return self
        return wrapper

class Population():
    def __init__(self, path_list):
        self.pl = path_list
        
    def set_params(self, elite_num=None, mutation_rate=None):
        self.elite_num, self.mutation_rate = elite_num, mutation_rate
        if elite_num is None:
            self.elite_num = len(self) // 5
        if mutation_rate is None:
            self.mutation_rate = 0.01
    @property
    def total_loss(self):
        total_loss = 0
        for path in self.pl:
            total_loss += path.loss
        return -total_loss

    @modify_path_list
    def rank_paths(self, pl):
        return sorted(pl, key=lambda x: x.loss)
        
    @modify_path_list
    def select(self, pl):
        selected = pl[:self.elite_num]
        s = {i: pl[i].loss for i in range(len(pl))}
        df = pd.DataFrame(s.items(), columns=["", "loss"])
        df["cumulative_sum"] = df.loss.cumsum()
        df["freq"] = (
            df.cumulative_sum / df.loss.sum()
        )  # weights individuals loss over the whole population
        # higher loss - more copies
        for i in range(len(pl) - elite_num):
            rand = random.random()
            for i in range(len(pl)):
                if df.iat[i, 3] > rand:  # iac is 10x faster then iloc[i]['freq']
                    selected.append(pl[i])
                    break
        return selected

    @modify_path_list
    def breed(self, pl):
        children = pl[:self.elite_num]
        non_elite = random.sample(pl, len(pl))
        length = len(pl) - elite_num
        for i in range(length):
            # to be sure everyone respects monogamy and every couple has exactly 2 children
            child = non_elite[i] & non_elite[len(pl) - i - 1]
            children.append(child)
        return children

    @modify_path_list
    def mutate(self, pl):
        return [path.mutate(self.mutation_rate) for path in pl]

    def next_generation(self):
        return self.rank_paths().select().breed().mutate()


def to_plot(path):
    return ([p.x for p in path] + [path[0].x], [p.y for p in path] + [path[0].y])


def save_path(path, file_name):
    pd.DataFrame(
        [[p.x, p.y] for p in path], 
        columns=["x", "y"]
    ).to_csv(file_name)


def evolve(population, generations_num, to_save):
    print(f"Initial distance: { - 1/population.rank_paths().pl[0].loss}")
    distances = []
    fig, ax = plt.subplots()
    data = to_plot(population.pl[0])
    lines = ax.plot(data[0], data[1], marker="o")
    fig.canvas.manager.show()
    for i in range(generations_num):
        population = population.next_generation()
        best_path = population.rank_paths().pl[0]
        distances.append(best_path.loss)
        print(f"Gen: {i} --- Loss: {best_path.loss}")
        if i % 20 == 0:
            data = to_plot(best_path)
            lines[0].set_data(data[0], data[1])
            fig.canvas.draw()
            fig.canvas.flush_events()
    if to_save: 
        plt.savefig(os.path.join(data_path, "final_path.png"))
        save_path(best_path, os.path.join(data_path, "final_path.csv"))
    plt.close()
    plt.plot(range(len(distances)), distances)
    plt.ylabel("Distance")
    plt.xlabel("Generation")
    plt.ion()
    plt.show()
    if to_save: plt.savefig(os.path.join(data_path, "progress.png"))
    # update figure, calc stuff
    plt.pause(10)
    print(f"Final distance: {- 1 / best_path.loss}")
    return best_path


def gui_choose_points(points_num):
    path = Path([])
    BOX_SIZE = 25
    layout = [
        [sg.Text(f"Choose {points_num} points", key="-OUTPUT-")],
        [sg.Graph((800, 800), (0, 450), (450, 0), key="-GRAPH-", change_submits=True, drag_submits=False)],
        [sg.Button("Show"), sg.Button("Exit")],
    ]
    window = sg.Window("THE GREAT G.A.T.S.PY", layout, finalize=True)
    g = window["-GRAPH-"]
    t = window["-OUTPUT-"]
    g.draw_rectangle((BOX_SIZE, BOX_SIZE), (BOX_SIZE, BOX_SIZE))
    while len(path) < points_num:
        event, values = window.read()
        if event in (None, "Exit"):
            break
        mouse = values["-GRAPH-"]
        if event == "-GRAPH-":
            if mouse == (None, None):
                continue
            box_x = mouse[0]
            box_y = mouse[1]
            path.append(Point(box_x / BOX_SIZE, box_y / BOX_SIZE))
            g.draw_circle((box_x, box_y), 5, fill_color="black", line_color="white")
            print(f"Chosen point: ({box_x}, {box_y})")
            t.update(value=f"Choose {points_num - len(path)} points")
    window.close()
    return path


parser = argparse.ArgumentParser(description="THE GREAT G.A.T.S.PY --- Genetic Algoritm for Travelling Salesman problem in PYthon")
parser.add_argument("--rand", default=False, action="store_true", help="extract points randomly (default: False)")
parser.add_argument("--save", default=False, action="store_true", help="saves pictures and best path data (default: False)")
parser.add_argument("-c", type=int, default=30, help="number of cities when extracted randomly (default: 50)")
parser.add_argument("-s", type=int, default=100, help="size of populations (default: 100)")
parser.add_argument("-g", type=int, default=700, help="number of generations (default: 700)")
parser.add_argument("-e", type=int, default=30, help="number of elite individuals (default: 50)")
parser.add_argument("-m", type=float, default=0.005, help="mutation rate (default: 0.005)")
args = parser.parse_args()

points_num = args.c
population_size = args.s
generations_num = args.g
elite_num = args.e  # better near 30%
mutation_rate = (args.m)  # if it's 0, convergence is faster but progress curve is a broken line

if not args.rand:
    initial_path = gui_choose_points(points_num)
else:
    initial_path = Path(
        [
            Point(x=int(random.random() * 200), y=int(random.random() * 200))
            for i in range(points_num)
        ]
    )

if args.save: save_path(initial_path, os.path.join(data_path, "initial_path.csv"))
initial_population = Population([initial_path] * population_size)
initial_population.set_params(elite_num=elite_num, mutation_rate=mutation_rate)
evolve(initial_population, generations_num, args.save)
