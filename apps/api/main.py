from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from apps.api.routes import audits, google, health, metrics, shared
from apps.shared.config import get_settings
from apps.shared.observability import init_sentry

settings = get_settings()
init_sentry(settings, component="api")

app = FastAPI(
    title="BLC Website Audit Automation",
    version="0.1.0",
    description="Local-first API for Phase 1 website audit jobs.",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    swagger_ui_parameters={
        "displayRequestDuration": True,
        "filter": True,
        "tryItOutEnabled": True,
    },
)

# The CORS spec forbids combining a wildcard origin with credentials. If "*" is ever
# configured, disable credentials so the policy stays valid instead of reflecting an
# any-origin-with-credentials response.
cors_allow_credentials = "*" not in settings.api_cors_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.api_cors_origins,
    allow_credentials=cors_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(metrics.router)
app.include_router(audits.router)
app.include_router(google.router)
# Public, token-gated report sharing — intentionally NOT behind Clerk auth.
app.include_router(shared.router)


@app.get("/", include_in_schema=False)
def redirect_to_swagger() -> RedirectResponse:
    return RedirectResponse(url="/docs")
