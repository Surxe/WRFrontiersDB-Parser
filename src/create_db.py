import sqlite3

# Connect to (or create) a new database file
conn = sqlite3.connect('game_data.db')
cursor = conn.cursor()

# Create a sample table
cursor.execute('''
CREATE TABLE items (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    value INTEGER
)
''')

# Insert sample data
items = [
    (1, 'Iron Sword', 'Weapon', 10),
    (2, 'Health Potion', 'Consumable', 5),
    (3, 'Steel Shield', 'Armor', 15)
]

cursor.executemany('INSERT INTO items VALUES (?, ?, ?, ?)', items)

# Save and close
conn.commit()
conn.close()

print("Sample database created: game_data.db")
