import os, psycopg
from psycopg.rows import dict_row
from flask import Flask, request, jsonify, escape
from flask_cors import CORS
from dotenv import load_dotenv

app = Flask(__name__)
CORS(app) 
app.config['JSON_AS_ASCII'] = False

load_dotenv()
db_url = os.environ.get("DB_URL")
conn = psycopg.connect(db_url, row_factory=dict_row, autocommit = True)

def check_key(api_key):
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM jonnen WHERE api_key = %s", [api_key])
        return cur.fetchone()['id']


@app.route("/")
def index():
    return { "message": "Use endpoint /todo" }

@app.route("/orders/<int:id>", methods=['PUT', 'DELETE'])
def changeToDo(id):
    try:
        guest_id = check_key(request.args.get('api_key'))
    except:
        return { 'message': 'Error: api_key not set or invalid' }, 401
    try:
        req_body = request.get_json()
        if request.method == 'PUT':
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE orders SET
                        category_id = %s,
                        order_title = %s,
                        due_at = %s
                    WHERE
                        id = %s
                    """, 
                    (
                        req_body['category_id'],
                        escape(req_body['order_title']),
                        req_body['due_at'],
                        req_body['id']
                    ))
            return { "message": "Todo updated successfully" }
    except Exception as e:
        return { "error message": repr(e) }, 400

# Skapa användare samt api_key
@app.route("/person/<int:id>", methods=['GET'])
def user(id):
    try:
        guest_id = check_key(request.args.get('api_key'))
    except Exception as e:
        return {'message': 'Error: api_key not set or invalid'}, 401

    if request.method == 'GET':
        with conn.cursor() as cur:
            cur.execute("SELECT name FROM jonnen WHERE id = %s", (guest_id,))
            result = cur.fetchone()
            if result:
                return {"name": result['name']}
            else:
                return {"message": "No user found with the provided API key."}, 404


#Returnerar todos med rätt category (id) samt checkar rätt api_key (guest_id)
@app.route("/category/<int:id>", methods=['GET', 'POST'])
def bookings(id):
    try:
        guest_id = check_key(request.args.get('api_key'))
    except:
        return {"message": "ERROR: Invalid API-key"}, 401

    if request.method == 'GET':
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    b.id,
                    b.order_title,
                    b.jonne_id,
                    b.category_id,
                    b.due_at::varchar,
                    c.category_name
                FROM 
                    orders b
                INNER JOIN
                    jonnen g
                    ON g.id = b.jonne_id
                INNER JOIN 
                    category as c
                    ON c.id = b.category_id
                WHERE g.id = %s AND c.id = %s
                ORDER BY b.due_at ASC
            """, [guest_id, id])
            result = cur.fetchall()
        return {"orders": result}


#Returnerar alla dina todos på basis av api_key(guest_id)
@app.route("/orders/<int:id>", methods=['GET', 'POST'])
def fis(id):
    try:
        guest_id = check_key(request.args.get('api_key'))
    except:
        return {"message": "ERROR: Invalid API-key"}, 401

    if request.method == 'GET':
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    b.id,
                    b.order_title,
                    b.jonne_id,
                    b.category_id,
                    b.due_at::varchar,
                    c.category_name,
                    b.completed::varchar
                FROM 
                    orders b
                INNER JOIN
                    jonnen g
                    ON g.id = b.jonne_id
                INNER JOIN 
                    category as c
                    ON c.id = b.category_id
                WHERE g.id = %s
                ORDER BY b.due_at ASC
            """, [guest_id])
            result = cur.fetchall()
        return { "orders": result }
    
    #Postar ny todo om man har rätt api_key(guest_id)
    if request.method == 'POST':
        try:
            req_body = request.get_json()
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO orders (
                        order_title,
                        jonne_id,
                        category_id,
                        due_at
                    ) VALUES (
                        %s, %s,%s,%s
                    ) RETURNING id
                """, [
                    escape(req_body['order_title']),
                    guest_id,
                    req_body['category_id'],
                    req_body['due_at']
                ])
                new_id = cur.fetchone()['id']

            return { "new_booking": new_id }
        except Exception as e:
            print("ERROR: " + repr(e))
            return  repr(e), 400
    else:
        return { "Du använde metoden": request.method }

# Ta bårt från databasen
@app.route("/delete/<int:id>", methods=['DELETE'])
def delete(id):
    try:
        guest_id = check_key(request.args.get('api_key'))
    except:
        return { 'message': 'Error: api_key not set or invalid' }, 401               
    
    if request.method == 'DELETE':
        #req_body = request.get_json();
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    DELETE FROM 
                        orders 
                    WHERE
                        id = %s
                    AND
                        jonne_id = %s 
                    """, [ id, guest_id ])
                result = cur.rowcount
            return { 'message': result }
        except Exception as e:
            print("ERROR: " + repr(e))
            return  repr(e), 400

# Uppdatera
@app.route('/edit/<int:id>', methods=['PUT'])
def update(id):
    try:
        guest_id = check_key(request.args.get('api_key'))
    except:
        return { 'message': 'Error: api_key not set or invalid' }, 401
    
    req_body = request.get_json()
    if request.method == 'PUT':
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE orders SET
                    category_id = %s,
                    order_title = %s,
                    due_at = %s
                    WHERE
                    id = %s AND jonne_id = %s
                    """,
                    (
                    req_body['category_id'],
                    escape(req_body['order_title']),
                    req_body['due_at'],
                    id,
                    guest_id
                    ))
            return { "message": "Todo updated successfully" }
        except Exception as e:
            return { "error message": repr(e) }, 400

# Complete endpointen
@app.route('/completed/<int:id>', methods=[ 'PUT' ])
def completeTask(id):
    try:
        guest_id = check_key(request.args.get('api_key'))
    except:
        return { 'message': 'Error: api_key not set or invalid' }, 401
    
    if request.method == 'PUT':
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE orders SET
                    completed = CURRENT_TIMESTAMP
                    WHERE
                    id = %s AND jonne_id = %s
                    """, 
                    [id, guest_id])
                result = cur.rowcount
            return { "rows affected": result}
        except Exception as e:
            return print(e)


## Kom ihåg:
# - pip install -r requirements.txt
# - Kopiera/byt namn på .env-example ==> .env och sätt in en riktig DB_URL
# - Ändra portnummer nedan

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8173, debug=True)