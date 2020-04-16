#!/usr/bin/env python3
"""Coronavirus projections"""
import os.path as op
import re
import sys
import datetime
from collections import namedtuple

import numpy as np
import requests


VERBOSE = False
LAST_N = 5
NUMBER_FILE = op.join(op.dirname(op.realpath(__file__)), "corona-numbers")
MAX_POLY = 4
DATED_NUMBER = namedtuple("DatedNumber", "date value")


def get_numbers():
    """Return the latest available number of cases in Scotland

    Read corona-numbers from the same dir as the script (following symlinks),
    and potentially add today's number if a new number has been added to
    gov.scot's coronavirus page (DOESN'T check date, just assumes that the
    number will increase and so compares to the last stored number).
    """
    # Existing numbers
    global NUMBER_FILE
    numbers = []
    for line in open(NUMBER_FILE, "r"):
        date, num = line.split(",")
        numbers.append(DATED_NUMBER(datetime.datetime.strptime(date, "%Y-%m-%d").date(), int(num)))
    if numbers[-1].date == datetime.date.today():
        return numbers, False
    # Check if a new number exists
    if VERBOSE:
        print("Checking for new number...")
    rx_number = re.compile("([0-9,]+).* positive")
    response = requests.get("https://www.gov.scot/coronavirus-covid-19/").text
    covid_number = rx_number.search(response)
    new = False
    if covid_number:
        num = int(covid_number.group(1).replace(",", ""))
        if numbers[-1] != num:
            new = True
            print("Added today:", num)
            numbers.append(DATED_NUMBER(dates.append(datetime.date.today()), num))
    return numbers, new


def predict_average(numbers):
    """Mean of growthrates"""
    delta_days = [
        (n1.date - n0.date).days for n0, n1 in zip(numbers, numbers[1:])
    ]
    ratios = [n1.value / n0.value for n0, n1 in zip(numbers, numbers[1:])]
    rates = [ratio / delta for (delta, ratio) in zip(delta_days, ratios)]
    growthrate = sum(rates) / len(rates)
    if VERBOSE:
        print(rates)
        print("{:.3f}".format(growthrate))
        print()
    return int(numbers[-1].value * growthrate), growthrate


def predict_growthrate_poly(numbers, degrees):
    """Polyfit on growthrates"""
    date_0 = numbers[0].date
    days_since_0 = np.array([(n.date - date_0).days for n in numbers][1:])
    delta_days = [
        (n1.date - n0.date).days for n0, n1 in zip(numbers, numbers[1:])
    ]
    ratios = np.array([n1.value / n0.value  for n0, n1 in zip(numbers, numbers[1:])])
    rates = [ratio / delta for (delta, ratio) in zip(delta_days, ratios)]
    model = np.poly1d(np.polyfit(days_since_0, rates, degrees))
    next_growthrate = model(days_since_0[-1] + 1)
    if VERBOSE:
        print(next_growthrate)
    return int(numbers[-1].value * next_growthrate), next_growthrate


def index_of_nearest(numbers, actual):
    index_min_diff = 0
    min_diff = None
    for i, val in enumerate(numbers):
        diff = np.abs(val - actual)
        if not min_diff:
            min_diff = diff
            index_min_diff = i
        elif diff < min_diff:
            min_diff = diff
            index_min_diff = i
        else:
            pass
    return index_min_diff


def prediction_list(predictions_and_descriptions, actual, with_closest=False):
    index_min_diff = index_of_nearest(
        [n[0] for n in predictions_and_descriptions], actual
    )
    out = ""
    for i, (val, description) in enumerate(predictions_and_descriptions):
        closest = " "
        if with_closest and i == index_min_diff:
            closest = "*"
        out += "  {closest} {val} - {desc}\n".format(
            val=val, desc=description, closest=closest
        )
    return out


def get_predictions(numbers):
    predict_today, rate = predict_average(numbers[-LAST_N:])
    predictions = []
    for degree in range(1, MAX_POLY + 1):
        prediction, rate = predict_growthrate_poly(numbers, degree)
        predictions.append((prediction, "poly" + str(degree), rate))

    mean_rate = np.mean([r for _, _, r in predictions])
    predictions.append((int(mean_rate * numbers[-1][1]), "μ(all poly)", mean_rate))
    return predictions


def nth(n):
    def nth_n(indexable):
        return indexable[n]
    return nth_n


def print_predictions(message, numbers, last, closest_marker):
        outfmt = "{}{} - {:12s} ({:.3f})"
        print("\n" + message)
        predictions = get_predictions(numbers)
        index_closest = index_of_nearest([p for p, _, _ in predictions], last.value)
        for i, (val, description, growth) in enumerate(predictions):
            print(outfmt.format(closest_marker if i == index_closest else "  ", val, description, growth))


def main():
    """Run various coronavirus projections"""
    data, added_today = get_numbers()

    history = ", ".join([str(i[1]) for i in data[-5:]])
    print("LAST UPDATE\t", data[-1].date)
    print("...{}".format(history))
    print_predictions("predicted", data[:-1], data[-1], "* ")
    print_predictions("next?", data, data[-1],"  ")

    if added_today:
        with open(NUMBER_FILE, "w") as f_numbers:
            for entry in data:
                print("{},{}".format(entry.date, entry.value), file=f_numbers)
        print("\nWrote new number to file")


if __name__ == "__main__":
    if "-v" in sys.argv or "--verbose" in sys.argv:
        VERBOSE = True
    main()
