from sqlalchemy import Column, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship

from backend.core.database.database import Base
from backend.db.models.mixins import TimestampMixin, UUIDMixin

class WorkspacePlugin(Base, UUIDMixin, TimestampMixin):
    """Stores workspace-scoped plugin configurations and enablement states."""
    __tablename__ = "workspace_plugins"

    workspace_id = Column(String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    plugin_id = Column(String(255), nullable=False, index=True)
    enabled = Column(Boolean, default=False, nullable=False)
    
    # Store JSON config securely
    encrypted_config = Column(String, nullable=True)

    workspace = relationship("Workspace", back_populates="plugins")
