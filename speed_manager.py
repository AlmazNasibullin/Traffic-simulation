"""
Данный класс отвечает за работу системы динамических дорожных знаком ограничения скорости(ДДЗОС).
Управление динамическими дорожными знаками ограничения скорости(ДДЗОС) происходит следующим образом:
Вся дорога разбита на несколько секций, в конце каждой секции есть ДДЗОС для каждой полосы свой.
С некоторым интервалом происходит обновление значения скорости на каждом из ДДЗОС
в зависимости от дорожной обстановки. Рассматриваются несколько вариантов алгоритма обновления
скорости.
"""

import time
import numpy as np

import car

class Section():
    def __init__(self, start, end, max_speed):
        self.start = start
        self.end = end
        self.max_speed = [max_speed, max_speed, max_speed]
        self.last_update = [time.time(), time.time(), time.time()]

def get_reducing_coefficient(max_speed):
    if (max_speed < 80):
        return 0.9
    if (max_speed < 100):
        return 0.87
    return 0.85

class Updater():
    def __init__(self, road_length, each_section_length, algorithm, adaptive_top_speed,
            max_speed = 100.0, slow_cars_coefficient = 0.7, steps_backword = 1):
        self.road_length = road_length
        self.each_section_length = each_section_length
        self.max_speed = max_speed
        self.algorithm = algorithm
        self.adaptive_top_speed = adaptive_top_speed
        self.slow_cars_coefficient = slow_cars_coefficient
        self.reducing_coefficient = get_reducing_coefficient(max_speed)
        self.steps_backword = steps_backword
        self.last_update_time = time.time()
        self.last_update_time_each_lane = [time.time(), time.time(), time.time()]
        self.reduced = False

    def fill_sections(self):
        car.Car.sections = []
        car.Car.sections_number = 0
        car.Car.each_section_length = self.each_section_length
        cur_section_start = 0
        cur_section_end = car.Car.each_section_length
        while (cur_section_start < self.road_length):
            car.Car.sections_number += 1
            car.Car.sections.append(Section(cur_section_start, min(cur_section_end,
                self.road_length), self.max_speed))
            cur_section_start += car.Car.each_section_length
            cur_section_end += car.Car.each_section_length

    def update_speeds(self, cars):
        if (self.algorithm == 2):
            for lane in range(1, 3):
                self.updated_speeds_on_sections_many_times_each_lane(cars, lane)
        else:
            if (time.time() - self.last_update_time > 20.0):
                if (self.algorithm == 0):
                    self.updated_speeds_on_sections_many_times(cars)
                elif (self.algorithm == 1):
                    self.update_speeds_on_sections_pairwise(cars)

    def get_avg_speed_on_sections(self, cars):
        avg_speed_on_sections = np.zeros(car.Car.sections_number)
        cars_number_on_each_section = np.zeros(car.Car.sections_number)
        for lane in [1, 2]:
            for carr in cars[lane]:
                if (carr.x_coordinate < self.road_length):
                    section_number = int(carr.x_coordinate / car.Car.each_section_length)
                    avg_speed_on_sections[section_number] += carr.speed
                    cars_number_on_each_section[section_number] += 1

        for i in range(car.Car.sections_number):
            if (cars_number_on_each_section[i] > 0):
                avg_speed_on_sections[i] /= cars_number_on_each_section[i]
        return avg_speed_on_sections, cars_number_on_each_section
    
    def get_avg_speed_on_sections_on_lane(self, cars, lane):
        avg_speed_on_sections = np.zeros(car.Car.sections_number)
        cars_number_on_each_section = np.zeros(car.Car.sections_number)
        for carr in cars[lane]:
            if (carr.x_coordinate < self.road_length):
                section_number = int(carr.x_coordinate / car.Car.each_section_length)
                avg_speed_on_sections[section_number] += carr.speed
                cars_number_on_each_section[section_number] += 1

        for i in range(car.Car.sections_number):
            if (cars_number_on_each_section[i] > 0):
                avg_speed_on_sections[i] /= cars_number_on_each_section[i]
        return avg_speed_on_sections, cars_number_on_each_section                                
    
    def get_safe_speed(self, cur_speed, follow_speed, i):
        if (follow_speed <= cur_speed):
            return self.max_speed
        T = 1.0
        d_i_j = 1.0 * i * self.each_section_length
        tau = d_i_j / (follow_speed - cur_speed)
        rho_i = 1.0 / (follow_speed * T + 15.0)
        rho_j = 1.0 / (cur_speed * T + 15.0)
        c = (cur_speed * rho_j - follow_speed * rho_i) / (rho_j - rho_i)
        safe_speed = cur_speed + (d_i_j + c * tau - cur_speed * T) / tau
        return safe_speed

    def updated_speeds_on_sections_many_times_each_lane(self, cars, lane):
        avg_speeds, cars_number = self.get_avg_speed_on_sections_on_lane(cars, lane)
        
        for i in range(car.Car.sections_number):
            section = car.Car.sections[i]
            if (self.adaptive_top_speed):
                if (cars_number[i] > 4 and avg_speeds[i] < self.slow_cars_coefficient 
                        * car.Car.sections[i].max_speed[lane]):
                    section.max_speed[lane] = self.max_speed * self.reducing_coefficient
                    section.last_update[lane] = time.time()
                else:
                    if (time.time() - section.last_update[lane] > 20.0):
                        section.max_speed[lane] = self.max_speed
                        section.last_update[lane] = time.time()

    def updated_speeds_on_sections_many_times(self, cars):
        avg_speeds, cars_number_on_each_section = self.get_avg_speed_on_sections(cars)

        examined_sections = np.zeros(car.Car.sections_number)
        smth_updated = False
        for i in range(car.Car.sections_number):
            if (i >= 1 and self.adaptive_top_speed):
                if (cars_number_on_each_section[i] > 0):
                    if (avg_speeds[i] < self.slow_cars_coefficient
                            * car.Car.sections[i].max_speed[0]
                            and cars_number_on_each_section[i] > 5):
                        for j in range(self.steps_backword):
                            if (i - j >= 0):
                                examined_sections[i - j] = 1
                                if (car.Car.sections[i - j].max_speed[0] == self.max_speed):
                                    smth_updated = True
                                for lane in range(2):
                                    car.Car.sections[i - j].max_speed[lane] = (self.max_speed
                                        * self.reducing_coefficient)
                    else:
                        for j in range(self.steps_backword):
                            if (i - j >= 0 and examined_sections[i - j] == 0):
                                if (car.Car.sections[i - j].max_speed[0] != self.max_speed):
                                    smth_updated = True
                                for lane in range(2):
                                    car.Car.sections[i - j].max_speed[lane] = self.max_speed
                else:
                    for j in range(self.steps_backword):
                        if (i - j >= 0 and examined_sections[i - j] == 0):
                            if (car.Car.sections[i - j].max_speed[0] != self.max_speed):
                                smth_updated = True
                            for lane in range(2):
                                car.Car.sections[i - j].max_speed[lane] = self.max_speed
        if (smth_updated):
            self.last_update_time = time.time()

    def update_speeds_on_sections_pairwise(self, cars):
        avg_speeds, cars_number_on_each_section = self.get_avg_speed_on_sections(cars)
        smth_updated = False
        for i in range(car.Car.sections_number - 1):
            if (cars_number_on_each_section[i] > 0 and cars_number_on_each_section[i + 1] > 0):
                if (self.adaptive_top_speed):
                    for lane in range(2):
                        car.Car.sections[i].max_speed[lane] = max(self.get_safe_speed(avg_speeds[i + 1],
                            avg_speeds[i], 1), 0.7 * self.max_speed)
                    smth_updated = True
                else:
                    smth_updated = True
        if smth_updated:
            self.last_update_time = time.time()