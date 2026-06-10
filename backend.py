import sqlite3
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import requests

app = FastAPI()

DATABASE_NAME = "complaints.db"

INITIAL_ORDERS = [
    {
        "order_id": "12345",
        "status": "out for delivery",
        "expected_delivery": "today by 8 PM"
    },
    {
        "order_id": "98765",
        "status": "packed and ready to ship",
        "expected_delivery": "tomorrow"
    },
    {
        "order_id": "ORD789",
        "status": "delivered",
        "expected_delivery": "already delivered"
    },
    {
        "order_id": "ORD555",
        "status": "cancelled",
        "expected_delivery": "not applicable"
    }
]


INITIAL_PRODUCTS = [
    {
        "product_id": "P1001",
        "name": "wireless mouse",
        "price": 799,
        "stock": 18,
        "category": "computer accessories"
    },
    {
        "product_id": "P1002",
        "name": "mechanical keyboard",
        "price": 2499,
        "stock": 7,
        "category": "computer accessories"
    },
    {
        "product_id": "P1003",
        "name": "usb c cable",
        "price": 299,
        "stock": 35,
        "category": "mobile accessories"
    },
    {
        "product_id": "P1004",
        "name": "laptop stand",
        "price": 999,
        "stock": 0,
        "category": "office accessories"
    }
]





class ComplaintRequest(BaseModel):
    order_id: str
    issue_description: str
    
class ComplaintStatusUpdate(BaseModel):
    status: str
    
class ReturnRequestCreate(BaseModel):
    order_id: str
    reason: str
    
class ReturnStatusUpdate(BaseModel):
    status: str
    
class ChatMessage(BaseModel):
    message: str
    sender: str = "web_user"
    
class OrderStatusUpdate(BaseModel):
    status: str
    expected_delivery: str


class ProductUpdate(BaseModel):
    name: str
    price: int
    stock: int
    category: str


def get_db_connection():
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def create_complaints_table():
    conn = get_db_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS complaints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_id TEXT NOT NULL,
            order_id TEXT NOT NULL,
            issue_description TEXT NOT NULL,
            status TEXT NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()

def create_returns_table():
    conn = get_db_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS return_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            return_id TEXT NOT NULL,
            order_id TEXT NOT NULL,
            reason TEXT NOT NULL,
            status TEXT NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()

def create_orders_table():
    conn = get_db_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id TEXT NOT NULL UNIQUE,
            status TEXT NOT NULL,
            expected_delivery TEXT NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()
    
def create_products_table():
    conn = get_db_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            price INTEGER NOT NULL,
            stock INTEGER NOT NULL,
            category TEXT NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()
    
