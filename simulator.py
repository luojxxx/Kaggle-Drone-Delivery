import math
import random
from collections import Counter
from itertools import permutations
import copy

random.seed(1)

##### DATA PARSING #####


def get_layout(data):
    line = data[0]
    specifics = line.split(' ')

    return {
        'rows': int(specifics[0]),
        'columns': int(specifics[1]),
        'drones': int(specifics[2]),
        'turns': int(specifics[3]),
        'max_payload': int(specifics[4])
    }


def get_product_weights(data):
    line = data[2]
    product_weights = line.split(' ')

    return {
        'product_weights': tuple([int(weight) for weight in product_weights])
    }


def get_warehouses(data):
    lines = data[4:24]

    warehouses = []
    for i in range(0, len(lines), 2):
        coordinates = lines[i].split(' ')
        inventory = lines[i+1].split(' ')
        warehouses.append({
            'id': int(i/2),
            'coordinates': tuple([int(coor) for coor in coordinates]),
            'inventory': [int(item) for item in inventory]
        })

    return {
        'warehouses': warehouses
    }


def get_orders(data):
    lines = data[25:]

    orders = []
    for i in range(0, len(lines), 3):
        coordinates = lines[i].split(' ')
        products = lines[i+2].split(' ')
        orders.append({
            'id': int(i/3),
            'coordinates': tuple([int(coor) for coor in coordinates]),
            'products': tuple([int(item) for item in products])
        })

    return {
        'orders': orders
    }


def parse_file(filename):
    with open(filename) as f:
        read_data = f.read()
        data = read_data.split('\n')

    return {
        **get_layout(data),
        **get_product_weights(data),
        **get_warehouses(data),
        **get_orders(data)
    }

##### SIMULATOR CLASSES #####


class Drone():
    def __init__(self, id, coordinates):
        self.id = id
        self.coordinates = coordinates
        self.hold = []
        self.available = True
        self.busy_turns = 0

    def set_availability(self, availablity):
        self.available = availablity

    def load_item(self, product_order, quantity):
        for _ in range(quantity):
            self.hold.append(product_order)
        self.busy_turns += 1
        self.set_availability(False)

    def unload_item(self, product_order, quantity):
        for _ in range(quantity):
            matching_idx = 0
            for idx in range(len(self.hold)):
                if product_order['product'] == self.hold[idx]['product']:
                    matching_idx = idx
            self.hold.pop(matching_idx)
        self.busy_turns += 1
        self.set_availability(False)

    def set_coordinates(self, coordinates):
        distance = calculate_distance(self.coordinates, coordinates)
        self.coordinates = coordinates
        self.busy_turns += math.ceil(distance)
        self.set_availability(False)

    def iterate(self):
        if self.busy_turns > 0:
            self.busy_turns -= 1
            if self.busy_turns == 0:
                self.set_availability(True)


class Warehouse():
    def __init__(self, data):
        self.id = data['id']
        self.coordinates = data['coordinates']
        self.inventory = data['inventory']

    def export_item(self, product, quantity):
        self.inventory[product] = self.inventory[product] - quantity

    def import_item(self, product, quantity):
        self.inventory[product] = self.inventory[product] + quantity


class Order():
    def __init__(self, data):
        self.id = data['id']
        self.coordinates = data['coordinates']
        self.products = sorted(data['products'])
        self.processing_products = []
        self.fulfilled_products = []
        self.completed = False

    def process_order(self, product, quantity):
        for _ in range(quantity):
            self.products.remove(product)
            self.processing_products.append(product)

    def fulfill_order(self, product, quantity):
        for _ in range(quantity):
            self.processing_products.remove(product)
            self.fulfilled_products.append(product)
        if len(self.products) == 0 and len(self.processing_products) == 0:
            self.completed = True


class Simulation():
    def __init__(self, filename):
        data = parse_file(filename)
        drone_initial_coordinates = data['warehouses'][0]['coordinates']
        drone_initial_count = data['drones']
        all_warehouse_data = data['warehouses']
        self.xy = (data['rows'], data['columns'])
        self.drones = [Drone(drone_id, drone_initial_coordinates)
                       for drone_id in range(drone_initial_count)]
        self.warehouses = [Warehouse(warehouse_data)
                           for warehouse_data in all_warehouse_data]
        self.turn = 0
        self.max_payload = data['max_payload']
        self.product_weights = data['product_weights']
        self.history = []

    def record(self, line):
        self.history.append(line)

    def next_turn(self):
        [drone.iterate() for drone in self.drones]
        self.turn += 1

    def writeout_history(self):
        with open('submission.csv', 'w') as f:
            f.write(f'{len(self.history)}\n')
            for line in self.history:
                f.write(f'{line}\n')

##### SIMULATOR FUNCTIONS #####


def calculate_distance(coor1, coor2):
    return ((coor1[0] - coor2[0])**2 + (coor1[1] - coor2[1])**2)**0.5


def available_drones(sim):
    return [drone for drone in sim.drones if drone.available == True]


def available_drones_by_distance(sim, coor):
    return sorted(
        available_drones(sim),
        key=lambda drone:
        calculate_distance(drone.coordinates, coor)
    )


def pool_orders(pending_orders, pool_size):
    pool = []
    for order in pending_orders:
        for product in order.products:
            pool.append({
                'order': order,
                'product': product,
            })
        if len(pool) >= pool_size:
            break
    return pool


