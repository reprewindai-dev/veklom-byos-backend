from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
    scopes={
        "capi:execute": "Execute CAPI runs",
        "capi:stream": "Read CAPI SSE streams",
        "ledger:read": "Read VNP ledger",
        "workspace:read": "Read workspace data",
        "workspace:execute": "Execute workspace runs",
    },
)
