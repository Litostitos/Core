from flask import Flask,request
from flask_sqlalchemy import SQLAlchemy
from schemas import ItemSchema, StoreSchema
import os

app=Flask(__name__)

db_path = os.path.join(app.instance_path, "data.db")
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


class Store(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False, unique=True)
    items = db.relationship('Item', backref='store', lazy=True)

class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    ip = db.Column(db.String(40), nullable=False)
    store_id = db.Column(db.Integer, db.ForeignKey('store.id'), nullable=False)

# Initialize schemas
item_schema = ItemSchema()
store_schema = StoreSchema()


@app.get("/store")
def get_stores():
    stores = Store.query.all()
    return {"stores": [
        {"name": store.name, "items": [{"name": item.name, "ip": item.ip} for item in store.items]}
        for store in stores
    ]}



@app.post("/store")
def crate_store():
    request_data = request.get_json()
    #vlidate incoming data
    errors = store_schema.validate(request_data)
    if errors:
        return {"message": "Validation errors", "errors": errors}, 400
    
    new_store = Store(name=request_data['name'])
    db.session.add(new_store)
    db.session.commit()

    return {"name": new_store.name, "items": []}, 201

@app.post("/store/<string:name>/item", methods=["POST"])
def crate_item(name):
    request_data = request.get_json()
    #validate incoming data
    errors = item_schema.validate(request_data)
    if errors:
        return {"message": "Validation errors", "errors": errors}, 400
    store = Store.query.filter_by(name=name).first()
    if not store:
        return {"message": "store not found"}, 404

    new_item = Item(name=request_data['name'], ip=request_data['ip'], store_id=store.id)
    db.session.add(new_item)
    db.session.commit()

    return {"name": new_item.name, "ip": new_item.ip}, 201

with app.app_context():
    db.create_all()

print("Resolved DB path:", os.path.join(app.instance_path, "data.db"))
#Temporary debug
@app.route("/debug/stores")
def debug_stores():
    stores = Store.query.all()
    return {"stores": [store.name for store in stores]}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

