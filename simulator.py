import math
import random
from collections import Counter

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

  def load_item(self, order_product, quantity):
    for _ in range(quantity):
      self.hold.append(order_product)
    self.busy_turns += 1
    self.set_availability(False)

  def unload_item(self, order_product, quantity):
    for _ in range(quantity):
      matching_idx = 0
      for idx in range(len(self.hold)):
        if order_product['product'] == self.hold[idx]['product']:
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
      self.products.pop(self.products.index(product))
      self.processing_products.append(product)

  def fulfill_order(self, product, quantity):
    for _ in range(quantity):
      self.processing_products.pop(self.processing_products.index(product))
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

def load_drone(sim, drone, warehouse, order_product, quantity):
  product = order_product['product']
  drone.set_coordinates(warehouse.coordinates)
  drone.load_item(order_product, quantity)
  warehouse.export_item(product, quantity)
  sim.record(f'{drone.id} L {warehouse.id} {product} {quantity}')

def drone_delivery(sim, drone):
  for order_product in drone.hold[:]:
    order = order_product['order']
    product = order_product['product']
    drone.set_coordinates(order.coordinates)
    quantity = 1
    drone.unload_item(order_product, quantity)
    order.fulfill_order(product, quantity)
    sim.record(f'{drone.id} D {order.id} {product} {quantity}')

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

def pool_orders(pending_orders, quantity):
  pool = []
  for order in pending_orders:
    for product in order.products:
      pool.append({
        'order': order,
        'product': product,
      })
    if len(pool) >= quantity:
      break
  return pool

def find_order_cluster(sim, order_pool, sample_size):
  results = []
  for _ in range(sample_size):
    random_coor = (random.randrange(sim.xy[0]), random.randrange(sim.xy[1]))
    order_pool_distances = []
    for order_product in order_pool:
      order_pool_distances.append({
        **order_product,
        'distance': calculate_distance(
          random_coor, 
          order_product['order'].coordinates
        )
      })
    order_pool_distances.sort(key=lambda item:item['distance'])
    
    order_pool_selection = []
    weight_capacity = sim.max_payload
    for order_product in order_pool_distances:
      # print('order pool selection', order_pool_selection)
      product = order_product['product']
      product_weight = sim.product_weights[product]
      if weight_capacity - product_weight < 0:
        break
      else:
        order_pool_selection.append(order_product)
        weight_capacity = weight_capacity - product_weight
      
    results.append(order_pool_selection)

  results.sort(
    key=lambda result:
    sum([
      sim.product_weights[order_product['product']] 
      for order_product in result
    ]) /
    ((sum([
      order_product['distance'] 
      for order_product in result
    ]) / len(result)) + 1)
  )

  return [
    {
      'order': order_product['order'], 
      'product': order_product['product']
    } for order_product in results[-1]
  ]


def process_orders(sim, pending_orders):
  assigned_drones = available_drones(sim)
  for drone in assigned_drones:
    order_pool = pool_orders(pending_orders, 100)
    # print('orderpool', [order['product'] for order in order_pool])
    if len(order_pool) == 0:
      break
    order_cluster = find_order_cluster(sim, order_pool, 30)
    # print('ordercluster', order_cluster)
    for order_product in order_cluster:
      order = order_product['order']
      product = order_product['product']
      order.process_order(product, 1)
      
      warehouse = find_closest_warehouse_with_product(
        sim, 
        order.coordinates, 
        product
      )
      
      load_drone(sim, drone, warehouse, order_product, 1)
  
  for drone in assigned_drones:
    drone_delivery(sim, drone)


################ Data loading
data = parse_file('busy_day.in')
sim = Simulation('busy_day.in')

################ Execution code
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
## calculate best single route to maximize score with available drone, 
## calculate next best route, etc
## maximum score is moving most product with shortest distances
## need to balance the warehouse spread with delivery spread
## represent items as array of id-item-order
## identify cluster between nodes using stochasitic method, nodes are id-item-orders
### find minimal distance between random point and id-item-orders
### sorting id-item-orders by distance, add items up to weight limit. 
### calculate average distance of added items
### pick maximum payload_weight/average_distance among random points
### the selected items around this point is the cluster
## once cluster and items are found, find minimum warehouse visits for drone
### warehouses should be sorted by distance to order
### 
## drone delivers items in order in which it's stored in hold
# demand distribution map should match supply distribution map
