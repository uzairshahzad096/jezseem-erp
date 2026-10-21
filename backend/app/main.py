import logging
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.auth.router import router as auth_router
from app.calibration.router import router as calibration_router
from app.leads.router import router as leads_router
from app.crm.router import router as crm_router
from app.security.router import router as security_router
from app.companies.router import router as companies_router
from app.core.config import settings
from app.dashboard.router import router as dashboard_router
from app.exports.router import router as exports_router
from app.finance.errors import FinanceError
from app.finance.imported_vouchers import router as imported_vouchers_router
from app.finance.router import router as finance_router
from app.receivables.router import ar_router, sales_router as sales_invoice_router
from app.gatepass.router import router as gatepass_router
from app.hrms.router import router as hrms_router
from app.inventory.images import MEDIA_URL_PREFIX
from app.inventory.router import router as inventory_router
from app.partners.router import router as partners_router
from app.procurement.router import router as procurement_router
from app.sales.router import router as sales_router
from app.documents.router import router as documents_router
from app.reports.router import router as reports_router

logger = logging.getLogger("jezseem")
logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Guard: the development auth bypass must never reach production ---
if settings.AUTH_DISABLED:
    if settings.ENVIRONMENT.lower() == "production":
        raise RuntimeError(
            "AUTH_DISABLED=true with ENVIRONMENT=production. "
            "Authentication cannot be bypassed in production Ã¢â‚¬â€ set AUTH_DISABLED=false."
        )
    logger.warning(
        "=" * 72 + "\n"
        "  AUTH_DISABLED is ON. Every request runs as '%s' and all\n"
        "  permission checks pass. Development only Ã¢â‚¬â€ set AUTH_DISABLED=false\n"
        "  before this system holds real data.\n" + "=" * 72,
        settings.DEV_USER_USERNAME,
    )


@app.get("/api/v1/auth/status", tags=["auth"])
def auth_status():
    """Lets the frontend know whether it should show a login screen."""
    return {"auth_required": not settings.AUTH_DISABLED}


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """
    Turn any unhandled error into a JSON response carrying CORS headers.

    Without this, Starlette's default 500 bypasses CORSMiddleware, the browser
    blocks the response, and the frontend reports a bare "Failed to fetch" with
    no clue what broke. Per spec section 24: the user sees a reference code,
    the technical detail goes to the server log only.
    """
    reference = uuid.uuid4().hex[:8]
    logger.exception("Unhandled error [%s] on %s %s", reference, request.method, request.url.path)

    origin = request.headers.get("origin")
    headers = {}
    if origin and origin in settings.CORS_ORIGINS:
        headers["Access-Control-Allow-Origin"] = origin
        headers["Access-Control-Allow-Credentials"] = "true"

    return JSONResponse(
        status_code=500,
        headers=headers,
        content={
            "detail": (
                "Something went wrong on the server. "
                f"Quote reference {reference} when reporting this."
            ),
            "reference": reference,
        },
    )


@app.exception_handler(FinanceError)
async def finance_error_handler(request: Request, exc: FinanceError):
    """Finance services raise FinanceError, not HTTPException, because the
    posting engine is also called outside requests. Its message is written
    for the user and goes out as the detail, like an HTTPException's."""
    origin = request.headers.get("origin")
    headers = {}
    if origin and origin in settings.CORS_ORIGINS:
        headers["Access-Control-Allow-Origin"] = origin
        headers["Access-Control-Allow-Credentials"] = "true"
    return JSONResponse(status_code=exc.status_code, headers=headers, content={"detail": exc.message})


