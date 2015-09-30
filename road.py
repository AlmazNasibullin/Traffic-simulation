"""
Данный класс представляет собой автомобильную многополосную дорогу. Данный класс отвечает
за добавление новых авто на дорогу, обновление координат, скорости тех авто, что уже на дороге,
и непосредственно отрисовку дороги и автомобилей.
"""

import pygame
import random
import time
import queue
import matplotlib.pyplot as plt
import numpy as np
import multiprocessing as mp
import os

import car
import speed_manager

#----colors----
background_color = (0, 150, 10)
cars_colors = [(200, 10, 10),
                (255, 255, 0),
                (240, 140, 10),
                (55, 50, 132)]
black = (0, 0, 0)
blue = (20, 20, 200)
buff = (200, 180, 180)
#--------------

"""
Все константы это блока взяты из статистических данных.
"""
#----cars sizes----
cars_sizes = [18, 15, 36, 54] #[6m, 5m, 12m, 18m]
#------------------

#----accelerations vs decelerations----
accelerations = [7.5, 4.5, 3.6, 2.1]
decelerations = [13.5, 12.0, 12.0, 12.0]
#--------------------------------------

#----cars production----
time_intervals = [[4.0, 2.5, 2.5], [4.0, 1.5, 1.5]]
total_cars_number = [[[200, 200], [720, 80], [720, 80]],
                    [[200, 200], [900, 100], [900, 100]],
                    [[200, 200], [720, 80], [720, 80]]]
#-----------------------

#----max_speeds----
max_speeds = [100.0, 95.0, 85.0, 90.0]
#------------------

#----delta time----
delta_time_for_hour = [900.0, 1800.0, 900.0]
#------------------

def draw_text(text, coords, screen):
   font = pygame.font.Font(None, 20)
   text_to_draw = font.render(text, 1, (255, 255, 255))
   screen.blit(text_to_draw, coords)

