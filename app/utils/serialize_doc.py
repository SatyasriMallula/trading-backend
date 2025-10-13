def serialize_doc(doc):
    """Convert MongoDB document to JSON-safe dict"""
    if not doc:
        return None
    doc = dict(doc)  # ensure it's a dict
    if "_id" in doc:
        doc["_id"] = str(doc["_id"])
    return doc