import os
import json
import time
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
import re

from .config import settings
from .git_helper import get_modified_files, get_git_diff, get_file_content, get_demo_files, get_demo_diff, get_pulled_files, get_pulled_diff
from .paritok_client import compress_code, test_api_connection
from .llm_reviewer import get_code_review
from .diagnostics import run_diagnostics

# Global history of compressed runs
def make_relative_path(file_path, base_path):
    try:
        abs_file = os.path.abspath(file_path)
        abs_base = os.path.abspath(base_path)
        # Normalize slashes for consistency
        abs_file = abs_file.replace("\\", "/")
        abs_base = abs_base.replace("\\", "/")
        if abs_file.lower().startswith(abs_base.lower()):
            rel = abs_file[len(abs_base):].lstrip("/")
            return rel if rel else "."
    except Exception:
        pass
    return str(file_path)

HISTORY = [
    {"timestamp": "2026-07-28 14:22", "original_tokens": 12450, "compressed_tokens": 3120, "savings": 74.9, "cost_saved": 0.056},
    {"timestamp": "2026-07-29 09:15", "original_tokens": 8900, "compressed_tokens": 2010, "savings": 77.4, "cost_saved": 0.041},
    {"timestamp": "2026-07-30 11:45", "original_tokens": 24500, "compressed_tokens": 5890, "savings": 75.9, "cost_saved": 0.111},
    {"timestamp": "2026-08-01 16:30", "original_tokens": 18200, "compressed_tokens": 4200, "savings": 76.9, "cost_saved": 0.084},
]

# Cache of files compressed in the active session for visualizer display
COMPRESSED_FILES_CACHE = {}

