import random
import csv

def load_diet_items():
	diet_items = {}
	with open('data/items.csv') as csvfile:
		diet_reader = csv.DictReader(csvfile, delimiter=',')
		for row in diet_reader:
			diet_item = row['name']
			diet_types = row['type'].split(':')
			for diet_type in diet_types:
				diet_items.setdefault(diet_type, []).append(diet_item)
	return diet_items

def schedule(num_days):
	diet_items = load_diet_items()
	# get random num_days items
	morning_items = random.sample(diet_items['breakfast'], num_days)
	lunch_items = random.sample(diet_items['lunch'], num_days)
	dinner_items = random.sample(diet_items['dinner'], num_days)

	schedule = []
	for i in range(num_days):
		schedule.append({
			'breakfast': morning_items[i],
			'lunch': lunch_items[i],
			'dinner': dinner_items[i]
		})

	return schedule


print schedule(4)