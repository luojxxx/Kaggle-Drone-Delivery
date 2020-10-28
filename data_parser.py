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
            'products': [int(item) for item in products]
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

