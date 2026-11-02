"""Database schema and deterministic synthetic data generation."""
from __future__ import annotations
import random
import sqlite3
from datetime import date, timedelta
from pathlib import Path

DDL = """
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS customers (
 customer_id INTEGER PRIMARY KEY, customer_name TEXT NOT NULL, segment TEXT NOT NULL,
 region TEXT NOT NULL, signup_date TEXT NOT NULL, email_domain TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS products (
 product_id INTEGER PRIMARY KEY, product_name TEXT NOT NULL, category TEXT NOT NULL,
 unit_cost REAL NOT NULL, list_price REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS orders (
 order_id INTEGER PRIMARY KEY, customer_id INTEGER NOT NULL REFERENCES customers(customer_id),
 order_date TEXT NOT NULL, status TEXT NOT NULL, channel TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS order_items (
 order_item_id INTEGER PRIMARY KEY, order_id INTEGER NOT NULL REFERENCES orders(order_id),
 product_id INTEGER NOT NULL REFERENCES products(product_id), quantity INTEGER NOT NULL,
 unit_price REAL NOT NULL, discount REAL NOT NULL, unit_cost REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS payments (
 payment_id INTEGER PRIMARY KEY, order_id INTEGER NOT NULL REFERENCES orders(order_id),
 payment_date TEXT NOT NULL, payment_method TEXT NOT NULL, amount REAL NOT NULL,
 payment_status TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS returns (
 return_id INTEGER PRIMARY KEY, order_item_id INTEGER NOT NULL REFERENCES order_items(order_item_id),
 return_date TEXT NOT NULL, quantity INTEGER NOT NULL, refund_amount REAL NOT NULL,
 reason TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_orders_date ON orders(order_date);
CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_items_order ON order_items(order_id);
CREATE INDEX IF NOT EXISTS idx_items_product ON order_items(product_id);
"""

def create_database(path: str | Path, seed: int = 42) -> dict[str, int]:
    """Create a repeatable synthetic retail database with ~30k rows."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    rng = random.Random(seed)
    con = sqlite3.connect(path)
    con.executescript(DDL)
    cur = con.cursor()
    regions = ["North", "South", "East", "West", "Central"]
    segments = ["Consumer", "Corporate", "Small Business", "Enterprise"]
    domains = ["example.com", "mail.test", "sample.org"]
    start = date(2023, 1, 1)
    customers = []
    for i in range(1, 1201):
        d = start + timedelta(days=rng.randint(0, 900))
        customers.append((i, f"Customer {i:04d}", rng.choice(segments), rng.choice(regions), d.isoformat(), rng.choice(domains)))
    cur.executemany("INSERT INTO customers VALUES (?,?,?,?,?,?)", customers)
    categories = ["Electronics", "Home", "Office", "Outdoor", "Accessories"]
    products = []
    for i in range(1, 101):
        cost = round(rng.uniform(4, 350), 2)
        products.append((i, f"Product {i:03d}", rng.choice(categories), cost, round(cost*rng.uniform(1.25, 2.4), 2)))
    cur.executemany("INSERT INTO products VALUES (?,?,?,?,?)", products)
    item_id = payment_id = return_id = 1
    order_count = 6500
    item_rows, payment_rows, return_rows, order_rows = [], [], [], []
    reasons = ["Damaged", "Wrong item", "Changed mind", "Late delivery"]
    for oid in range(1, order_count + 1):
        customer_id = rng.randint(1, 1200)
        od = start + timedelta(days=rng.randint(0, 1095))
        status = rng.choices(["completed", "shipped", "processing", "cancelled"], [0.68, 0.16, 0.11, 0.05])[0]
        channel = rng.choice(["Web", "Mobile", "Sales rep", "Marketplace"])
        order_rows.append((oid, customer_id, od.isoformat(), status, channel))
        nitems = rng.randint(1, 4)
        order_item_ids = []
        gross_total = 0.0
        for _ in range(nitems):
            pid = rng.randint(1, 100)
            p = products[pid-1]
            qty = rng.randint(1, 5)
            price = round(p[4] * rng.uniform(0.85, 1.08), 2)
            discount = round(rng.choice([0, 0, 0, rng.uniform(0.02, 0.18)]), 3)
            item_rows.append((item_id, oid, pid, qty, price, discount, p[3]))
            order_item_ids.append((item_id, qty, price, discount))
            gross_total += qty * price * (1-discount)
            if status != "cancelled" and rng.random() < 0.035:
                rqty = rng.randint(1, qty)
                refund = round(rqty * price * (1-discount), 2)
                rd = od + timedelta(days=rng.randint(1, 35))
                return_rows.append((return_id, item_id, rd.isoformat(), rqty, refund, rng.choice(reasons)))
                return_id += 1
            item_id += 1
        if status != "cancelled":
            # Some orders have split payments, to exercise safe aggregation.
            split = rng.random() < 0.08
            amount1 = round(gross_total * (0.5 if split else 1.0), 2)
            payment_rows.append((payment_id, oid, (od+timedelta(days=rng.randint(0, 3))).isoformat(),
                                 rng.choice(["Card", "UPI", "Bank transfer", "Wallet"]), amount1,
                                 rng.choice(["paid", "paid", "paid", "pending"])))
            payment_id += 1
            if split:
                payment_rows.append((payment_id, oid, (od+timedelta(days=rng.randint(0, 3))).isoformat(),
                                     rng.choice(["Card", "UPI", "Bank transfer", "Wallet"]), round(gross_total-amount1, 2), "paid"))
                payment_id += 1
    cur.executemany("INSERT INTO orders VALUES (?,?,?,?,?)", order_rows)
    cur.executemany("INSERT INTO order_items VALUES (?,?,?,?,?,?,?)", item_rows)
    cur.executemany("INSERT INTO payments VALUES (?,?,?,?,?,?)", payment_rows)
    cur.executemany("INSERT INTO returns VALUES (?,?,?,?,?,?)", return_rows)
    con.commit()
    counts = {}
    for table in ["customers", "products", "orders", "order_items", "payments", "returns"]:
        counts[table] = cur.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    con.close()
    return counts
