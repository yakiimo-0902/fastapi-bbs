from app.database import engine

SQL = """
ALTER TABLE posts ADD COLUMN attachment TEXT;
"""

def run():
    with engine.connect() as conn:
        conn.exec_driver_sql(SQL)
        print("✔ attachment カラムを追加しました")

if __name__ == "__main__":
    run()