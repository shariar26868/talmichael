from pymongo import IndexModel, ASCENDING

idx = IndexModel([("guid", ASCENDING)], unique=True)
print("document:", idx.document)
print("keys:", idx.document.get("key"))
