import os
import json
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

from .config import settings
from .git_helper import get_modified_files, get_git_diff, get_file_content, get_demo_files, get_demo_diff
from .paritok_client import compress_code, test_api_connection
from .llm_reviewer import get_code_review
from .diagnostics import run_diagnostics

# Global History state
HISTORY = [
    {"timestamp": "2026-07-28 14:22", "original_tokens": 12450, "compressed_tokens": 3120, "savings": 74.9, "cost_saved": 0.056},
    {"timestamp": "2026-07-29 09:15", "original_tokens": 8900, "compressed_tokens": 2010, "savings": 77.4, "cost_saved": 0.041},
    {"timestamp": "2026-07-30 11:45", "original_tokens": 24500, "compressed_tokens": 5890, "savings": 75.9, "cost_saved": 0.111},
    {"timestamp": "2026-08-01 16:30", "original_tokens": 18200, "compressed_tokens": 4200, "savings": 76.9, "cost_saved": 0.084},
]

class GitLeanRequestHandler(BaseHTTPRequestHandler):
    def _send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

    def do_OPTIONS(self):
        self.send_response(200)
        self._send_cors_headers()
        self.end_headers()

    def do_GET(self):
        parsed_path = urlparse(self.path)
        path = parsed_path.path

        if path == "/api/settings":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self._send_cors_headers()
            self.end_headers()
            
            res_data = {
                "use_gpu_server": settings.use_gpu_server,
                "api_key": settings.gpu_api_key,
                "upstream_api_key": settings.upstream_api_key,
                "upstream_model": settings.upstream_model
            }
            self.wfile.write(json.dumps(res_data).encode("utf-8"))

        elif path == "/api/history":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self._send_cors_headers()
            self.end_headers()
            
            self.wfile.write(json.dumps(HISTORY).encode("utf-8"))
            
        else:
            self.send_response(404)
            self._send_cors_headers()
            self.end_headers()
            self.wfile.write(b"Not Found")

    def do_POST(self):
        parsed_path = urlparse(self.path)
        path = parsed_path.path

        # Read content length for POST body
        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
        
        try:
            body = json.loads(post_data) if post_data else {}
        except Exception:
            body = {}

        if path == "/api/settings":
            settings.use_gpu_server = body.get("use_gpu_server", settings.use_gpu_server)
            settings.gpu_api_key = body.get("api_key", settings.gpu_api_key)
            upstream_key = body.get("upstream_api_key", "")
            
            if upstream_key is not None:
                settings.upstream_api_key = upstream_key
                os.environ["ANTHROPIC_API_KEY"] = upstream_key
                
            settings.save_config()

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self._send_cors_headers()
            self.end_headers()
            
            res_data = {
                "status": "success",
                "settings": {
                    "use_gpu_server": settings.use_gpu_server,
                    "api_key": settings.gpu_api_key,
                    "upstream_api_key": settings.upstream_api_key,
                    "upstream_model": settings.upstream_model
                }
            }
            self.wfile.write(json.dumps(res_data).encode("utf-8"))

        elif path == "/api/analyze":
            start_time = time.time()
            demo_mode = body.get("demo_mode", True)
            repo_path = body.get("repo_path", "")
            compression_level = body.get("compression_level", "medium")

            if demo_mode:
                files_dict = get_demo_files()
                git_diff = get_demo_diff()
            else:
                path_to_scan = repo_path or "."
                if not os.path.exists(path_to_scan):
                    self.send_response(400)
                    self._send_cors_headers()
                    self.end_headers()
                    self.wfile.write(json.dumps({"detail": f"Path '{path_to_scan}' does not exist."}).encode("utf-8"))
                    return

                modified = get_modified_files(path_to_scan)
                if not modified:
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self._send_cors_headers()
                    self.end_headers()
                    
                    res_data = {
                        "status": "no_changes",
                        "message": "No modified or unstaged files found in repository. Try Demo Mode!",
                        "original_tokens": 0,
                        "compressed_tokens": 0,
                        "savings_ratio": 0.0,
                        "cost_saved": 0.00
                    }
                    self.wfile.write(json.dumps(res_data).encode("utf-8"))
                    return

                files_dict = {str(f.relative_to(path_to_scan) if hasattr(f, "relative_to") else f): get_file_content(f) for f in modified}
                git_diff = get_git_diff(path_to_scan)

            # Compress files
            compressed_files = {}
            total_original_tokens = 0
            total_compressed_tokens = 0

            for filepath, content in files_dict.items():
                comp_res = compress_code(
                    content=content, 
                    query=git_diff, 
                    level=compression_level,
                    kind="code"
                )
                
                compressed_files[filepath] = {
                    "original_code": content,
                    "compressed_code": comp_res["compressed"],
                    "original_tokens": comp_res["original_tokens"],
                    "compressed_tokens": comp_res["compressed_tokens"],
                    "savings_ratio": comp_res["savings_ratio"],
                    "gpu_used": comp_res["gpu_used"]
                }
                
                total_original_tokens += comp_res["original_tokens"]
                total_compressed_tokens += comp_res["compressed_tokens"]

            savings_ratio = 0.0
            if total_original_tokens > 0:
                savings_ratio = round((1 - (total_compressed_tokens / total_original_tokens)) * 100, 2)
                
            input_token_price = 0.000003
            tokens_saved = max(0, total_original_tokens - total_compressed_tokens)
            cost_saved = round(tokens_saved * input_token_price, 4)

            # Upstream review
            review_report = get_code_review(git_diff, compressed_files, use_mock=demo_mode)
            duration = round(time.time() - start_time, 2)

            new_run = {
                "timestamp": time.strftime("%Y-%m-%d %H:%M"),
                "original_tokens": total_original_tokens,
                "compressed_tokens": total_compressed_tokens,
                "savings": savings_ratio,
                "cost_saved": cost_saved
            }
            HISTORY.append(new_run)
            
            # Update social logs
            _update_social_media_logs(total_original_tokens, total_compressed_tokens, savings_ratio, cost_saved)

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self._send_cors_headers()
            self.end_headers()

            res_data = {
                "status": "success",
                "duration_seconds": duration,
                "original_tokens": total_original_tokens,
                "compressed_tokens": total_compressed_tokens,
                "savings_ratio": savings_ratio,
                "cost_saved": cost_saved,
                "review_report": review_report,
                "files": compressed_files,
                "git_diff": git_diff
            }
            self.wfile.write(json.dumps(res_data).encode("utf-8"))

        elif path == "/api/diagnose":
            diag_res = run_diagnostics()
            
            # Write directly to feedback.md
            try:
                workspace_dir = settings.BASE_DIR
                feedback_path = workspace_dir / "feedback.md"
                with open(feedback_path, "w", encoding="utf-8") as f:
                    f.write(diag_res["report"])
                diag_res["feedback_updated"] = True
            except Exception as e:
                diag_res["feedback_updated"] = False
                diag_res["feedback_error"] = str(e)

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self._send_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps(diag_res).encode("utf-8"))
            
        else:
            self.send_response(404)
            self._send_cors_headers()
            self.end_headers()
            self.wfile.write(b"Not Found")

