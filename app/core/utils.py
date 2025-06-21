def convert_mongo_id(doc: dict) -> dict:
    if "_id" in doc and not isinstance(doc["_id"], str):
        doc["_id"] = str(doc["_id"])
    return doc