def seed_initial_data():
    conn = get_db_connection()

    for order in INITIAL_ORDERS:
        conn.execute(
            """
            INSERT OR IGNORE INTO orders
            (order_id, status, expected_delivery)
            VALUES (?, ?, ?)
            """,
            (
                order["order_id"],
                order["status"],
                order["expected_delivery"]
            )
        )

    for product in INITIAL_PRODUCTS:
        conn.execute(
            """
            INSERT OR IGNORE INTO products
            (product_id, name, price, stock, category)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                product["product_id"],
                product["name"],
                product["price"],
                product["stock"],
                product["category"]
            )
        )

    conn.commit()
    conn.close()

create_complaints_table()
create_returns_table()
create_orders_table()
create_products_table()
seed_initial_data()



@app.get("/")
def home():
    return {"message": "E-commerce backend API is running"}


@app.get("/orders/{order_id}")
def get_order_status(order_id: str):
    conn = get_db_connection()

    order = conn.execute(
        """
        SELECT order_id, status, expected_delivery
        FROM orders
        WHERE order_id = ?
        """,
        (order_id,)
    ).fetchone()

    conn.close()

    if not order:
        return {
            "found": False,
            "message": "Order not found"
        }

    return {
        "found": True,
        "order_id": order["order_id"],
        "status": order["status"],
        "expected_delivery": order["expected_delivery"]
    }


@app.post("/complaints")
def create_complaint(complaint: ComplaintRequest):
    conn = get_db_connection()

    cursor = conn.execute("SELECT COUNT(*) FROM complaints")
    complaint_count = cursor.fetchone()[0]

    ticket_id = f"TICKET-{1000 + complaint_count + 1}"

    conn.execute(
        """
        INSERT INTO complaints 
        (ticket_id, order_id, issue_description, status)
        VALUES (?, ?, ?, ?)
        """,
        (
            ticket_id,
            complaint.order_id,
            complaint.issue_description,
            "open"
        )
    )

    conn.commit()
    conn.close()

    return {
        "created": True,
        "ticket_id": ticket_id,
        "message": "Complaint registered successfully"
    }


@app.get("/complaints")
def get_all_complaints():
    conn = get_db_connection()

    complaints = conn.execute(
        """
        SELECT id, ticket_id, order_id, issue_description, status
        FROM complaints
        ORDER BY id DESC
        """
    ).fetchall()

    conn.close()

    return [dict(complaint) for complaint in complaints]


@app.get("/complaints/{ticket_id}")
def get_complaint_by_ticket_id(ticket_id: str):
    conn = get_db_connection()

    complaint = conn.execute(
        """
        SELECT id, ticket_id, order_id, issue_description, status
        FROM complaints
        WHERE ticket_id = ?
        """,
        (ticket_id,)
    ).fetchone()

    conn.close()

    if not complaint:
        return {
            "found": False,
            "message": "Complaint not found"
        }

    return {
        "found": True,
        "complaint": dict(complaint)
    }
    
@app.patch("/complaints/{ticket_id}/status")
def update_complaint_status(ticket_id: str, update: ComplaintStatusUpdate):
    allowed_statuses = ["open", "in_progress", "resolved", "closed"]

    if update.status not in allowed_statuses:
        return {
            "updated": False,
            "message": f"Invalid status. Allowed statuses are: {allowed_statuses}"
        }

    conn = get_db_connection()

    complaint = conn.execute(
        """
        SELECT id, ticket_id, order_id, issue_description, status
        FROM complaints
        WHERE ticket_id = ?
        """,
        (ticket_id,)
    ).fetchone()

    if not complaint:
        conn.close()
        return {
            "updated": False,
            "message": "Complaint not found"
        }

    conn.execute(
        """
        UPDATE complaints
        SET status = ?
        WHERE ticket_id = ?
        """,
        (update.status, ticket_id)
    )

    conn.commit()
    conn.close()

    return {
        "updated": True,
        "ticket_id": ticket_id,
        "new_status": update.status,
        "message": "Complaint status updated successfully"
    }
    
@app.get("/products/search")
def search_product(q: str):
    search_query = f"%{q.lower().strip()}%"

    conn = get_db_connection()

    product = conn.execute(
        """
        SELECT product_id, name, price, stock, category
        FROM products
        WHERE LOWER(name) LIKE ?
        LIMIT 1
        """,
        (search_query,)
    ).fetchone()

    conn.close()

    if not product:
        return {
            "found": False,
            "message": "Product not found"
        }

    return {
        "found": True,
        "product": dict(product)
    }
    
@app.post("/returns")
def create_return_request(return_request: ReturnRequestCreate):
    conn = get_db_connection()

    cursor = conn.execute("SELECT COUNT(*) FROM return_requests")
    return_count = cursor.fetchone()[0]

    return_id = f"RETURN-{1000 + return_count + 1}"

    conn.execute(
        """
        INSERT INTO return_requests
        (return_id, order_id, reason, status)
        VALUES (?, ?, ?, ?)
        """,
        (
            return_id,
            return_request.order_id,
            return_request.reason,
            "requested"
        )
    )

    conn.commit()
    conn.close()

    return {
        "created": True,
        "return_id": return_id,
        "message": "Return request created successfully"
    }


@app.get("/returns")
def get_all_return_requests():
    conn = get_db_connection()

    returns = conn.execute(
        """
        SELECT id, return_id, order_id, reason, status
        FROM return_requests
        ORDER BY id DESC
        """
    ).fetchall()

    conn.close()

    return [dict(return_request) for return_request in returns]


@app.get("/returns/{return_id}")
def get_return_request(return_id: str):
    conn = get_db_connection()

    return_request = conn.execute(
        """
        SELECT id, return_id, order_id, reason, status
        FROM return_requests
        WHERE return_id = ?
        """,
        (return_id,)
    ).fetchone()

    conn.close()

    if not return_request:
        return {
            "found": False,
            "message": "Return request not found"
        }

    return {
        "found": True,
        "return_request": dict(return_request)
    }
    
@app.patch("/returns/{return_id}/status")
def update_return_status(return_id: str, update: ReturnStatusUpdate):
    allowed_statuses = ["requested", "approved", "picked_up", "refunded", "rejected"]

    if update.status not in allowed_statuses:
        return {
            "updated": False,
            "message": f"Invalid status. Allowed statuses are: {allowed_statuses}"
        }

    conn = get_db_connection()

    return_request = conn.execute(
        """
        SELECT id, return_id, order_id, reason, status
        FROM return_requests
        WHERE return_id = ?
        """,
        (return_id,)
    ).fetchone()

    if not return_request:
        conn.close()
        return {
            "updated": False,
            "message": "Return request not found"
        }

    conn.execute(
        """
        UPDATE return_requests
        SET status = ?
        WHERE return_id = ?
        """,
        (update.status, return_id)
    )

    conn.commit()
    conn.close()

    return {
        "updated": True,
        "return_id": return_id,
        "new_status": update.status,
        "message": "Return/refund status updated successfully"
    }
    
@app.post("/chat/message")
def send_message_to_rasa(chat_message: ChatMessage):
    try:
        response = requests.post(
            "http://127.0.0.1:5005/webhooks/rest/webhook",
            json={
                "sender": chat_message.sender,
                "message": chat_message.message
            },
            timeout=10
        )

        return {
            "success": True,
            "responses": response.json()
        }

    except requests.exceptions.RequestException:
        return {
            "success": False,
            "message": "Unable to connect to Rasa bot server"
        }
        
@app.get("/orders")
def get_all_orders():
    conn = get_db_connection()

    orders = conn.execute(
        """
        SELECT id, order_id, status, expected_delivery
        FROM orders
        ORDER BY id ASC
        """
    ).fetchall()

    conn.close()

    return [dict(order) for order in orders]


@app.get("/products")
def get_all_products():
    conn = get_db_connection()

    products = conn.execute(
        """
        SELECT id, product_id, name, price, stock, category
        FROM products
        ORDER BY id ASC
        """
    ).fetchall()

    conn.close()

    return [dict(product) for product in products]

@app.patch("/orders/{order_id}")
def update_order(order_id: str, update: OrderStatusUpdate):
    conn = get_db_connection()

    order = conn.execute(
        """
        SELECT id, order_id, status, expected_delivery
        FROM orders
        WHERE order_id = ?
        """,
        (order_id,)
    ).fetchone()

    if not order:
        conn.close()
        return {
            "updated": False,
            "message": "Order not found"
        }

    conn.execute(
        """
        UPDATE orders
        SET status = ?, expected_delivery = ?
        WHERE order_id = ?
        """,
        (update.status, update.expected_delivery, order_id)
    )

    conn.commit()
    conn.close()

    return {
        "updated": True,
        "order_id": order_id,
        "new_status": update.status,
        "expected_delivery": update.expected_delivery,
        "message": "Order updated successfully"
    }
    
@app.patch("/products/{product_id}")
def update_product(product_id: str, update: ProductUpdate):
    conn = get_db_connection()

    product = conn.execute(
        """
        SELECT id, product_id, name, price, stock, category
        FROM products
        WHERE product_id = ?
        """,
        (product_id,)
    ).fetchone()

    if not product:
        conn.close()
        return {
            "updated": False,
            "message": "Product not found"
        }

    conn.execute(
        """
        UPDATE products
        SET name = ?, price = ?, stock = ?, category = ?
        WHERE product_id = ?
        """,
        (
            update.name,
            update.price,
            update.stock,
            update.category,
            product_id
        )
    )

    conn.commit()
    conn.close()

    return {
        "updated": True,
        "product_id": product_id,
        "message": "Product updated successfully"
    }

@app.get("/admin/returns", response_class=HTMLResponse)
def returns_admin_dashboard():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Return/Refund Admin Dashboard</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                background: #f4f6f8;
                padding: 30px;
            }

            h1 {
                color: #222;
            }

            a {
                display: inline-block;
                margin-bottom: 20px;
                color: #222;
                font-weight: bold;
            }

            table {
                width: 100%;
                border-collapse: collapse;
                background: white;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            }

            th, td {
                padding: 12px;
                border-bottom: 1px solid #ddd;
                text-align: left;
            }

            th {
                background: #222;
                color: white;
            }

            select, button {
                padding: 6px 10px;
                margin: 2px;
            }

            button {
                cursor: pointer;
                background: #222;
                color: white;
                border: none;
                border-radius: 4px;
            }

            .status {
                font-weight: bold;
            }
        </style>
    </head>
    <body>
        <h1>Return/Refund Admin Dashboard</h1>
        <a href="/admin">Go to Complaint Dashboard</a>

        <table>
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Return ID</th>
                    <th>Order ID</th>
                    <th>Reason</th>
                    <th>Status</th>
                    <th>Update Status</th>
                </tr>
            </thead>
            <tbody id="returnsTable">
            </tbody>
        </table>

        <script>
            async function loadReturns() {
                const response = await fetch('/returns');
                const returns = await response.json();

                const table = document.getElementById('returnsTable');
                table.innerHTML = '';

                returns.forEach(returnRequest => {
                    const row = document.createElement('tr');

                    row.innerHTML = `
                        <td>${returnRequest.id}</td>
                        <td>${returnRequest.return_id}</td>
                        <td>${returnRequest.order_id}</td>
                        <td>${returnRequest.reason}</td>
                        <td class="status">${returnRequest.status}</td>
                        <td>
                            <select id="status-${returnRequest.return_id}">
                                <option value="requested">requested</option>
                                <option value="approved">approved</option>
                                <option value="picked_up">picked_up</option>
                                <option value="refunded">refunded</option>
                                <option value="rejected">rejected</option>
                            </select>
                            <button onclick="updateReturnStatus('${returnRequest.return_id}')">Update</button>
                        </td>
                    `;

                    table.appendChild(row);
                });
            }

            async function updateReturnStatus(returnId) {
                const selectedStatus = document.getElementById(`status-${returnId}`).value;

                const response = await fetch(`/returns/${returnId}/status`, {
                    method: 'PATCH',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        status: selectedStatus
                    })
                });

                const result = await response.json();

                if (result.updated) {
                    alert(`Return/refund status updated to ${selectedStatus}`);
                    loadReturns();
                } else {
                    alert(result.message);
                }
            }

            loadReturns();
        </script>
    </body>
    </html>
    """
    
@app.get("/admin", response_class=HTMLResponse)
def admin_dashboard():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Complaint Admin Dashboard</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                background: #f4f6f8;
                padding: 30px;
            }

            h1 {
                color: #222;
            }

            table {
                width: 100%;
                border-collapse: collapse;
                background: white;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            }

            th, td {
                padding: 12px;
                border-bottom: 1px solid #ddd;
                text-align: left;
            }

            th {
                background: #222;
                color: white;
            }

            select, button {
                padding: 6px 10px;
                margin: 2px;
            }

            button {
                cursor: pointer;
                background: #222;
                color: white;
                border: none;
                border-radius: 4px;
            }

            .status {
                font-weight: bold;
            }
        </style>
    </head>
    <body>
        <h1>Complaint Admin Dashboard</h1>

        <table>
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Ticket ID</th>
                    <th>Order ID</th>
                    <th>Issue</th>
                    <th>Status</th>
                    <th>Update Status</th>
                </tr>
            </thead>
            <tbody id="complaintsTable">
            </tbody>
        </table>

        <script>
            async function loadComplaints() {
                const response = await fetch('/complaints');
                const complaints = await response.json();

                const table = document.getElementById('complaintsTable');
                table.innerHTML = '';

                complaints.forEach(complaint => {
                    const row = document.createElement('tr');

                    row.innerHTML = `
                        <td>${complaint.id}</td>
                        <td>${complaint.ticket_id}</td>
                        <td>${complaint.order_id}</td>
                        <td>${complaint.issue_description}</td>
                        <td class="status">${complaint.status}</td>
                        <td>
                            <select id="status-${complaint.ticket_id}">
                                <option value="open">open</option>
                                <option value="in_progress">in_progress</option>
                                <option value="resolved">resolved</option>
                                <option value="closed">closed</option>
                            </select>
                            <button onclick="updateStatus('${complaint.ticket_id}')">Update</button>
                        </td>
                    `;

                    table.appendChild(row);
                });
            }

            async function updateStatus(ticketId) {
                const selectedStatus = document.getElementById(`status-${ticketId}`).value;

                const response = await fetch(`/complaints/${ticketId}/status`, {
                    method: 'PATCH',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        status: selectedStatus
                    })
                });

                const result = await response.json();

                if (result.updated) {
                    alert(`Status updated to ${selectedStatus}`);
                    loadComplaints();
                } else {
                    alert(result.message);
                }
            }

            loadComplaints();
        </script>
    </body>
    </html>
    """
    
@app.get("/chat", response_class=HTMLResponse)
def chat_page():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>E-commerce Support Chatbot</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                background: #f4f6f8;
                margin: 0;
                padding: 0;
            }

            .chat-container {
                width: 420px;
                margin: 40px auto;
                background: white;
                border-radius: 12px;
                box-shadow: 0 4px 14px rgba(0,0,0,0.15);
                overflow: hidden;
            }

            .chat-header {
                background: #222;
                color: white;
                padding: 18px;
                font-size: 20px;
                font-weight: bold;
            }

            .chat-box {
                height: 480px;
                padding: 16px;
                overflow-y: auto;
                background: #fafafa;
            }

            .message {
                margin: 10px 0;
                padding: 10px 12px;
                border-radius: 10px;
                max-width: 80%;
                line-height: 1.4;
            }

            .user {
                background: #dbeafe;
                margin-left: auto;
                text-align: right;
            }

            .bot {
                background: #e5e7eb;
                margin-right: auto;
            }

            .input-area {
                display: flex;
                border-top: 1px solid #ddd;
            }

            input {
                flex: 1;
                padding: 14px;
                border: none;
                outline: none;
                font-size: 15px;
            }

            button {
                padding: 14px 18px;
                border: none;
                background: #222;
                color: white;
                cursor: pointer;
                font-weight: bold;
            }

            button:hover {
                background: #444;
            }
        </style>
    </head>
    <body>
        <div class="chat-container">
            <div class="chat-header">E-commerce Support Assistant</div>

            <div class="chat-box" id="chatBox">
                <div class="message bot">Hi! I am your support assistant. How can I help you?</div>
            </div>

            <div class="input-area">
                <input id="userInput" type="text" placeholder="Type your message..." onkeydown="handleKey(event)">
                <button onclick="sendMessage()">Send</button>
            </div>
        </div>

        <script>
            const senderId = "user_" + Math.floor(Math.random() * 100000);

            function addMessage(text, className) {
                const chatBox = document.getElementById("chatBox");
                const messageDiv = document.createElement("div");
                messageDiv.className = "message " + className;
                messageDiv.innerText = text;
                chatBox.appendChild(messageDiv);
                chatBox.scrollTop = chatBox.scrollHeight;
            }

            async function sendMessage() {
                const input = document.getElementById("userInput");
                const message = input.value.trim();

                if (!message) {
                    return;
                }

                addMessage(message, "user");
                input.value = "";

                const response = await fetch("/chat/message", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        sender: senderId,
                        message: message
                    })
                });

                const data = await response.json();

                if (!data.success) {
                    addMessage("Sorry, bot server is not connected.", "bot");
                    return;
                }

                if (data.responses.length === 0) {
                    addMessage("Sorry, I did not understand that.", "bot");
                    return;
                }

                data.responses.forEach(botResponse => {
                    if (botResponse.text) {
                        addMessage(botResponse.text, "bot");
                    }
                });
            }

            function handleKey(event) {
                if (event.key === "Enter") {
                    sendMessage();
                }
            }
        </script>
    </body>
    </html>
    """
    
