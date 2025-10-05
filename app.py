from flask import Flask

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