@app.get("/api/health", tags=["system"])
def health_check(db: bool = False):
    """Liveness/readiness probe for Docker, Nginx and monitoring.

    `?db=true` also tries the database and says which kind of failure it hit,
    by exception class and PostgreSQL error code only, never the address or
    credentials, so a hosted deployment can be diagnosed without its logs."""
    out = {"status": "ok", "app": settings.APP_NAME, "environment": settings.ENVIRONMENT}
    if db:
        from sqlalchemy import text
        from app.core.database import engine
        try:
            with engine.connect() as conn:
                conn.execute(text("select 1"))
                out["database"] = "ok"
                out["schema_version"] = conn.execute(text("select version_num from alembic_version")).scalar()
                out["users"] = conn.execute(text("select count(*) from users")).scalar()
        except Exception as exc:  # report the kind of failure, not its text
            original = getattr(exc, "orig", None)
            out["database"] = "failed"
            out["error"] = type(original or exc).__name__
            out["sqlstate"] = getattr(original, "sqlstate", None)
        # The picture store: whether it is set up and answers, by error code only.
        from app.inventory import images
        if not images.r2_enabled():
            out["pictures"] = "local folder (R2 not configured)"
        else:
            from app.core.r2_storage import get_r2_client
            # Listing one object names the reason when refused (InvalidAccessKeyId,
            # SignatureDoesNotMatch, AccessDenied), where a HEAD only says 403.
            try:
                found = get_r2_client().list_objects_v2(Bucket=settings.R2_BUCKET_NAME, MaxKeys=1)
                out["pictures"] = "r2 ok" + ("" if found.get("KeyCount") else " (bucket is empty)")
            except Exception as exc:
                code = getattr(exc, "response", {}).get("Error", {}).get("Code") if hasattr(exc, "response") else None
                out["pictures"] = f"r2 failed: {type(exc).__name__} {code or ''}".strip()
            out["r2_bucket"] = settings.R2_BUCKET_NAME
            out["r2_key_length"] = {"account_id": len(settings.R2_ACCOUNT_ID),
                                    "access_key_id": len(settings.R2_ACCESS_KEY_ID),
                                    "secret": len(settings.R2_SECRET_ACCESS_KEY)}
    return out


# --- Uploaded files ---
# Product images are served as plain static files so an <img> tag can load
# them: a browser does not attach the bearer token to an image request, so an
# authenticated route would leave every picture broken once AUTH_DISABLED is
# switched off. Filenames are item UUIDs, which are not guessable, but this
# path performs no permission check Ã¢â‚¬â€ anyone who can reach the API and knows
# an item's id can fetch its picture. For an internal ERP behind Nginx that is
# the intended trade; if product photos ever need to be access-controlled,
# replace this mount with an authenticated route and have the frontend load
# images through fetch() into object URLs.
#
# The pictures are read through this route rather than a static folder,
# because the hosted server keeps no files: they are in Cloudflare R2 there
# (app/inventory/images.py), and on this disk when R2 is not configured.
import re


from app.inventory import images as _images

# Product pictures carry the item code (from the legacy import) or the item id;
# employee photos the employee id. Nothing else, and no path separators.
_MEDIA_KEY = re.compile(r"^(items|employees)/[A-Za-z0-9_-]{1,64}\.(jpg|png|webp)$")


@app.get(MEDIA_URL_PREFIX + "/{storage_key:path}", include_in_schema=False)
def media(storage_key: str):
    if not _MEDIA_KEY.match(storage_key):
        raise HTTPException(404, "Not found")
    data = _images.read_image(storage_key)
    if data is None:
        raise HTTPException(404, "Not found")
    # Replacing a picture keeps its name, so the browser may cache it for an
    # hour but not for days.
    return Response(data, media_type=_images.CONTENT_TYPES["." + storage_key.rsplit(".", 1)[1]],
                    headers={"Cache-Control": "public, max-age=3600"})



app.include_router(auth_router, prefix=settings.API_V1_PREFIX)
app.include_router(companies_router, prefix=settings.API_V1_PREFIX)
app.include_router(dashboard_router, prefix=settings.API_V1_PREFIX)
app.include_router(inventory_router, prefix=settings.API_V1_PREFIX)
app.include_router(partners_router, prefix=settings.API_V1_PREFIX)
app.include_router(sales_router, prefix=settings.API_V1_PREFIX)
app.include_router(documents_router, prefix=settings.API_V1_PREFIX)
app.include_router(reports_router, prefix=settings.API_V1_PREFIX)
app.include_router(exports_router, prefix=settings.API_V1_PREFIX)
app.include_router(gatepass_router, prefix=settings.API_V1_PREFIX)
app.include_router(procurement_router, prefix=settings.API_V1_PREFIX)
app.include_router(finance_router, prefix=settings.API_V1_PREFIX)
app.include_router(imported_vouchers_router, prefix=settings.API_V1_PREFIX)
app.include_router(sales_invoice_router, prefix=settings.API_V1_PREFIX)
app.include_router(ar_router, prefix=settings.API_V1_PREFIX)
app.include_router(hrms_router, prefix=settings.API_V1_PREFIX)
app.include_router(calibration_router, prefix=settings.API_V1_PREFIX)
app.include_router(leads_router, prefix=settings.API_V1_PREFIX)
app.include_router(crm_router, prefix=settings.API_V1_PREFIX)
app.include_router(security_router, prefix=settings.API_V1_PREFIX)
