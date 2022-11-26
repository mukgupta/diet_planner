#TODO


# Add inventory
# Add support for favourites
import os
import sys

import random
import csv
import calendar
from jinja2 import Environment, FileSystemLoader
import sys
from ortools.sat.python import cp_model
import json
from itertools import groupby
import operator
import datetime
import s3fs
import boto3
from botocore.exceptions import ClientError
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication


calendar.setfirstweekday(calendar.TUESDAY)
S3_BUCKET_NAME = 'diet-planner-s3-bucket'
last_week_file_key = "lastweek.json"
last_week_file_path = "%s/%s" % (S3_BUCKET_NAME,last_week_file_key)
num_days_to_pick_from_last_week = 2
num_days_to_prevent_last_week_dishes = 2


def create_multipart_message(sender, recipients, title, text, html, attachment_data):
    """
    Creates a MIME multipart message object.
    Uses only the Python `email` standard library.
    Emails, both sender and recipients, can be just the email string or have the format 'The Name <the_email@host.com>'.

    :param sender: The sender.
    :param recipients: List of recipients. Needs to be a list, even if only one recipient.
    :param title: The title of the email.
    :param text: The text version of the email body (optional).
    :param html: The html version of the email body (optional).
    :param attachments: List of files to attach in the email.
    :return: A `MIMEMultipart` to be used to send the email.
    """
    multipart_content_subtype = 'alternative' if text and html else 'mixed'
    msg = MIMEMultipart(multipart_content_subtype)
    msg['Subject'] = title
    msg['From'] = sender
    msg['To'] = ', '.join(recipients)

    # Record the MIME types of both parts - text/plain and text/html.
    # According to RFC 2046, the last part of a multipart message, in this case the HTML message, is best and preferred.
    if text:
        part = MIMEText(text, 'plain')
        msg.attach(part)
    if html:
        part = MIMEText(html, 'html')
        msg.attach(part)

    # Add attachments
    part = MIMEApplication(attachment_data.encode('utf-8'))
    part.add_header('Content-Disposition', 'attachment', filename='file.html')
    msg.attach(part)

    return msg


def send_mail(subject, content):
    """
    Send email to recipients. Sends one mail to all recipients.
    The sender needs to be a verified email in SES.
    """
    BODY_TEXT = ("Please find the diet chart attached"
                )

    BODY_HTML = """<html>
    <head></head>
    <body>
      <h1>Diet Chart</h1>
      <p>Please find the diet chart attached</p>
    </body>
    </html>
    """
    msg = create_multipart_message(
        "mukeshgupta.2006@gmail.com",
        ["mukeshgupta.2006@gmail.com"],
        subject, BODY_TEXT, BODY_HTML, content)
    ses_client = boto3.client('ses')  # Use your settings here
    return ses_client.send_raw_email(
        Source="mukeshgupta.2006@gmail.com",
        Destinations=["mukeshgupta.2006@gmail.com"],
        RawMessage={'Data': msg.as_string()}
    )


class DietPartialSolutionPrinter(cp_model.CpSolverSolutionCallback):
    """Print intermediate solutions."""

    def __init__(self, limit):
        cp_model.CpSolverSolutionCallback.__init__(self)
        self._solution_count = 0
        self._limit = limit

    def on_solution_callback(self):
        self._solution_count += 1
        if self._solution_count >= self._limit:
            self.StopSearch()

    def solution_count(self):
        return self._solution_count

def next_weekday(weekday):
    onDay = lambda date, day: date + datetime.timedelta(days=(day-date.weekday()+7)%7)
    now = datetime.datetime.now()
    next_monday = onDay(now, 0)
    return onDay(next_monday, weekday)

def render_template(schedule, inventory, start_date, end_date):
    env = Environment(loader=FileSystemLoader('.'))
    template = env.get_template('week_template.html.tpl')
    output_from_parsed_template = template.render(
        schedule=schedule,
        calendar=calendar,
        inventory=inventory,
        start_date=start_date,
        end_date=end_date)
    return output_from_parsed_template

