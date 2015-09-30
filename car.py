"""
Данный класс описывает автомобиль. Содержит полное описание автомобиля и отвечает за корректное
поведение автомобиля на дороге, а именно, корректное обновление координаты по ходу движения,
обновление полосы движения, его скорости и ускорения.
Обновление скорости, ускорения, полосы движения происходит согласно принципу безаварийного
движения, что имеет строгую математическую интерпретацию и выражается в математических формулах.
Помимо этого класс car считает количество потребляемого топлива, опираясь на математическую
модель VT-micro.
"""

import pygame
import time
import numpy as np
import math
import random

jam_speed = 10.0
trash_speed = 40.0

max_acceleration = 8.34

"""
Коэффициенты 'consumption_coefficients' были взяты из модели VT-micro, оценивающая расход топлива
автомобиля в зависимости от текущих скорости и ускорения. 
"""
consumption_coefficients = [[[-0.679439, 0.029665, -0.000276, 0.0000015],
                            [0.135273, 0.004808, -0.000020, 5.5409E-8],
                            [0.015946, 0.000083, 0.0000009, -2.47964E-8],
                            [-0.001189, -0.000061, 0.0000003, -4.467234E-9]],
                            
                            [[0.887447, 0.070994, -0.000786, 0.0000046],
                           [0.148841, 0.003870, 0.0000932, -0.0000007],
                            [0.030550, -0.000926, 0.0000491, -0.0000003],
                            [-0.001348, 0.0000461, -0.00000141, 8.1724E-9]]]

coeff = [100.0 * 4.0, 1.0  * 3.6 / 1000.0]

def get_cons(speed, acc, k):
    consumption = 0.0
    for i in range(0, 4):
        for j in range(0, 4):
            consumption += (consumption_coefficients[k][i][j] * pow(acc, i) * pow(speed / 1.08, j))
    return consumption

def calculate_consumption(prev_speed, new_speed, k):
    acc = (new_speed - prev_speed) / Car.delta_time
    speed = new_speed
    consumption = 0.0
    if (abs(acc) > 10):
        consumption = 0.0
        delta_acc = 2.0
        if (acc < 0.0):
            delta_acc = -2.0
        for i in range(int(abs(acc / delta_acc))):
            consumption += get_cons(speed, delta_acc, k)
            speed += delta_acc
    else:
        consumption = get_cons(speed, acc, k)
    if (consumption > 20.0):
        return 0
    return math.exp(consumption) * coeff[k] / (speed + 1.0)

def get_safe_distance(speed):
    return speed * 0.15 + 8.5

def get_safe_speed(speed, next_speed, x_coordinate, next_x_coordinate, width, dec):
    if (x_coordinate >= next_x_coordinate - 10.0):
        return next_speed
    if (speed <= next_speed):
        return 200.0
    reaction_time = 0.5
    dist_between_cars = next_x_coordinate - x_coordinate - width
    braking_time = (speed - next_speed) / dec
    safe_speed = (next_speed + (dist_between_cars - get_safe_distance(speed))
        / (braking_time + reaction_time))
    return safe_speed

def get_safe_speed_agressive(speed, next_speed, x_coordinate, next_x_coordinate, width, dec):
    if (x_coordinate >= next_x_coordinate - 10.0):
        return next_speed
    if (speed <= next_speed):
        return 200.0
    reaction_time = 0.5
    dist_between_cars = next_x_coordinate - x_coordinate - width
    braking_time = (speed - next_speed) / dec
    safe_speed = (next_speed + (dist_between_cars - get_safe_distance(speed))
        / (braking_time + reaction_time))
    agressive_coefficient = 1.2
    if (speed < 20.0):
        agressive_coefficient = 1.5
    safe_speed += dec * braking_time * braking_time / (2.0 * (braking_time + reaction_time))
    return safe_speed


