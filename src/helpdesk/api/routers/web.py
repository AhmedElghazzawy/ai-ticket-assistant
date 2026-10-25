"""The health check and the built React app. Included last, so every /api route wins."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from helpdesk.api.deps import ServicesDep

router = APIRouter()


@router.get("/api/health")
def health() -> dict[str, str]:
    """For Docker and hosting services: the app is up and answering."""
    return {"status": "ok"}


@router.get("/{path:path}", include_in_schema=False)
def web_app(path: str, services: ServicesDep) -> FileResponse:
    """Files of the built React app; any other address gets index.html and the app's router
    picks the page (e.g. /staff/tickets/2)."""
    if path.startswith("api/"):
        raise HTTPException(status_code=404, detail="Not found.")
    dist = services.dist_dir
    index = dist / "index.html"
    if not index.exists():
        raise HTTPException(
            status_code=404, detail="Frontend not built: cd frontend && npm run build"
        )
    file = (dist / path).resolve()
    # Path traversal guard: "/../.env" must never leave the dist folder.
    if path and file.is_file() and file.is_relative_to(dist.resolve()):
        return FileResponse(file)
    return FileResponse(index)