def load_diet_items():
    diet_items = {}
    with open('data/items.csv') as csvfile:
        diet_reader = csv.DictReader(csvfile, delimiter=',')
        for row in diet_reader:
            if row['enabled'] == 'y':
                diet_item = {
                   "id": int(row['id']),
                   "name": row['name'],
                   "inventory": [],
                   "constraint_ingredients": []
                }
                diet_types = row['type'].split(':')
                if row['constraint_ingredients']:
                    diet_item["constraint_ingredients"] = row['constraint_ingredients'].split(':')

                if row['inventory']:
                    diet_item["inventory"] = row['inventory'].split(':')

                if row['health_ingredients']:
                    diet_item["health_ingredients"] = row["health_ingredients"].split(':')
                for diet_type in diet_types:
                    diet_items.setdefault(diet_type, []).append(diet_item)

    return diet_items


def load_ingredients():
    ingredients = {}
    with open('data/ingredients.csv') as csvfile:
        ingredients_reader = csv.DictReader(csvfile, delimiter=',')
        for row in ingredients_reader:
            ingredients[row['name']] = {
                "id": row['id'],
                "min_distance_between_servings": row['min_distance_between_servings'],
                "max_servings_per_cycle": row['max_servings_per_cycle'],
                "min_servings_per_cycle": row['min_servings_per_cycle']
            }
    return ingredients


def get_constraint_dict(diet_items):
    contraint_dict = {}
    for key, diet_items in diet_items.items():
        for item in diet_items:
            for contraint in item['constraint_ingredients']:
                contraint_dict.setdefault(contraint, set()).add(item['id'])

    return contraint_dict

def get_health_ingredients_dict(diet_items):
    health_ingredients_dict = {}
    for key, diet_items in diet_items.items():
        for item in diet_items:
            for contraint in item.get('health_ingredients',[]):
                health_ingredients_dict.setdefault(contraint, set()).add(item['id'])

    return health_ingredients_dict



