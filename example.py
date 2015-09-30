import sys
import numpy as np
import random
import matplotlib.pyplot as plt
from matplotlib.legend_handler import HandlerLine2D

import road
import car
import speed_manager

"""
Временные интервалы 'time_intervals' задают частоту появления автомобилей на дороге.
"""
time_intervals = [[9.0, 3.6, 3.6],
                [9.0, 2.0, 2.0],
                [9.0, 3.6, 3.6]]

def fill_time_intervals():
    road.Road.time_intervals = [[[], [], []],
                                [[], [], []],
                                [[], [], []]]
    for hour in range(3):
        for lane in range(3):
            for production_times in range(10000):
                time_interval = time_intervals[hour][lane]
                road.Road.time_intervals[hour][lane].append(random.uniform(0.9 * time_interval,
                    1.1 * time_interval))
    road.Road.time_intervals[0][1][0] /= 2.0


def run_road(road_length, adaptive_top_speed, on_ramp_start, on_ramp_end):
    each_section_length = 1000.0
    algorithm = 2
    updater = speed_manager.Updater(road_length, each_section_length, algorithm, adaptive_top_speed)
    updater.fill_sections()

    my_road = road.Road(updater, road_length, 710, adaptive_top_speed, on_ramp_start, on_ramp_end)
    avg_time, sd_time, avg_consumption, sd_consumption, avg_emissions, sd_emissions, cars_number \
        = my_road.run()

def main(road_length, pandus_start, pandus_end):
    car.Car.on_ramp_end = on_ramp_end
    car.Car.on_ramp_start = on_ramp_start
    car.Car.road_length = road_length
    car.Car.height = 710
    fill_time_intervals()

    avg_times = []
    sd_times = []
    avg_consumptions = []
    sd_consumptions = []
    for adaptive_top_speed in [False]:
        road.Road.production_times = [0, 0, 0]
        run_road(road_length, adaptive_top_speed, on_ramp_start, on_ramp_end)

if __name__ == '__main__':
    if (len(sys.argv) < 4):
        print ("Args : road_length, on_ramp_start, on_ramp_end")
        sys.exit(0)
    road_length = int(sys.argv[1])
    on_ramp_start = int(sys.argv[2])
    on_ramp_end = int(sys.argv[3])
    main(road_length, on_ramp_start, on_ramp_end)