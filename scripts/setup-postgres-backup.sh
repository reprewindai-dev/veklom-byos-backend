#!/bin/bash
# PostgreSQL Backup Script for Veklom Production
# Run on Hetzner server (5.78.135.11) as root

# Configuration
DB_NAME="veklom"
DB_USER="veklom"
BACKUP_DIR="/data/backups/postgresql"
RETENTION_DAYS=7
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/veklom_${DATE}.sql.gz"

# Ensure backup directory exists
mkdir -p "$BACKUP_DIR"

# Create backup
echo "Starting PostgreSQL backup at $(date)"
pg_dump -h localhost -U "$DB_USER" "$DB_NAME" 2>/dev/null | gzip > "$BACKUP_FILE"

if [ $? -eq 0 ]; then
    echo "Backup created: $BACKUP_FILE"
    echo "Size: $(du -h $BACKUP_FILE | cut -f1)"
    
    # Verify backup integrity
    if gunzip -t "$BACKUP_FILE" 2>/dev/null; then
        echo "Backup integrity verified"
    else
        echo "ERROR: Backup corruption detected!" >&2
        rm -f "$BACKUP_FILE"
        exit 1
    fi
else
    echo "ERROR: Backup failed!" >&2
    rm -f "$BACKUP_FILE"
    exit 1
fi

# Clean up old backups (retention policy)
echo "Cleaning up backups older than $RETENTION_DAYS days..."
find "$BACKUP_DIR" -name "veklom_*.sql.gz" -mtime +$RETENTION_DAYS -delete

# List remaining backups
echo "Current backups:"
ls -lh "$BACKUP_DIR"/*.sql.gz 2>/dev/null || echo "No backups found"

echo "Backup completed at $(date)"