def generate_schedule(num_days, num_simulations=1, last_week_schedule=None):
    lunch_plan = {}
    dinner_plan = {}
    breakfast_plan = {}

    add_last_week_constraints = False

    if last_week_schedule:
        add_last_week_constraints = True

    model = cp_model.CpModel()

    diet_items = load_diet_items()
    contraint_dict = get_constraint_dict(diet_items)
    health_ingredients_dict = get_health_ingredients_dict(diet_items)
    breakfast_items = [item for item in diet_items['breakfast']]
    lunch_items = [item for item in diet_items['lunch']]
    dinner_items = [item for item in diet_items['dinner']]

    breakfast_ids = [item['id'] for item in breakfast_items]
    dinner_ids = [item['id'] for item in dinner_items]
    lunch_ids = [item['id'] for item in lunch_items]


    carb_ids = list(health_ingredients_dict['carbs'])
    protein_ids = list(health_ingredients_dict['protein'])

    random.shuffle(breakfast_ids)
    random.shuffle(dinner_ids)
    random.shuffle(lunch_ids)

    common_ids = list(set(lunch_ids).intersection(dinner_ids))

    all_days = range(num_days)

    ingredients_map = load_ingredients()

    def get_dish_contraint_sum(dish_ids, d):
        dish_servings = 0
        for dish in dish_ids:
            if dish in breakfast_ids:
                dish_servings += breakfast_plan[(dish, d)]
            if dish in lunch_ids:
                dish_servings += lunch_plan[(dish, d)]
            if dish in dinner_ids:
                dish_servings += dinner_plan[(dish, d)]
        return dish_servings


    def get_n_days_dishes_of_last_week(n):
        last_week_ids = []
        items = last_week_schedule['schedule_ids']
        for item in items[-n:]:
            last_week_ids.append(item['breakfast'])
            last_week_ids.append(item['lunch'])
            last_week_ids.append(item['dinner'])

        last_week_ids = set(last_week_ids)
        return last_week_ids

    for breakfast_dish in breakfast_ids:
        for d in all_days:
            breakfast_plan[(breakfast_dish, d)] = model.NewBoolVar('breakfast_dish%id%i' % (breakfast_dish, d))

    for lunch_dish in lunch_ids:
        for d in all_days:
            lunch_plan[(lunch_dish, d)] = model.NewBoolVar('lunch_dish%id%i' % (lunch_dish, d))

    for dinner_dish in dinner_ids:
        for d in all_days:
            dinner_plan[(dinner_dish, d)] = model.NewBoolVar('dinner_dish%id%i' % (dinner_dish, d))

    contraint_servings = {}
    contraint_servings_cycle = {}
    protein_servings = {}
    carb_servings = {}
    last_week_avoid_constraints = {}
    for contraint, dishes in contraint_dict.items():
        contraint_servings[contraint] = {}
        contraint_servings_cycle[contraint] = 0

    for d in all_days:
        if add_last_week_constraints:
            n = num_days - (d + 1)
            last_week_n_day_dishes = get_n_days_dishes_of_last_week(n)

            last_week_avoid_constraints[d] = get_dish_contraint_sum(last_week_n_day_dishes, d)
            model.Add(last_week_avoid_constraints[d] == 0)

        # there should be at least one lunch and one dinner everyday
        model.Add(sum(lunch_plan[(lunch_dish, d)] for lunch_dish in lunch_ids) == 1)
        model.Add(sum(dinner_plan[(dinner_dish, d)] for dinner_dish in dinner_ids) == 1)
        model.Add(sum(breakfast_plan[(breakfast_dish, d)] for breakfast_dish in breakfast_ids) == 1)

        protein_servings[d] = get_dish_contraint_sum(protein_ids, d)
        carb_servings[d] = get_dish_contraint_sum(carb_ids, d)

        model.Add(protein_servings[d] >= 1)
        model.Add(carb_servings[d] <= 1)
        
        # For every contraint, there shouldn't be more than one serving per day
        for contraint, dishes in contraint_dict.items():
            contraint_servings[contraint][d] = get_dish_contraint_sum(dishes, d)
            contraint_servings_cycle[contraint] += contraint_servings[contraint][d]

            model.Add(contraint_servings[contraint][d] <= 1)

    for contraint, dishes in contraint_dict.items():
        max_servings_per_cycle = int(ingredients_map.get(contraint, {}).get('max_servings_per_cycle', 100000))
        min_servings_per_cycle = int(ingredients_map.get(contraint, {}).get('min_servings_per_cycle', -1))
        model.Add(min_servings_per_cycle <= contraint_servings_cycle[contraint] )
        model.Add(contraint_servings_cycle[contraint] <= max_servings_per_cycle)

    # Item with similar constraints shouldn't be scheduled for two consecutive days
    for d in all_days:
        contraint_servings_count = {}
        for contraint, dishes in contraint_dict.items():
            min_distance_between_servings = int(ingredients_map.get(contraint, {}).get('min_distance_between_servings', 0))
            contraint_servings_count[contraint] = 0
            range_to_check = min(min_distance_between_servings, num_days - d)
            for i in range(range_to_check):
                contraint_servings_count[contraint] += contraint_servings[contraint][(d + i) % num_days]
            model.Add(contraint_servings_count[contraint] <= 1)

    # same dish not to be repeated on any day in breakfast
    for breakfast_dish in breakfast_ids:
        model.Add(sum(breakfast_plan[(breakfast_dish, d)] for d in all_days) <= 1)

    # same dish not to be repeated on any day in lunch
    for lunch_dish in lunch_ids:
        model.Add(sum(lunch_plan[(lunch_dish, d)] for d in all_days) <= 1)

    # same dish not to be repeated on any day in dinner
    for dinner_dish in dinner_ids:
        model.Add(sum(dinner_plan[(dinner_dish, d)] for d in all_days) <= 1)

    # same dish not to be repeated if it has appeared at least once in either dinner or lunch or breakfast
    for dish in common_ids:
        model.Add(sum(dinner_plan[(dish, d)] for d in all_days) + sum(lunch_plan[(dish, d)] for d in all_days) <= 1)

    solver = cp_model.CpSolver()

    solution_printer = solver.Solve(model)

    limit = random.randint(0, num_simulations)

    solution_printer = DietPartialSolutionPrinter(limit)
    status = solver.SearchForAllSolutions(model, solution_printer)
    # status = solver.Solve(model)
    schedule = []
    for d in range(num_days):
        schedule.append({
            'breakfast': "",
            'lunch': "",
            'dinner': ""
            })
        for breakfast in breakfast_items:
            if solver.Value(breakfast_plan[(breakfast['id'], d)]):
                schedule[d]['breakfast'] = breakfast

        for lunch in lunch_items:
            if solver.Value(lunch_plan[(lunch['id'], d)]):
                schedule[d]['lunch'] = lunch
        for dinner in dinner_items:
            if solver.Value(dinner_plan[(dinner['id'], d)]):
                schedule[d]['dinner'] = dinner

    return schedule

