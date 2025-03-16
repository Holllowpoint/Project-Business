from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from typing import Dict, List
import asyncio
import sqlite3
from sqlalchemy import create_engine, Column, Integer, String, MetaData, Table
from sqlalchemy.orm import sessionmaker

app = FastAPI()

# SQLite database setup
DATABASE_URL = "sqlite:///inventory.db"
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

# Initialize database with default items
def initialize_db():
    with Session() as session:
        conn = session.connection()
        existing_items = conn.execute(inventory_table.select()).fetchall()
        if not existing_items:  # Only insert if the table is empty
            conn.execute(inventory_table.insert().values([
                {"item_name": "crates", "count": 10}
            ]))
        session.commit()

initialize_db()

# In-memory player scores and positions for multiplayer
player_scores: Dict[str, int] = {}
player_positions: Dict[str, Dict[str, int]] = {}

# Store active WebSocket connections
connected_clients: set[WebSocket] = set()

class ScoreUpdate(BaseModel):
    player: str
    points: int

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
                inventory = {row.item_name: row.count for row in session.execute(inventory_table.select())}
            await websocket.send_json({
                "inventory": inventory,
                "scores": player_scores,
                "positions": player_positions
            })
            await asyncio.sleep(1)  # Reduced to 1s for faster updates
    except WebSocketDisconnect:
        connected_clients.remove(websocket)
    except Exception as e:
        connected_clients.remove(websocket)
        print(f"WebSocket error: {str(e)}")
    finally:
        if websocket in connected_clients:
            connected_clients.remove(websocket)

@app.post("/update-score/")
async def update_score(score_update: ScoreUpdate):
    try:
        player = score_update.player.strip()
        if not player:
            return {"error": "Player name cannot be empty"}, 400
        player_scores[player] = player_scores.get(player, 0) + score_update.points
        await broadcast_update()
        return {"message": "Score updated!", "new_score": player_scores[player]}
    except Exception as e:
        return {"error": f"Failed to update score: {str(e)}"}, 500

@app.post("/collect-item/")
async def collect_item(collection: ItemCollection):
    try:
        player = collection.player.strip()
        item = collection.item.lower().strip()
        if not player or not item:
            return {"error": "Player name and item name cannot be empty"}, 400
        with Session() as session:
            result = session.execute(inventory_table.select().where(inventory_table.c.item_name == item)).fetchone()
            if result and result.count > 0:
                session.execute(inventory_table.update().where(inventory_table.c.item_name == item).values(count=result.count - 1))
                session.commit()
                player_scores[player] = player_scores.get(player, 0) + 10
                await broadcast_update()
                return {
                    "message": f"{player} collected {item}",
                    "inventory": {result.item_name: result.count - 1},
                    "score": player_scores[player]
                }
            return {"message": f"Item '{item}' not available"}, 400
    except Exception as e:
        return {"error": f"Failed to collect item: {str(e)}"}, 500

@app.post("/update-position/")
async def update_position(position: PlayerPosition):
    try:
        player = position.player.strip()
        if not player:
            return {"error": "Player name cannot be empty"}, 400
        player_positions[player] = {"x": position.x, "y": position.y}
        await broadcast_update()
        return {"message": "Position updated!"}
    except Exception as e:
        return {"error": f"Failed to update position: {str(e)}"}, 500

async def broadcast_update():
    """Broadcast inventory, scores, and positions to all connected WebSocket clients."""
    if connected_clients:
        with Session() as session:
            inventory = {row.item_name: row.count for row in session.execute(inventory_table.select())}
        message = {
            "inventory": inventory,
            "scores": player_scores,
            "positions": player_positions
        }
        for client in connected_clients:
            try:
                await client.send_json(message)
            except Exception as e:
                print(f"Error broadcasting update: {str(e)}")

# Run with: uvicorn server:app --reload