def find_order_cluster(sim, order_pool, sample_size):
    results = []
    for _ in range(sample_size):
        random_coor = (random.randrange(
            sim.xy[0]), random.randrange(sim.xy[1]))
        order_pool_distances = []
        for product_order in order_pool:
            order_pool_distances.append({
                **product_order,
                'distance': calculate_distance(
                    random_coor,
                    product_order['order'].coordinates
                )
            })
        order_pool_distances.sort(key=lambda item: item['distance'])

        order_pool_selection = []
        weight_capacity = sim.max_payload
        for product_order in order_pool_distances:
            product = product_order['product']
            product_weight = sim.product_weights[product]
            if weight_capacity - product_weight < 0:
                break
            else:
                order_pool_selection.append(product_order)
                weight_capacity = weight_capacity - product_weight

        results.append(order_pool_selection)

    results.sort(
        key=lambda result:
        sum([
            sim.product_weights[product_order['product']]
            for product_order in result
        ]) / (1 + (
            sum([
                product_order['distance']
                for product_order in result
            ]) / len(result)))
    )

    return [
        {
            'order': product_order['order'],
            'product': product_order['product']
        } for product_order in results[-1]
    ]


def find_closest_warehouse_with_product(sim, coordinates, item):
    warehouse_availability = []
    for warehouse in sim.warehouses:
        if warehouse.inventory[item] > 0:
            warehouse_availability.append(warehouse)

    warehouse_availability.sort(
        key=lambda warehouse:
        calculate_distance(coordinates, warehouse.coordinates)
    )

    return warehouse_availability[0]


def find_warehouses_for_product_orders(sim, product_orders):
    warehouse_product_orders = []
    sim_copy = copy.deepcopy(sim)
    for product_order in product_orders:
        order = product_order['order']
        product = product_order['product']
        order.process_order(product, 1)

        warehouse = find_closest_warehouse_with_product(
            sim_copy,
            order.coordinates,
            product
        )

        warehouse_product_orders.append({
            **product_order,
            'warehouse_id': warehouse.id
        })

        warehouse.export_item(product, 1)

    return warehouse_product_orders


def load_drone(sim, drone, warehouse, product_order, quantity):
    drone.set_coordinates(warehouse.coordinates)
    drone.load_item(product_order, quantity)
    product = product_order['product']
    warehouse.export_item(product, quantity)
    sim.record(f'{drone.id} L {warehouse.id} {product} {quantity}')


def optimize_drone_manifest(manifest):
    delivery_routes = list(permutations([i for i in range(len(manifest))]))
    best_delivery_route = []
    best_delivery_route_distance = 9999999999999
    for route in delivery_routes:
        product_orders = [manifest[i] for i in route]
        total_distance = 0
        for idx in range(len(product_orders) - 1):
            first = product_orders[idx]
            second = product_orders[idx + 1]
            total_distance += calculate_distance(
                first['order'].coordinates,
                second['order'].coordinates
            )
        if total_distance < best_delivery_route_distance:
            best_delivery_route = product_orders
    return best_delivery_route


def drone_delivery(sim, drone):
    drone_manifest = optimize_drone_manifest(drone.hold.copy())
    for product_order in drone_manifest:
        order = product_order['order']
        product = product_order['product']
        drone.set_coordinates(order.coordinates)
        quantity = 1
        drone.unload_item(product_order, quantity)
        order.fulfill_order(product, quantity)
        sim.record(f'{drone.id} D {order.id} {product} {quantity}')


def process_orders(sim, pending_orders):
    assigned_drones = available_drones(sim)
    for drone in assigned_drones:
        order_pool = pool_orders(pending_orders, 100)
        if len(order_pool) == 0:
            break
        order_cluster = find_order_cluster(sim, order_pool, 30)
        warehouse_product_orders = find_warehouses_for_product_orders(
            sim, order_cluster)

        for warehouse_product_order in warehouse_product_orders:
            warehouse = sim.warehouses[warehouse_product_order['warehouse_id']]
            product_order = {
                'product': warehouse_product_order['product'],
                'order': warehouse_product_order['order'],
            }
            load_drone(sim, drone, warehouse, product_order, 1)

    for drone in assigned_drones:
        drone_delivery(sim, drone)


##### DATA LOADING #####
data = parse_file('busy_day.in')
sim = Simulation('busy_day.in')

##### EXECUTION CODE #####
orders = [Order(order) for order in data['orders']]
orders = sorted(orders, key=lambda order: len(order.products))

# for order in orders:
#   print(order.coordinates, order.products)

for i in range(data['turns']):
    pending_orders = [
        order for order in orders
        if order.completed == False
    ]
    if len(pending_orders) > 0:
        if len(available_drones(sim)) > 0:
            process_orders(sim, pending_orders)
    sim.next_turn()

print(len(sim.history))
print(sim.history)
sim.writeout_history()

# find closest warehouses to the order products, then bundle, then drones
# do short easy orders first
# packing efficency
# order in which the warehouses are visited per bundle ending towards order's coordinates
# write validator to find optimized parameters or just use total drone commands as proxy

# optimize globally across multiple orders
# group some orders together such as running 20 pending orders (to reduce computational load),
# calculate best single route to maximize score with available drone,
# calculate next best route, etc
# maximum score is moving most product with shortest distances
# need to balance the warehouse spread with delivery spread
# represent items as array of id-item-order
# identify cluster between nodes using stochasitic method, nodes are id-item-orders
# find minimal distance between random point and id-item-orders
# sorting id-item-orders by distance, add items up to weight limit.
# calculate average distance of added items
# pick maximum payload_weight/average_distance among random points
# the selected items around this point is the cluster
# once cluster and items are found, find minimum warehouse visits for drone
# keep track of best route, if current route exceeds it, give up on route
# find centroid between order and first closest warehouse for first item
# then find closest warehouse for next item based on centroid
# iterate through every possible order of warehouses or deliveries
# find route with shortest total distance
# drone delivers items in order in which it's stored in hold
# demand distribution map should match supply distribution map
