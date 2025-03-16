from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from typing import Dict
import asyncio
from sqlalchemy import create_engine, Column, Integer, String, MetaData, Table
from sqlalchemy.orm import sessionmaker
import random

app = FastAPI()

# Database setup
DATABASE_URL = "sqlite:///inventory.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
metadata = MetaData()

inventory_table = Table(
    "inventory", metadata,
    Column("id", Integer, primary_key=True),
    Column("crate_id", String, unique=True),
    Column("x", Integer),
    Column("y", Integer),
    Column("state", String),
    Column("player", String, nullable=True)
)

metadata.create_all(engine)
Session = sessionmaker(bind=engine)

# Initialize with 10 crates
def initialize_db():
    with Session() as session:
        conn = session.connection()
        conn.execute(inventory_table.delete())
        for i in range(10):
            conn.execute(inventory_table.insert().values({
                "crate_id": f"crate_{i}",
                "x": random.randint(50, 900),
                "y": random.randint(50, 500),
                "state": "on_floor",
                "player": None
            }))
        session.commit()

initialize_db()

player_scores: Dict[str, int] = {}
player_positions: Dict[str, Dict[str, int]] = {}
connected_clients: set = set()

class ItemCollection(BaseModel):
    player: str
    item: str

class PlayerPosition(BaseModel):
    player: str
    x: int
    y: int

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_clients.add(websocket)
    try:
        while True:
            with Session() as session:
                crates = {row.crate_id: {"x": row.x, "y": row.y, "state": row.state, "player": row.player} 
                         for row in session.execute(inventory_table.select())}
            await websocket.send_json({
                "crates": crates,
                "scores": player_scores,
                "positions": player_positions
            })
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        connected_clients.remove(websocket)

@app.post("/collect-item/")
async def collect_item(collection: ItemCollection):
    with Session() as session:
        crate = session.execute(inventory_table.select().where(inventory_table.c.crate_id == collection.item)).fetchone()
        if crate and crate.state == "on_floor":
            # Pick up crate
            session.execute(inventory_table.update().where(inventory_table.c.crate_id == collection.item).values(
                state="carried", player=collection.player))
            session.commit()
            return {"message": f"{collection.player} collected {collection.item}"}
        elif crate and crate.state == "carried" and crate.player == collection.player:
            pos = player_positions.get(collection.player, {"x":0, "y":0})
            # Check if in delivery zone (example: x between 400 and 500 and y between 500 and 550)
            if 400 <= pos["x"] <= 500 and 500 <= pos["y"] <= 550:
                session.execute(inventory_table.delete().where(inventory_table.c.crate_id == collection.item))
                player_scores[collection.player] = player_scores.get(collection.player, 0) + 10
                session.commit()
                return {"message": f"{collection.player} delivered {collection.item}"}
        return {"error": "Cannot collect/deliver item"}, 400

@app.post("/update-position/")
async def update_position(position: PlayerPosition):
    player_positions[position.player] = {"x": position.x, "y": position.y}
    return {"message": "Position updated"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