class Road:
    def __init__(self, updater, width, height, adaptive_top_speed, on_ramp_start, on_ramp_end):
        self.updater = updater
        self.scr_size = (1290, height)
        self.width = width
        self.height = height
        self.avg_time = 0.0
        self.sd_time = 0.0
        self.avg_consumption = 0.0
        self.sd_consumption = 0.0
        self.avg_emissions = 0.0
        self.sd_emissions = 0.0
        self.adaptive_top_speed = adaptive_top_speed
        self.on_ramp_start = on_ramp_start
        self.on_ramp_end = on_ramp_end

    def produce_car(self, prev_car_time, hour, lane, cars_number, cars, pygame_cars_list,
            cars_queue, last_car):
        # ----cars production----
        time_interval = Road.time_intervals[hour][lane][Road.production_times[lane]]
        if (time.time() - prev_car_time[lane] > time_interval):
            A_B_type_probability = (1.0 * total_cars_number[hour][lane][0]
                / (total_cars_number[hour][lane][0] + total_cars_number[hour][lane][1]))
            A_B = np.random.binomial(1, 1.0 - A_B_type_probability)
            first_or_second = np.random.binomial(1, 0.5)
            car_type = 2 * A_B + first_or_second
            startX = -cars_sizes[car_type]
            if (lane == 0):
                startX += self.on_ramp_start
            cars[lane].append(car.Car(startX, self.height / 2 - 25 * lane + 35,
                lane, max_speeds[car_type], accelerations[car_type], decelerations[car_type],
                cars_sizes[car_type], 6, None, None, self.adaptive_top_speed, cars_colors[car_type], car_type))
            if (last_car[lane] == None):
                last_car[lane] = cars[lane][-1]
                pygame_cars_list[lane].add(last_car[lane])
            else:
                cars_queue[lane].put(cars[lane][-1])
            cars_number[hour][lane][A_B] += 1
            prev_car_time[lane] = time.time()
            Road.production_times[lane] += 1
        # -----------------------

    def add_car_on_road(self, cars_queue, lane, last_car, pygame_cars_list):
        # ----cars adding----
        dist = 25.0
        if (lane == 0):
            dist += self.on_ramp_start
        if (not cars_queue[lane].empty() and last_car[lane].rect.x > dist):
            new_car = cars_queue[lane].get()
            last_car[lane] = new_car
            new_car.find_next(pygame_cars_list)
            pygame_cars_list[lane].add(new_car)
        # -------------------

    def draw(self, full_road, pygame_cars_list, screen, knob, ratio, track, pygame_clock):
        # ----drawing----
        full_road.fill(background_color)
        pygame.draw.rect(full_road, (80, 80, 80), [0, self.height / 2 - 25, self.width, 50])
        for i in range(int(self.width / 15) + 5):
            pygame.draw.rect(full_road, (230, 230, 230), [15 * i, self.height / 2 - 1, 5, 2])
        pygame.draw.rect(full_road, (50, 50, 50), [self.on_ramp_start, self.height / 2 + 25,
            self.on_ramp_end - self.on_ramp_start, 25])
        pygame.draw.polygon(full_road, (50, 50, 50), [(self.on_ramp_end, self.height / 2 + 25),
            (self.on_ramp_end, self.height / 2 + 50), (self.on_ramp_end + 100,
            self.height / 2 + 25)])
        for i in range (car.Car.sections_number):
            draw_text(str(car.Car.sections[i].max_speed[1]), (i * car.Car.each_section_length + 2,
                full_road.get_height() / 2 - 50), full_road)
            draw_text(str(car.Car.sections[i].max_speed[2]), (i * car.Car.each_section_length + 2,
                full_road.get_height() / 2 - 80), full_road)
        for i in range(3):
            pygame_cars_list[i].draw(full_road)
        screen.blit(full_road, ((knob.left / ratio) * -1 , 0))
        pygame.draw.rect(screen, buff, track, 0)
        pygame.draw.rect(screen, blue, knob.inflate(0, -5), 2)
        pygame.display.update()
        pygame_clock.tick(20)
        # ---------------

    def run(self):
        pygame.init()
        pygame_clock = pygame.time.Clock()
        screen = pygame.display.set_mode(self.scr_size)
        screen_rect = screen.get_rect()
        full_road = pygame.Surface((self.width, self.height))
        pygame.display.set_caption('Road')

        # ----scrolling----
        ratio = (1.0 * screen_rect.width) / full_road.get_width()
        scroll_thick = 20
        track = pygame.Rect(screen_rect.left, screen_rect.bottom
            - scroll_thick, screen_rect.width, scroll_thick)   
        knob = pygame.Rect(track)  
        knob.width = track.width * ratio
        scrolling = False
        # -----------------
        
        # ----cars----
        cars_number = [[[0, 0], [0, 0], [0, 0]],
                        [[0, 0], [0, 0], [0, 0]],
                        [[0, 0], [0, 0], [0, 0]]]
        cars = [[],[], []]
        pygame_cars_list = [pygame.sprite.Group(), pygame.sprite.Group(), pygame.sprite.Group()]
        running_process = True
        prev_car_time = [time.time(), time.time(), time.time()]
        cur_time = time.time()
        cars_queue = [queue.Queue(), queue.Queue(), queue.Queue()]
        last_car = [None, None, None]
        # ------------

        #----timing----
        hour = 0
        start_time = time.time()
        #--------------

        """
        В каждый момент времени в этом цикле выполняются при возможности несколько действий:
            1. Обнавляются значения знаков ограничения скорости на каждом из отрезков дороги.
            2. Добавляются новые авто в начало дороги.
            3. Обрабатываются действия пользователя(нажатие каких-то клавиш, закрытие окна).
            4. Выполняется отрисовка дороги, автомобилей.
        """
        while running_process:
            #----update hour----
            if (hour < 3 and time.time() - start_time > delta_time_for_hour[hour]):
                hour += 1
                start_time = time.time()
            #-------------------

            # ----updating max speeds on sections----
            self.updater.update_speeds(pygame_cars_list)
            # ---------------------------------------

            car.Car.delta_time = time.time() - cur_time
            cur_time = time.time()

            # ----cars production----
            if (hour < 3):
                for lane in range(3):
                    self.produce_car(prev_car_time, hour, lane, cars_number, cars,
                        pygame_cars_list, cars_queue, last_car)
            # -----------------------

            # ----cars adding----
            for lane in range(3):
                self.add_car_on_road(cars_queue, lane, last_car, pygame_cars_list)
            # -------------------

            # ----events----
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running_process = False
                elif (event.type == pygame.MOUSEMOTION and scrolling):
                    if event.rel[0] != 0:
                        move = max(event.rel[0], track.left - knob.left)
                        move = min(move, track.right - knob.right)
                        if move != 0:
                            knob.move_ip((move, 0))
                elif (event.type == pygame.MOUSEBUTTONDOWN
                        and knob.collidepoint(event.pos)):
                    scrolling = True
                elif event.type == pygame.MOUSEBUTTONUP:
                    scrolling = False
            # --------------

            for i in range(3):
                pygame_cars_list[i].update(pygame_cars_list)
            # ----drawing----
            self.draw(full_road, pygame_cars_list, screen, knob, ratio, track, pygame_clock)
            # ---------------

            if ((len(cars[1]) > 0 or len(cars[2]) > 0) and cars_queue[1].empty()
                    and pygame_cars_list[1].__len__() == 0 and cars_queue[2].empty()
                    and pygame_cars_list[2].__len__() == 0):
                running_process = False

        pygame.quit()
        return (self.avg_time, self.sd_time, self.avg_consumption, self.sd_consumption,
            self.avg_emissions, self.sd_emissions, cars_number)