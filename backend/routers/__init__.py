# ==============================================================================
# Copyright (c) 2026 IT support BD (https://itsupport.com.bd)
# Made By Arif (https://arifmahmud.com/)
# Project: MyAgent | Version: 2.2.0
# ==============================================================================

from .chat import router as chat_router
from .documents import router as documents_router
from .memory import router as memory_router
from .settings import router as settings_router
from .auth import router as auth_router
from .sessions import router as sessions_router
from .users import router as users_router
from .dashboard import router as dashboard_router
from .models_mgmt import router as models_mgmt_router
from .mcp_router import router as mcp_router
from .security_router import router as security_router

