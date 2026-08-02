import requests
import logging
from .config import settings

logger = logging.getLogger("gitlean.paritok_client")

def compress_code(content: str, query: str = "", level: str = "medium", kind: str = "code") -> dict:
    """
    Compresses code content using Paritok's hosted API or local proxy.
    Returns a dictionary containing:
        - "compressed": The compressed code string.
        - "original_tokens": Estimated token count of the original content.
        - "compressed_tokens": Estimated token count of the compressed content.
        - "savings_ratio": Percentage of tokens saved.
        - "gpu_used": Boolean indicating if the hosted GPU server did the compression.
    """
    # Fallback to local proxy if use_gpu_server is false and local proxy is available,
    # but we default to calling Paritok's hosted API directly to simplify the user experience.
    api_key = settings.gpu_api_key
    base_url = "https://www.paritok.com/api"
    
    # Estimate tokens simply (1 token ~ 4 chars for estimate)
    original_char_count = len(content)
    est_original_tokens = max(1, original_char_count // 4)
    
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
        
    payload = {
        "model": "paritok-4b-v1",
        "content": content,
        "query": query,
        "level": level,
        "kind": kind,
        "upstream_model": settings.upstream_model
    }
    
    # If using local proxy fallback
    if not settings.use_gpu_server and settings.paritok_proxy_url:
        # If the user is running the local proxy daemon, we can route directly to it.
        # But for direct calls, we'll try paritok.com first.
        pass

    try:
        url = f"{base_url}/compress"
        logger.info(f"Sending compression request to Paritok hosted API: {url}")
        
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            res_data = response.json()
            compressed_content = res_data.get("compressed", content)
            gpu_used = res_data.get("gpu_available", True)
            
            comp_char_count = len(compressed_content)
            est_comp_tokens = max(1, comp_char_count // 4)
            savings = max(0.0, (1 - (est_comp_tokens / est_original_tokens)) * 100)
            
            return {
                "compressed": compressed_content,
                "original_tokens": est_original_tokens,
                "compressed_tokens": est_comp_tokens,
                "savings_ratio": round(savings, 2),
                "gpu_used": gpu_used,
                "status": "success"
            }
        else:
            logger.warning(f"Paritok API returned status {response.status_code}: {response.text}")
            return _make_fallback_response(content, f"API error {response.status_code}")
            
    except Exception as e:
        logger.error(f"Failed to communicate with Paritok API: {e}")
        return _make_fallback_response(content, str(e))

def _make_fallback_response(content: str, error_msg: str) -> dict:
    """Returns the original content unmodified with 0% savings on error."""
    original_char_count = len(content)
    est_original_tokens = max(1, original_char_count // 4)
    return {
        "compressed": content,
        "original_tokens": est_original_tokens,
        "compressed_tokens": est_original_tokens,
        "savings_ratio": 0.0,
        "gpu_used": False,
        "status": f"fallback ({error_msg})"
    }

def test_api_connection(api_key: str = None) -> dict:
    """Runs a health check on the Paritok API."""
    key = api_key or settings.gpu_api_key
    base_url = "https://www.paritok.com/api"
    headers = {}
    if key:
        headers["Authorization"] = f"Bearer {key}"
        
    try:
        response = requests.get(f"{base_url}/test", headers=headers, timeout=10)
        return {
            "status_code": response.status_code,
            "response": response.json() if response.status_code == 200 else response.text,
            "headers_sent": {"Authorization": "Bearer ***" if key else "None"}
        }
    except Exception as e:
        return {
            "status_code": 0,
            "error": str(e),
            "headers_sent": {"Authorization": "Bearer ***" if key else "None"}
        }
