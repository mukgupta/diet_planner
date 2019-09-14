## -*- coding: utf-8 -*-

from main import generate_schedule, load_diet_items
from itertools import groupby
import operator

num_iterations = 30
num_days = 7

def print_frequency(items):

	results = {value: len(list(freq)) for value, freq in groupby(sorted(items))}
	sorted_results = sorted(results.items(), key=operator.itemgetter(1), reverse=True)
	for key, val in sorted_results:
		print("%s : %s" % (key, val))

breafast_ids = []
lunch_ids = []
dinner_ids = []
for i in range(num_iterations):
	schedule = generate_schedule(num_days, 1)

	for idx, item in enumerate(schedule):
		# import ipdb as pdb; pdb.set_trace()
		breafast_ids.append(item['breakfast']['name'])
		lunch_ids.append(item['lunch']['name'])
		dinner_ids.append(item['dinner']['name'])


diet_items = load_diet_items()
breakfast_items = [item['name'] for item in diet_items['breakfast']]
lunch_items = [item['name'] for item in diet_items['lunch']]
dinner_items = [item['name'] for item in diet_items['dinner']]


print("\nResults of %s simulations" % num_iterations)
print("\n----- breakfast ----")
print_frequency(breafast_ids)
print("\n----- lunch ----")
print_frequency(lunch_ids)
print("\n----- dinner ----")
print_frequency(dinner_ids)

print("\n------ Overall ----")
print_frequency(breafast_ids + lunch_ids + dinner_ids)