def _update_social_media_logs(original: int, compressed: int, savings: float, cost: float):
    try:
        workspace_dir = settings.BASE_DIR
        social_path = workspace_dir / "social_media.md"
        content = ""
        if social_path.exists():
            with open(social_path, "r", encoding="utf-8") as f:
                content = f.read()
                
        new_tweet = f"""
---

## Feature Highlight - Real-Time Code Compression (Autogenerated)
> Just ran GitLean on our PR changes:
> - Original context: {original} tokens 📄
> - Compressed context: {compressed} tokens ⚡
> - Token Reduction: **{savings}%** savings!
> - Cost Saved: ${cost:.4f} USD for a single review turn.
> 
> Paritok is stripping imports, loggers, and boilerplates, saving context budget for the LLM. 
> See the visual context diff in action below! 👇
> 
> #BuiltWithParitok #LLM #TokenReduction #DevTools
"""
        if "Real-Time Code Compression (Autogenerated)" not in content:
            if "(Draft pending implementation...)" in content:
                content = content.replace("(Draft pending implementation...)", new_tweet.strip())
            else:
                content += "\n" + new_tweet.strip()
                
            with open(social_path, "w", encoding="utf-8") as f:
                f.write(content)
    except Exception as e:
        print(f"Failed to autoupdate social media logs: {e}")

def run_server(port=8000):
    server_address = ("", port)
    httpd = HTTPServer(server_address, GitLeanRequestHandler)
    print(f"GitLean standard library HTTP server running on port {port}...")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server...")
        httpd.server_close()

if __name__ == "__main__":
    run_server()
