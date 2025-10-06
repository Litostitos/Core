from flask import Flask,request

app=Flask(__name__)

stores = [
    {
        'name': 'Switches',
        'items': [
            {'name': 'Switch ESTAR', 'ip ': "192.168.10.1"} 
        ]
    },

        {
        'name': 'Firewalls',
        'items': [
            {'name': 'Firewall ESTAR', 'ip ': "192.168.100.1"} 
        ]
    },
]


@app.get("/store") #http://127.0.0.1:5000/store
def get_stores():
    return {"stores": stores}

@app.get("/store/<string:name>") #http://127.0.0.1:5000/store/
def get_store(name):
    for store in stores:
        if store['name'] == name:
            return store
    return {"message": "store not found"}, 404

@app.get("/store/<string:name>/item") #http://127.0.0.1:5000/store/
def get_item_in_store(name):
    for store in stores:
        if store['name'] == name:
            return {"items": store['items']}
    return {"message": "store not found"}, 404


@app.post("/store")
def crate_store():
    request_data = request.get_json()
    new_store = {
        'name': request_data['name'],
        'items': request_data['items']
    }
    stores.append(new_store)
    return new_store, 201

@app.post("/store/<string:name>/item")
def crate_item(name):
    request_data = request.get_json()
    for store in stores:
        if store['name'] == name:
            new_item = {
                'name': request_data['name'],
                'ip': request_data['ip']
            }
            store['items'].append(new_item)
            return new_item, 201
    return {"message": "store not found"}, 404