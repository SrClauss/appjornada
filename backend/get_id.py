from pymongo import MongoClient

client = MongoClient("mongodb://admin_jornada:b824b0f9-a9a7-47b0-8e1f-7b6e927c3da8@localhost:27017/appjornada?authSource=admin")
db = client.get_default_database()
latest = db.jornadas.find().sort("_id", -1).limit(1)
for j in latest:
    print("appjornada:", j["_id"])
