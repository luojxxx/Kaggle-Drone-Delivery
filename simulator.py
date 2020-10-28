import math
from collections import Counter

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

  def load_item(self, product, quantity):
    for _ in range(quantity):
      self.hold.append(product)
    self.busy_turns += 1
    self.set_availability(False)

  def unload_item(self, product, quantity):
    for _ in range(quantity):
      self.hold.pop(self.hold.index(product))
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
    self.fulfilled_products = []
    self.completed = False

  def fulfill_order(self, product, quantity):
    for _ in range(quantity):
      self.products.pop(self.products.index(product))
      self.fulfilled_products.append(product)
    if len(self.products) == 0:
      self.completed = True

class Simulation():
  def __init__(self, filename):
    data = parse_file(filename)
    drone_initial_coordinates = data['warehouses'][0]['coordinates']
    drone_initial_count = data['drones']
    all_warehouse_data = data['warehouses']
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

def load_drone(sim, drone, warehouse, product, quantity):
  drone.set_coordinates(warehouse.coordinates)
  drone.load_item(product, quantity)
  warehouse.export_item(product, quantity)
  sim.record(f'{drone.id} L {warehouse.id} {product} {quantity}')

def drone_delivery(sim, drone, order):
  drone.set_coordinates(order.coordinates)
  for item, quantity in Counter(drone.hold).items():
    drone.unload_item(item, quantity)
    order.fulfill_order(item, quantity)
    sim.record(f'{drone.id} D {order.id} {item} {quantity}')

def package_order(sim, order):
  packages = []
  bundle = []
  weight_capacity = sim.max_payload
  products = order.products[:]
  while len(products) > 0:
    if all([
      weight_capacity - sim.product_weights[item] < 0 
      for item in products
    ]):
      packages.append(bundle)
      bundle = []
      weight_capacity = sim.max_payload
    for item in products:
      product_weight = sim.product_weights[item]
      if weight_capacity - product_weight >= 0:
        bundle.append(item)
        weight_capacity = weight_capacity - product_weight
        products.pop(products.index(item))
  if len(bundle) > 0:
    packages.append(bundle)
  
  return packages

def find_closest_warehouse_with_product(sim, order, item):
  warehouse_availability = []
  for warehouse in sim.warehouses:
    if warehouse.inventory[item] > 0:
      warehouse_availability.append(warehouse)

  warehouse_availability.sort(
    key=lambda warehouse: 
    calculate_distance(order.coordinates, warehouse.coordinates)
  )

  return warehouse_availability[0]

def process_order(sim, order):
  packages = package_order(sim, order)
  # print(packages)
  assigned_drones = []
  for bundle in packages:
    drones = available_drones_by_distance(sim, order.coordinates)
    if len(drones) == 0:
      break
    else:
      drone = drones[0]
      assigned_drones.append(drone)
    
    for product in bundle:
      warehouse = find_closest_warehouse_with_product(sim, order, product)
      load_drone(sim, drone, warehouse, product, 1)

  for drone in assigned_drones:
    drone_delivery(sim, drone, order)

################ Data loading
data = parse_file('busy_day.in')
sim = Simulation('busy_day.in')

################ Execution code
orders = [Order(order) for order in data['orders']]
orders = sorted(orders, key=lambda order: len(order.products))

for i in range(data['turns']):
  pending_orders = [
    order for order in orders
    if order.completed == False
  ]
  if len(pending_orders) > 0:
      if len(available_drones(sim)) > 0:
        process_order(sim, pending_orders[0])
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
# group some orders together (to reduce computational load), 
## calculate best single route to maximize score with available drone, 
## calculate next best route, etc
# demand distribution map should match supply distribution map
