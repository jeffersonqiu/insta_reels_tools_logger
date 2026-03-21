from supabase import Client, create_client

from config import settings


def _build_client() -> Client | None:
    if not settings.supabase_url or not settings.supabase_service_key:
        return None
    return create_client(settings.supabase_url, settings.supabase_service_key)


supabase: Client | None = _build_client()


def get_supabase() -> Client:
    if supabase is None:
        raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be configured.")
    return supabase
