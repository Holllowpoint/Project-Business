from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from sqlalchemy import create_engine, Column, Integer, String, MetaData, Table
from sqlalchemy.orm import sessionmaker
import asyncio

app = FastAPI()

# SQLite database setup
DATABASE_URL = "sqlite:///inventory_test.db"
engine = create_engine(DATABASE_URL)
metadata = MetaData()

inventory_table = Table(
    "inventory", metadata,
    Column("id", Integer, primary_key=True),
    Column("item_name", String, unique=True),
    Column("count", Integer)
)

metadata.create_all(engine)
Session = sessionmaker(bind=engine)

# Initialize database with exactly one crate
def initialize_db():
    with Session() as session:
        conn = session.connection()
        conn.execute(inventory_table.delete())  # Clear existing data
        conn.execute(inventory_table.insert().values({"item_name": "crates", "count": 1}))
        session.commit()
        print("Database initialized with 1 crate.")

initialize_db()

# Store active WebSocket connections
connected_clients = set()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_clients.add(websocket)
    try:
        while True:
            with Session() as session:
                inventory = {row.item_name: row.count for row in session.execute(inventory_table.select())}
            await websocket.send_json({
                "inventory": inventory,
                "scores": {},
                "positions": {}
            })
            print("Sent to client:", {"inventory": inventory, "scores": {}, "positions": {}})
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        connected_clients.remove(websocket)
    except Exception as e:
        print(f"WebSocket error: {str(e)}")
        connected_clients.remove(websocket)

# Run with: uvicorn server_test:app --reload
# Note: No direct uvicorn.run() here; run from command line instead