def get_inventory_fron_schedule(schedule):
    inventory = []
    for idx, item in enumerate(schedule):
        inventory.extend(item['breakfast']['inventory'] + item['lunch']['inventory'] + item['dinner']['inventory'])

    return inventory

def print_schedule_cli(schedule):
    for idx, item in enumerate(schedule):
        print("schedule for %s" %  (calendar.day_name[idx]))
        print("breakfast: %s, lunch: %s, dinner: %s\n" % (item['breakfast']['name'], item['lunch']['name'], item['dinner']['name']))

    inventory = get_inventory_fron_schedule(schedule)
    print("Inventory:\n ")
    results = {value: len(list(freq)) for value, freq in groupby(sorted(inventory))}
    sorted_results = sorted(results.items(), key=operator.itemgetter(1), reverse=True)
    for key, val in sorted_results:
        print("%s : %s" % (key, val))


def process(last_week_data=None, mode="1", handle_json=None, handle_html=None):
    num_days = 7

    datetime_format = '%d-%b-%y'

    start_date = next_weekday(0)
    end_date = next_weekday(num_days-1)


    # Discards last week data if older than 2 days
    if last_week_data:
        last_week_data_end_date = datetime.datetime.strptime(last_week_data["end_date"], datetime_format)
        if (last_week_data_end_date < datetime.datetime.now() - datetime.timedelta(days=2)):
            print("Discarding last week data since older than two days")
            last_week_data = None

    schedule = generate_schedule(num_days, last_week_schedule=last_week_data)
    json_data = {}
    json_data['schedule_ids'] = []
    json_data['start_date'] = start_date.strftime(datetime_format)
    json_data['end_date'] = end_date.strftime(datetime_format)

    schedule_name = []
    for s in schedule:
        json_data['schedule_ids'].append({
            "breakfast": s["breakfast"]['id'],
            "lunch": s["lunch"]['id'],
            "dinner": s["dinner"]['id']
            })

    for s in schedule:
        schedule_name.append({
            "breakfast": s["breakfast"]['name'],
            "lunch": s["lunch"]['name'],
            "dinner": s["dinner"]['name']
            })

    if handle_json:
        handle_json(json.dumps(json_data))

    inventory = set(get_inventory_fron_schedule(schedule))
    if mode == "1":
        print_schedule_cli(schedule)
    else:
        html = render_template(schedule_name, inventory, start_date, end_date)
        if handle_html:
            handle_html(html)

def handler(event, context):
    s3 = s3fs.S3FileSystem(default_cache_type=None)
    filename = "%s" % datetime.datetime.now().strftime("%d-%m-%y")


    def get_file_from_s3(key):
        s3 = boto3.client('s3')
        response = s3.get_object(Bucket=S3_BUCKET_NAME, Key=key)
        data = json.load(response['Body'])
        return data

    def put_file_on_s3(path, data):
        outfile = s3.open(path, 'wb')
        outfile.write(data)
        outfile.close()

    def handle_html(html_data):
        html_s3_path = "%s/%s.html" % (S3_BUCKET_NAME, filename)
        print("Uploading hrml")
        put_file_on_s3(html_s3_path, html_data.encode())
        print("Uploaded html")
        title = "Diet Chart: %s" % filename
        send_mail(title, html_data)

    def handle_json(json_data):
        print("Uploading json")
        json_s3_path = "%s/%s.json" % (S3_BUCKET_NAME, filename)
        put_file_on_s3(json_s3_path, json_data.encode())
        put_file_on_s3(last_week_file_path, json_data.encode())
        print("Uploaded json")

    print("Generating Schedule")
    print("Fetching last week schedule")
    last_week_data = get_file_from_s3(last_week_file_key)
    process(last_week_data=last_week_data, mode="0", handle_json=handle_json, handle_html=handle_html)


if __name__== "__main__":
    import sys
    last_week_data = None
    if len(sys.argv) > 2:
        last_week_file = sys.argv[2]
        with open(last_week_file) as f:
            last_week_data = json.load(f)

    mode = "1"
    if len(sys.argv) > 1:
        mode =  sys.argv[1]

    def handle_json(json):
        pass
        # print(json)

    def handle_html(html):
        print(html)

    process(last_week_data, mode, handle_json=handle_json, handle_html=handle_html )