from flask import Flask, render_template, request, abort
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from flask_socketio import SocketIO, emit
from models import Inventory, Location, Product

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)
engine = create_engine('mysql://admin:admin@localhost:3306/inventory_management', echo=True)
Session = sessionmaker(bind=engine)


@app.route('/')
def home():
    session = Session()
    query_inventory = select(Inventory)
    query_product = select(Product)
    query_location = select(Location)
    inventories = session.scalars(query_inventory)
    option_product = session.scalars(query_product)
    option_location = session.scalars(query_location)
    return render_template('index.html', inventories=inventories, option_product=option_product,
                           option_location=option_location)


@app.route('/products')
def products():
    session = Session()
    query = select(Product)
    sort_by = request.args.get('sort', default='')
    order = request.args.get('order', default='')
    if sort_by == 'name':
        if order == 'asc':
            products = session.query(Product).order_by(Product.name).all()
        elif order == 'desc':
            products = session.query(Product).order_by(Product.name.desc()).all()
        else:
            products = session.scalars(query)

    elif sort_by == 'description':
        if order == 'asc':
            products = session.query(Product).order_by(Product.description).all()
        elif order == 'desc':
            products = session.query(Product).order_by(Product.description.desc()).all()
        else:
            products = session.scalars(query)

    elif sort_by == 'price':
        if order == 'asc':
            products = session.query(Product).order_by(Product.price).all()
        elif order == 'desc':
            products = session.query(Product).order_by(Product.price.desc()).all()
        else:
            products = session.scalars(query)
    else:
        products = session.scalars(query)

    return render_template('products.html', products=products, order=order)


@app.route('/locations')
def locations():
    session = Session()
    query = select(Location)
    order = request.args.get('order', default='')
    if order == 'asc':
        locations = session.query(Location).order_by(Location.name).all()
    elif order == 'desc':
        locations = session.query(Location).order_by(Location.name.desc()).all()
    else:
        locations = session.scalars(query)
    return render_template('locations.html', locations=locations, order=order)


@socketio.on('new_location')
def add_location(data):
    location = data['location']
    session = Session()
    new_location = Location(name=location)
    session.add(new_location)
    session.commit()
    session.close()
    emit('new_location_added', {'location': location}, broadcast=True)
    session.close()


@socketio.on('deleting_location')
def delete_location(data):
    location_id = data['id']
    session = Session()
    location = session.execute(select(Location).filter_by(id=location_id)).scalar_one()
    try:
        session.delete(location)
        session.commit()
        emit('location_deleted', {'location_id': location_id, 'error': False}, broadcast=True)
    except:
        emit('location_deleted', {'location_id': location_id, 'error': True}, broadcast=True)
    session.close()


@socketio.on('edit_location')
def edit_location(data):
    location_id = data['id']
    new_location_name = data['value']
    session = Session()
    location = session.execute(select(Location).filter_by(id=location_id)).scalar_one()
    location.name = new_location_name
    session.commit()
    emit('location_edited', {'id': location_id, 'location_name': new_location_name}, broadcast=True)
    session.close()


@app.route('/search_location', methods=['POST'])
def search_location():
    session = Session()
    keyword = request.form.get('keyword')
    query = select(Location).filter(Location.name.like(f'%{keyword}%'))
    locations = session.scalars(query)
    return render_template('locations.html', locations=locations)


@app.route('/search_product', methods=['POST'])
def search_product():
    session = Session()
    keyword = request.form.get('keyword')
    query = select(Product).filter(Product.name.like(f'%{keyword}%'))
    products = session.scalars(query)
    return render_template('products.html', products=products)


@socketio.on('edit_product')
def edit_product(data):
    session = Session()
    new_product_name = data['productName']
    new_product_description = data['productDescription']
    new_product_price = float(data['productPrice'])
    product_id = data['id']
    product = session.execute(select(Product).filter_by(id=product_id)).scalar_one()
    if product.name != new_product_name:
        product.name = new_product_name
        session.commit()
    if product.description != new_product_description:
        product.description = new_product_description
        session.commit()
    if product.price != new_product_price:
        product.price = new_product_price
        session.commit()
    emit('product_edited', {'id': product_id, 'name': new_product_name, 'description': new_product_description,
                            'price': new_product_price}, broadcast=True)
    session.close()


@socketio.on('deleting_product')
def delete_product(data):
    session = Session()
    product = session.execute(select(Product).filter_by(id=data)).scalar_one()
    try:
        session.delete(product)
        session.commit()
        emit('product_deleted', {'product_id': data, 'error': False}, broadcast=True)
    except:
        emit('product_deleted', {'product_id': data, 'error': True}, broadcast=True)
    session.close()


@socketio.on('new_product')
def add_product(data):
    session = Session()
    product_name = data['productName']
    product_description = data['productDescription']
    product_price = float(data['productPrice'])
    new_record = Product(name=product_name, description=product_description, price=product_price)
    session.add(new_record)
    session.commit()
    emit('product_added', {'product_name': product_name, 'product_description': product_description,
                           'product_price': product_price}, broadcast=True)
    session.close()


@socketio.on('add_to_inventory')
def add_to_inventory(data):
    session = Session()
    product_id = int(data['product_id'])
    location_id = int(data['location_id'])
    quantity = int(data['quantity'])
    product = session.query(Product).filter_by(id=product_id).first()
    location = session.query(Location).filter_by(id=location_id).first()
    new_record = Inventory(product_id=product_id, location_id=location_id, quantity=quantity)
    session.add(new_record)
    session.commit()
    emit('added_to_inventory', {'product_name': product.name, 'product_description': product.description,
                                'product_price': product.price, 'location_name': location.name, 'quantity': quantity}, broadcast=True)
    session.close()


@socketio.on('edit_quantity')
def edit_quantity(data):
    session = Session()
    new_quantity = data['quantity']
    inventory_id = int(data['id'])
    current_quantity = session.query(Inventory).filter_by(id=inventory_id).first()
    if current_quantity.quantity != new_quantity:
        current_quantity.quantity = new_quantity
        session.commit()
    emit('quantity_edited', {'id': inventory_id, 'quantity': new_quantity}, broadcast=True)
    session.close()


@socketio.on('delete_inventory')
def delete_inventory(data):
    session = Session()
    inventory = session.execute(select(Inventory).filter_by(id=data)).scalar_one()
    session.delete(inventory)
    session.commit()
    emit('inventory_deleted', {'id': data}, broadcast=True)
    session.close()


if __name__ == '__main__':
    socketio.run(app, allow_unsafe_werkzeug=True)
