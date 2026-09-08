with open('backend/db/models/__init__.py', 'a') as f:
    f.write('\nfrom backend.db.models.vlink_binding import VLinkBinding\n__all__.append("VLinkBinding")\n')
