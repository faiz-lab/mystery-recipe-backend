from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")

# 连接 MongoDB
client = MongoClient(MONGO_URI)

# 选择数据库
db = client["mystery_recipe"]   # 改成你要用的数据库名，比如 sample_mflix