class Car(pygame.sprite.Sprite):
    def __init__(self, startX, startY, lane, self_top_speed, acceleration, deceleration, width,
            height, nextt, prev, adaptive_top_speed, color, car_type):
        pygame.sprite.Sprite.__init__(self)
        self.self_top_speed = self_top_speed
        if (lane > 0):
            self.speed = self_top_speed
            self.cur_top_speed = [self_top_speed, self_top_speed, self_top_speed]
        else:
            self.speed = 0.8 * self_top_speed
            self.cur_top_speed = [0.8 * self_top_speed, 0.8 * self_top_speed, 0.8 * self_top_speed]
        self.acceleration = random.uniform(0.95 * acceleration, 1.05 * acceleration)
        self.deceleration = random.uniform(0.95 * deceleration, 1.05 * deceleration)
        self.width = width
        self.image = pygame.Surface((width, height))
        self.image.fill(color)
        self.rect = pygame.Rect(startX, startY, width, height)
        self.startX = startX
        self.x_coordinate = 1.0 * startX
        self.y_coordinate = 1.0 * startY
        self.lane = lane
        self.start_time = time.time()
        self.life_time = 0.0
        self.prev = prev
        self.next = nextt
        self.top_speed_updated_times = 0
        self.adaptive_top_speed = adaptive_top_speed
        self.consumption = 0.0
        self.emissions = 0.0
        self.consumption_number = 1
        self.movement_up = False
        self.movement_down = False
        self.car_type = car_type
        self.braking_probability = [0.0, 0.0, 0.0]
        if (self.lane == 0):
            self.braking_probability = [0.0, 0.2, 0.0]
        self.time_on_left = time.time()
        self.speed_increased = False
        self.decel_start = time.time() - 10000.0
        self.decel_duration = 0.0
        self.decel_prev_attempt = time.time()
        self.br_pr = 0.3
        self.only_right = False
        if (np.random.binomial(1, 0.2) == 1):
            self.only_right = True

    def find_next(self, cars_list):
        for carr in cars_list[self.lane]:
            if (carr != self):
                if (self.next == None):
                    self.next = carr
                else:
                    if (carr.x_coordinate < self.next.x_coordinate):
                        self.next = carr
        if (self.next != None):
            self.next.prev = self

    def update_top_speed(self):
        if (Car.each_section_length * self.top_speed_updated_times < self.rect.x
                and self.lane != 0):
            for lane in range(1, 3):
                minimum = min(Car.sections[self.top_speed_updated_times].max_speed[lane],
                    self.self_top_speed)
                self.cur_top_speed[lane] = random.uniform(0.95 * minimum, 1.01 * minimum)
            self.speed_increased = False
            self.top_speed_updated_times += 1
    
    def get_safe_speed(self):
        if (self.next == None or self.speed <= self.next.speed):
            return 200.0
        if (self.x_coordinate >= self.next.x_coordinate - 10.0):
            return self.next.speed
        reaction_time = 1.0
        dist_between_cars = self.next.x_coordinate - self.x_coordinate - self.width
        braking_time = (self.speed - self.next.speed) / self.deceleration
        safe_speed = (self.next.speed + (dist_between_cars - get_safe_distance(self.speed))
            / (braking_time + reaction_time))
        return safe_speed

    def find_prev_next(self, desirable_lane, cars_list):
        prev = None
        nextt = None
        intersection = False
        start = self.x_coordinate
        end = self.x_coordinate + self.width
        for carr in cars_list[desirable_lane].sprites():
            car_start = carr.x_coordinate
            car_end = carr.x_coordinate + carr.width
            if ((start >= car_start and start <= car_end) or (end >= car_start and end <= car_end)
                    or (car_start >= start and car_start <= end) 
                    or (car_end >= start and car_end <= end)):
                intersection = True
                break
            if (car_end < start and (prev == None or car_start > prev.x_coordinate)):
                prev = carr
            if (car_start > end and (nextt == None or car_start < nextt.x_coordinate)):
                nextt = carr
        return prev, nextt, intersection

    def is_safe_moving(self, intersection, prev, nextt):
        if (intersection == True):
            return False
        same_lane = True
        if (prev != None):
            safe_speed_for_prev = get_safe_speed(prev.speed, self.speed, prev.x_coordinate,
                self.x_coordinate, prev.width, prev.deceleration)
            if (self.lane == 0):
                safe_speed = get_safe_speed_agressive(prev.speed, self.speed, prev.x_coordinate,
                self.x_coordinate, prev.width, prev.deceleration)
            dist = self.x_coordinate - (prev.x_coordinate + prev.width)
            desirable_dist = get_safe_distance(prev.speed)
            if (prev.speed - 5 < safe_speed_for_prev and dist > desirable_dist):
                same_lane = False
        else:
            same_lane = False
        if (nextt != None and same_lane == False):
            safe_speed_for_me = get_safe_speed(self.speed, nextt.speed, self.x_coordinate,
                nextt.x_coordinate, self.width, self.deceleration)
            if (self.lane == 0):
                safe_speed = get_safe_speed_agressive(self.speed, nextt.speed, self.x_coordinate,
                nextt.x_coordinate, self.width, self.deceleration)
            dist = nextt.x_coordinate - (self.x_coordinate + self.width)
            desirable_dist = get_safe_distance(self.speed)
            if (self.speed >= safe_speed_for_me + 5 or dist < desirable_dist):
                same_lane = True
        return not same_lane

    def make_movement_down(self):
        self.y_coordinate += (Car.delta_time * 20)
        if (self.y_coordinate >= Car.height / 2 + 10):
            self.movement_down = False
            self.y_coordinate = Car.height / 2 + 10
        self.rect.y = self.y_coordinate

    def make_movement_up(self):
        self.y_coordinate -= (Car.delta_time * 20)
        if (self.lane == 1):
            if (self.y_coordinate <= Car.height / 2 + 10):
                self.movement_up = False
                self.y_coordinate = Car.height / 2 + 10
                if (self.speed < 40.0):
                    self.braking_probability[1] = 0.01
        elif (self.lane == 2):
            if (self.y_coordinate <= Car.height / 2 - 15):
                self.movement_up = False
                self.y_coordinate = Car.height / 2 - 15
                self.time_on_left = time.time()
                self.speed_increased = False
        self.rect.y = self.y_coordinate

    def update(self, cars_list):
        if (self.lane == 2 and not self.speed_increased and time.time() - self.time_on_left > 10.0):
            self.cur_top_speed[self.lane] += 10.0
            self.speed_increased = True
            self.time_on_left = time.time()

        if (self.braking_probability[1] == 0.2 and self.x_coordinate > Car.on_ramp_end + 2000.0):
            self.braking_probability[1] = 0.0

        self.update_top_speed()
        
        if (self.movement_down):
            self.make_movement_down()

        if (self.movement_up):
            self.make_movement_up()

        if (self.lane == 2 and not self.movement_down and not self.movement_up and self.x_coordinate > 50.0):
            prev, nextt, intersection = self.find_prev_next(1, cars_list)
            safe_speed = self.get_safe_speed()
            safe_speed_other = 200.0
            if (nextt != None):
                safe_speed_other = get_safe_speed(self.speed, nextt.speed, self.x_coordinate,
                    nextt.x_coordinate, self.width, self.deceleration)
            if (safe_speed > self.cur_top_speed[2] and safe_speed_other > self.cur_top_speed[1]
                    and self.is_safe_moving(intersection, prev, nextt)):
                if (self.prev != None):
                    self.prev.next = self.next
                if (self.next != None):
                    self.next.prev = self.prev
                self.next = nextt
                self.prev = prev
                if (prev != None):
                    prev.next = self
                if (nextt != None):
                    nextt.prev = self
                self.lane = 1
                cars_list[2].remove(self)
                cars_list[1].add(self)
                self.movement_down = True

        if (self.lane == 1 and not self.movement_down and not self.movement_up and not self.only_right and self.x_coordinate > 50.0):
            prev, nextt, intersection = self.find_prev_next(2, cars_list)
            safe_speed = self.get_safe_speed()
            safe_speed_other = 200.0
            if (nextt != None):
                safe_speed_other = get_safe_speed(self.speed, nextt.speed, self.x_coordinate,
                    nextt.x_coordinate, self.width, self.deceleration)
            congested = (safe_speed < trash_speed) and (safe_speed_other < trash_speed)
            if (safe_speed < self.cur_top_speed[1] and not congested
                    and self.is_safe_moving(intersection, prev, nextt)):
                if (self.prev != None):
                    self.prev.next = self.next
                if (self.next != None):
                    self.next.prev = self.prev
                self.next = nextt
                self.prev = prev
                if (prev != None):
                    prev.next = self
                if (nextt != None):
                    nextt.prev = self
                self.lane = 2
                cars_list[1].remove(self)
                cars_list[2].add(self)
                self.movement_up = True

        if (self.lane == 0 and self.x_coordinate > 50.0 + Car.on_ramp_start):
            prev, nextt, intersection = self.find_prev_next(1,cars_list)
            if (self.is_safe_moving(intersection, prev, nextt)):
                if (self.prev != None):
                    self.prev.next = self.next
                if (self.next != None):
                    self.next.prev = self.prev
                self.next = nextt
                self.prev = prev
                if (prev != None):
                    self.next = prev.next
                    prev.next = self
                if (nextt != None):
                    self.prev = nextt.prev
                    nextt.prev = self
                self.lane = 1
                cars_list[0].remove(self)
                cars_list[1].add(self)
                self.movement_up = True

        if (self.speed < 40.0):
            self.br_pr = 0.05
        else:
            if (self.lane == 2):
                self.br_pr = 0.08
            else:
                self.br_pr = 0.3
        if (self.x_coordinate > Car.on_ramp_end):
            self.br_pr = 0.05
        
        new_speed = 0.0
        safe_speed = 0.0
        if (self.speed > self.cur_top_speed[self.lane]):
            new_speed = self.speed - self.deceleration * Car.delta_time
        else:
            if (self.lane == 0 and self.next == None):
                    safe_speed = get_safe_speed(self.speed, 0.0, self.x_coordinate, Car.on_ramp_end,
                        self.width, self.deceleration)
            else:
                safe_speed = self.get_safe_speed()

            new_speed = min(self.cur_top_speed[self.lane], self.speed
                + self.acceleration * Car.delta_time, safe_speed)
            if (np.random.binomial(1, self.br_pr) == 1):
                new_speed -= self.deceleration * Car.delta_time

            if (self.lane > 0):
                new_speed = max(new_speed, 10.0)
            else:
                new_speed = max(new_speed, 0.0)

        self.consumption += calculate_consumption(self.speed, new_speed, 0)
        self.emissions += calculate_consumption(self.speed, new_speed, 1)
        self.consumption_number += 1
        self.speed = new_speed
        self.consumption_number += 1

        self.x_coordinate += self.speed * Car.delta_time
        self.rect.x = self.x_coordinate

        if (self.rect.x > Car.road_length):
            self.life_time = time.time() - self.start_time
            self.consumption /= self.consumption_number
            self.emissions /= self.consumption_number
            self.x_coordinate = 100000.0
            cars_list[self.lane].remove(self)
    
    def draw(self, screen):
        screen.blit(self.image, (self.rect.x, self.rect.y))