@app.get("/admin/orders", response_class=HTMLResponse)
def orders_admin_dashboard():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Order Admin Dashboard</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                background: #f4f6f8;
                padding: 30px;
            }

            h1 {
                color: #222;
            }

            a {
                display: inline-block;
                margin-right: 15px;
                margin-bottom: 20px;
                color: #222;
                font-weight: bold;
            }

            table {
                width: 100%;
                border-collapse: collapse;
                background: white;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            }

            th, td {
                padding: 12px;
                border-bottom: 1px solid #ddd;
                text-align: left;
            }

            th {
                background: #222;
                color: white;
            }

            input, select, button {
                padding: 6px 10px;
                margin: 2px;
            }

            button {
                cursor: pointer;
                background: #222;
                color: white;
                border: none;
                border-radius: 4px;
            }
        </style>
    </head>
    <body>
        <h1>Order Admin Dashboard</h1>

        <a href="/admin">Complaint Dashboard</a>
        <a href="/admin/returns">Return Dashboard</a>
        <a href="/admin/products">Product Dashboard</a>
        <a href="/chat">Web Chat</a>

        <table>
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Order ID</th>
                    <th>Status</th>
                    <th>Expected Delivery</th>
                    <th>Update</th>
                </tr>
            </thead>
            <tbody id="ordersTable">
            </tbody>
        </table>

        <script>
            async function loadOrders() {
                const response = await fetch('/orders');
                const orders = await response.json();

                const table = document.getElementById('ordersTable');
                table.innerHTML = '';

                orders.forEach(order => {
                    const row = document.createElement('tr');

                    row.innerHTML = `
                        <td>${order.id}</td>
                        <td>${order.order_id}</td>
                        <td>
                            <input id="status-${order.order_id}" value="${order.status}">
                        </td>
                        <td>
                            <input id="delivery-${order.order_id}" value="${order.expected_delivery}">
                        </td>
                        <td>
                            <button onclick="updateOrder('${order.order_id}')">Update</button>
                        </td>
                    `;

                    table.appendChild(row);
                });
            }

            async function updateOrder(orderId) {
                const status = document.getElementById(`status-${orderId}`).value;
                const expectedDelivery = document.getElementById(`delivery-${orderId}`).value;

                const response = await fetch(`/orders/${orderId}`, {
                    method: 'PATCH',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        status: status,
                        expected_delivery: expectedDelivery
                    })
                });

                const result = await response.json();

                if (result.updated) {
                    alert('Order updated successfully');
                    loadOrders();
                } else {
                    alert(result.message);
                }
            }

            loadOrders();
        </script>
    </body>
    </html>
    """
    
@app.get("/admin/products", response_class=HTMLResponse)
def products_admin_dashboard():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Product Admin Dashboard</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                background: #f4f6f8;
                padding: 30px;
            }

            h1 {
                color: #222;
            }

            a {
                display: inline-block;
                margin-right: 15px;
                margin-bottom: 20px;
                color: #222;
                font-weight: bold;
            }

            table {
                width: 100%;
                border-collapse: collapse;
                background: white;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            }

            th, td {
                padding: 12px;
                border-bottom: 1px solid #ddd;
                text-align: left;
            }

            th {
                background: #222;
                color: white;
            }

            input, button {
                padding: 6px 10px;
                margin: 2px;
            }

            input {
                width: 90%;
            }

            button {
                cursor: pointer;
                background: #222;
                color: white;
                border: none;
                border-radius: 4px;
            }
        </style>
    </head>
    <body>
        <h1>Product Admin Dashboard</h1>

        <a href="/admin">Complaint Dashboard</a>
        <a href="/admin/returns">Return Dashboard</a>
        <a href="/admin/orders">Order Dashboard</a>
        <a href="/chat">Web Chat</a>

        <table>
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Product ID</th>
                    <th>Name</th>
                    <th>Price</th>
                    <th>Stock</th>
                    <th>Category</th>
                    <th>Update</th>
                </tr>
            </thead>
            <tbody id="productsTable">
            </tbody>
        </table>

        <script>
            async function loadProducts() {
                const response = await fetch('/products');
                const products = await response.json();

                const table = document.getElementById('productsTable');
                table.innerHTML = '';

                products.forEach(product => {
                    const row = document.createElement('tr');

                    row.innerHTML = `
                        <td>${product.id}</td>
                        <td>${product.product_id}</td>
                        <td>
                            <input id="name-${product.product_id}" value="${product.name}">
                        </td>
                        <td>
                            <input id="price-${product.product_id}" type="number" value="${product.price}">
                        </td>
                        <td>
                            <input id="stock-${product.product_id}" type="number" value="${product.stock}">
                        </td>
                        <td>
                            <input id="category-${product.product_id}" value="${product.category}">
                        </td>
                        <td>
                            <button onclick="updateProduct('${product.product_id}')">Update</button>
                        </td>
                    `;

                    table.appendChild(row);
                });
            }

            async function updateProduct(productId) {
                const name = document.getElementById(`name-${productId}`).value;
                const price = parseInt(document.getElementById(`price-${productId}`).value);
                const stock = parseInt(document.getElementById(`stock-${productId}`).value);
                const category = document.getElementById(`category-${productId}`).value;

                const response = await fetch(`/products/${productId}`, {
                    method: 'PATCH',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        name: name,
                        price: price,
                        stock: stock,
                        category: category
                    })
                });

                const result = await response.json();

                if (result.updated) {
                    alert('Product updated successfully');
                    loadProducts();
                } else {
                    alert(result.message);
                }
            }

            loadProducts();
        </script>
    </body>
    </html>
    """