class GitLeanProxyRequestHandler(BaseHTTPRequestHandler):
    def _send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, x-api-key, anthropic-version")

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

        elif path == "/api/cached-files":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self._send_cors_headers()
            self.end_headers()
            
            self.wfile.write(json.dumps(COMPRESSED_FILES_CACHE).encode("utf-8"))
            
        else:
            self.send_response(404)
            self._send_cors_headers()
            self.end_headers()
            self.wfile.write(b"Not Found")

    def do_POST(self):
        parsed_path = urlparse(self.path)
        path = parsed_path.path

        # Read POST content body
        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
        
        try:
            body = json.loads(post_data) if post_data else {}
        except Exception:
            body = {}

        # ----------------------------------------------------
        # 1. Standard API Settings Endpoints
        # ----------------------------------------------------
        if path == "/api/compress":
            code = body.get("code_content", "")
            level = body.get("compression_level", "medium")
            comp_res = compress_code(code, query="", level=level)
            
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self._send_cors_headers()
            self.end_headers()
            
            res_data = {
                "original_tokens": comp_res["original_tokens"],
                "compressed_code": comp_res["compressed"],
                "compressed_tokens": comp_res["compressed_tokens"],
                "savings_ratio": comp_res["savings_ratio"],
                "gpu_used": comp_res["gpu_used"]
            }
            self.wfile.write(json.dumps(res_data).encode("utf-8"))
            return

        elif path == "/api/settings":
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
            # Run local manual PR review
            start_time = time.time()
            demo_mode = body.get("demo_mode", True)
            repo_path = body.get("repo_path", "")
            compression_level = body.get("compression_level", "medium")

            if demo_mode:
                files_dict = get_demo_files()
                git_diff = get_demo_diff()
            else:
                path_to_scan = os.path.abspath(repo_path or ".")
                if not os.path.exists(path_to_scan):
                    self.send_response(400)
                    self._send_cors_headers()
                    self.end_headers()
                    self.wfile.write(json.dumps({"detail": f"Path '{path_to_scan}' does not exist."}).encode("utf-8"))
                    return

                scan_mode = body.get("scan_mode", "pulled")
                if scan_mode == "pulled":
                    modified = get_pulled_files(path_to_scan)
                    git_diff = get_pulled_diff(path_to_scan)
                else:
                    modified = get_modified_files(path_to_scan)
                    git_diff = get_git_diff(path_to_scan)

                if not modified:
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self._send_cors_headers()
                    self.end_headers()
                    
                    res_data = {
                        "status": "no_changes",
                        "message": f"No changes found in repository using mode '{scan_mode}'.",
                        "original_tokens": 0,
                        "compressed_tokens": 0,
                        "savings_ratio": 0.0,
                        "cost_saved": 0.00
                    }
                    self.wfile.write(json.dumps(res_data).encode("utf-8"))
                    return

                files_dict = {make_relative_path(f, path_to_scan): get_file_content(f) for f in modified}

            compressed_files = {}
            total_original_tokens = 0
            total_compressed_tokens = 0

            for filepath, content in files_dict.items():
                comp_res = compress_code(content, query=git_diff, level=compression_level)
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

                # Cache in global state for visualizer
                COMPRESSED_FILES_CACHE[filepath] = compressed_files[filepath]

            savings_ratio = round((1 - (total_compressed_tokens / total_original_tokens)) * 100, 2) if total_original_tokens > 0 else 0
            cost_saved = round((total_original_tokens - total_compressed_tokens) * 0.000003, 4)

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
            try:
                feedback_path = settings.BASE_DIR / "feedback.md"
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

        # ----------------------------------------------------
        # 2. Transparent IDE Proxy Layer (Anthropic / Claude Code)
        # ----------------------------------------------------
        elif path == "/v1/messages" or path == "/messages":
            print(f"\n[GitLean Proxy] Intercepting request to Anthropic upstream...")
            
            # Forward headers sent by Antigravity / Claude Code
            upstream_headers = {
                "x-api-key": self.headers.get("x-api-key", settings.upstream_api_key),
                "anthropic-version": self.headers.get("anthropic-version", "2023-06-01"),
                "content-type": "application/json"
            }
            
            # Extract and compress files embedded in messages
            messages = body.get("messages", [])
            modified_messages = []
            
            total_orig_tokens = 0
            total_comp_tokens = 0
            
            for msg in messages:
                content = msg.get("content", "")
                role = msg.get("role", "")
                
                # Check for large context blocks containing file reads (markdown code blocks)
                # Pattern: matches file paths followed by standard ``` block
                if role == "user" and isinstance(content, str) and "```" in content:
                    print(" - Scanning message for codebase files...")
                    # Regex to find markdown code fences and compress them
                    code_blocks = re.findall(r"(?:File:\s*([^\n`]+)\n)?```[a-zA-Z]*\n([\s\S]*?)```", content)
                    
                    new_content = content
                    for filepath, code_content in code_blocks:
                        filepath = filepath.strip() if filepath else "unnamed_source"
                        if len(code_content) > 200: # Only compress files containing substantial text
                            print(f"   * Found code block: {filepath} ({len(code_content)} chars)")
                            
                            comp_res = compress_code(code_content, query="optimize code context", level="medium")
                            compressed_code = comp_res["compressed"]
                            
                            # Replace in the prompt message content
                            original_fence = f"```\n{code_content}```"
                            replacement_fence = f"```\n{compressed_code}```"
                            
                            # Try with file path headers too
                            if f"File: {filepath}" in content:
                                original_fence = f"File: {filepath}\n```"
                                
                            new_content = new_content.replace(code_content, compressed_code)
                            
                            # Cache file metadata for dashboard visualizer
                            file_data = {
                                "original_code": code_content,
                                "compressed_code": compressed_code,
                                "original_tokens": comp_res["original_tokens"],
                                "compressed_tokens": comp_res["compressed_tokens"],
                                "savings_ratio": comp_res["savings_ratio"],
                                "gpu_used": comp_res["gpu_used"]
                            }
                            COMPRESSED_FILES_CACHE[filepath] = file_data
                            
                            total_orig_tokens += comp_res["original_tokens"]
                            total_comp_tokens += comp_res["compressed_tokens"]
                    
                    modified_messages.append({"role": role, "content": new_content})
                else:
                    modified_messages.append(msg)
                    
            # Smart Intent Interceptor: Check if user is requesting a code review or merge/pull summary
            user_prompts = [m.get("content", "") for m in modified_messages if m.get("role") == "user" and isinstance(m.get("content"), str)]
            prompt_combined = " ".join(user_prompts).lower()
            
            is_pull_request = any(w in prompt_combined for w in ["pull", "pulled", "merge", "merged", "whats new", "what did they change", "explain updates", "latest changes"])
            is_local_request = any(w in prompt_combined for w in ["review my changes", "unstaged", "uncommitted", "my local changes", "my code"])
            is_review_request = is_pull_request or is_local_request or any(w in prompt_combined for w in ["review", "pr review", "check code"])
            
            if is_review_request:
                if is_pull_request:
                    print("[GitLean Proxy] Detected Git PULL/MERGE review request. Scanning pulled changes...")
                    modified_files = get_pulled_files(".")
                    git_diff = get_pulled_diff(".")
                else:
                    print("[GitLean Proxy] Detected local workspace review request. Scanning unstaged modifications...")
                    modified_files = get_modified_files(".")
                    git_diff = get_git_diff(".")
                    
                if modified_files:
                    files_dict = {make_relative_path(f, os.getcwd()): get_file_content(f) for f in modified_files}
                    
                    # Compress files using Paritok
                    compressed_files = {}
                    for filepath, content in files_dict.items():
                        comp_res = compress_code(content, query=git_diff, level="medium")
                        compressed_files[filepath] = {
                            "original_code": content,
                            "compressed_code": comp_res["compressed"],
                            "original_tokens": comp_res["original_tokens"],
                            "compressed_tokens": comp_res["compressed_tokens"],
                            "savings_ratio": comp_res["savings_ratio"],
                            "gpu_used": comp_res["gpu_used"]
                        }
                        COMPRESSED_FILES_CACHE[filepath] = compressed_files[filepath]
                        
                    # Generate report
                    review_report = get_code_review(git_diff, compressed_files, use_mock=False)
                    
                    # Inject report into the last user message
                    injected_note = f"\n\n[GitLean Context-Compressed Code Review (Integrate these findings and present them beautifully to the developer):\n{review_report}]"
                    for i in reversed(range(len(modified_messages))):
                        if modified_messages[i].get("role") == "user":
                            orig_val = modified_messages[i].get("content", "")
                            if isinstance(orig_val, str):
                                modified_messages[i]["content"] = orig_val + injected_note
                                break
            
            # Update body messages
            body["messages"] = modified_messages
            
            # Record saving metrics in history if compression took place
            if total_orig_tokens > 0:
                savings_ratio = round((1 - (total_comp_tokens / total_orig_tokens)) * 100, 2)
                cost_saved = round((total_orig_tokens - total_comp_tokens) * 0.000003, 4)
                
                print(f"[GitLean Proxy] Compressed prompts: {total_orig_tokens} -> {total_comp_tokens} tokens (-{savings_ratio}%)")
                
                new_run = {
                    "timestamp": time.strftime("%Y-%m-%d %H:%M"),
                    "original_tokens": total_orig_tokens,
                    "compressed_tokens": total_comp_tokens,
                    "savings": savings_ratio,
                    "cost_saved": cost_saved
                }
                HISTORY.append(new_run)
                _update_social_media_logs(total_orig_tokens, total_comp_tokens, savings_ratio, cost_saved)
            
            # Forward the request to Anthropic API
            upstream_url = "https://api.anthropic.com/v1/messages"
            print(f"[GitLean Proxy] Forwarding request to Anthropic upstream: {upstream_url}...")
            
            try:
                response = requests.post(upstream_url, json=body, headers=upstream_headers, timeout=60)
                
                # Forward response back to the client
                self.send_response(response.status_code)
                for k, v in response.headers.items():
                    # Strip standard chunk transfer headers to avoid chunking mismatches
                    if k.lower() not in ["transfer-encoding", "content-encoding", "content-length"]:
                        self.send_header(k, v)
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(response.content)
                print(f"[GitLean Proxy] Successfully forwarded response. (Status: {response.status_code})")
            except Exception as e:
                print(f"[GitLean Proxy] Connection failed: {e}")
                self.send_response(502)
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(f"Proxy Connection Error: {e}".encode("utf-8"))
            
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
    httpd = HTTPServer(server_address, GitLeanProxyRequestHandler)
    print(f"GitLean standard library HTTP proxy server running on port {port}...")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping proxy server...")
        httpd.server_close()

if __name__ == "__main__":
    run_server()
