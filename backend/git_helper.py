import subprocess
import os
from pathlib import Path

def get_git_root(path="."):
    try:
        root = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=path,
            stderr=subprocess.DEVNULL
        ).decode().strip()
        return Path(root)
    except Exception:
        return None

def get_modified_files(cwd="."):
    """Returns a list of files that differ between the current branch and main, or unstaged modifications."""
    root = get_git_root(cwd)
    if not root:
        return []
    
    files = set()
    try:
        # Check against main/master branch first
        target_branch = "main"
        try:
            subprocess.check_call(["git", "rev-parse", "--verify", "main"], cwd=root, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError:
            target_branch = "master"
            
        diff_files = subprocess.check_output(
            ["git", "diff", "--name-only", target_branch],
            cwd=root,
            stderr=subprocess.DEVNULL
        ).decode().splitlines()
        files.update(diff_files)
    except Exception:
        pass
    
    try:
        # Also include uncommitted/unstaged local changes
        status_files = subprocess.check_output(
            ["git", "status", "--porcelain"],
            cwd=root
        ).decode().splitlines()
        for line in status_files:
            if line:
                # Format: XY filename -> we want the filename part
                parts = line[3:].strip().split(" -> ")
                files.add(parts[-1])
    except Exception:
        pass
        
    # Filter out deleted files and return absolute paths
    result = []
    for f in sorted(list(files)):
        full_path = root / f
        if full_path.exists() and full_path.is_file():
            result.append(full_path)
            
    return result

def get_git_diff(cwd="."):
    """Get the full git diff of modified/unstaged files."""
    root = get_git_root(cwd)
    if not root:
        return ""
    
    try:
        target_branch = "main"
        try:
            subprocess.check_call(["git", "rev-parse", "--verify", "main"], cwd=root, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError:
            target_branch = "master"
            
        diff_out = subprocess.check_output(
            ["git", "diff", target_branch],
            cwd=root,
            stderr=subprocess.DEVNULL
        ).decode()
        
        # If empty, try unstaged changes only
        if not diff_out:
            diff_out = subprocess.check_output(["git", "diff"], cwd=root).decode()
            
        return diff_out
    except Exception as e:
        return f"Error reading git diff: {e}"

def get_file_content(path):
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except Exception as e:
        return f"Error reading file {path}: {e}"

# MOCK DATA FOR DEMO MODE
MOCK_FILES = {
    "src/utils/payment_processor.py": """import os
import json
import requests
import hashlib
import time

# Unused/redundant helper utility functions that Paritok should compress out
def parse_date_to_epoch(date_str):
    print("Formatting date string input: " + date_str)
    # 20 lines of redundant parsing logic
    if not date_str:
        return time.time()
    try:
        from datetime import datetime
        dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
        return int(dt.timestamp())
    except:
        return int(time.time())

def log_debug_info(module_name, action, payload_data):
    # Verbose logging helper
    formatted_payload = json.dumps(payload_data, indent=4)
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] DEBUG ({module_name}) -> Action: {action}")
    print(f"Payload Size: {len(formatted_payload)} bytes")
    print(f"Payload: {formatted_payload}")

def generate_checksum_v1(input_bytes):
    # Old hashing mechanism kept for compatibility
    m = hashlib.md5()
    m.update(input_bytes)
    return m.hexdigest()

# CORE BUSINESS LOGIC (Must NOT be compressed or lost)
class PaymentProcessor:
    def __init__(self, api_key, endpoint_url="https://api.paymentgateway.com/v2"):
        self.api_key = api_key
        self.endpoint_url = endpoint_url
        self.session = requests.Session()
        
    def charge_customer(self, customer_id, amount_cents, currency="USD"):
        \"\"\"Charge a customer with a specified amount. Returns transaction ID.\"\"\"
        if amount_cents <= 0:
            raise ValueError("Amount must be positive")
            
        payload = {
            "customer_id": customer_id,
            "amount": amount_cents,
            "currency": currency,
            "timestamp": time.time()
        }
        
        # Verbose Logging (Paritok should compress this)
        log_debug_info("payment_processor", "charge_customer_attempt", payload)
        
        # CORE CALL
        headers = {"Authorization": f"Bearer {self.api_key}"}
        try:
            response = self.session.post(f"{self.endpoint_url}/charges", json=payload, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return data.get("transaction_id")
            else:
                raise Exception(f"Failed to charge customer: {response.text}")
        except Exception as e:
            # Bug introduced here: catching all exceptions and just returning None, failing silently!
            # (GitLean reviewer should flag this as a critical silent failure bug)
            return None
""",
    "src/utils/test_payment.py": """import unittest
from payment_processor import PaymentProcessor

class TestPaymentProcessor(unittest.TestCase):
    def test_charge_success(self):
        # Redundant boilerplate test setup
        print("Initializing payment processor test case...")
        processor = PaymentProcessor("sk_test_123")
        
        # Test basic positive charge
        tx_id = processor.charge_customer("cust_abc123", 5000)
        # Verify result
        print(f"Charge attempt finished, tx_id returned: {tx_id}")
        # Note: self.assertIsNotNone(tx_id) was commented out by mistake!
        # self.assertIsNotNone(tx_id)
        pass
"""
}

MOCK_DIFF = """diff --git a/src/utils/payment_processor.py b/src/utils/payment_processor.py
index a2d4e9b..b76735c 100644
--- a/src/utils/payment_processor.py
+++ b/src/utils/payment_processor.py
@@ -43,6 +43,9 @@ class PaymentProcessor:
         log_debug_info("payment_processor", "charge_customer_attempt", payload)
         
         # CORE CALL
         headers = {"Authorization": f"Bearer {self.api_key}"}
         try:
             response = self.session.post(f"{self.endpoint_url}/charges", json=payload, headers=headers, timeout=10)
             if response.status_code == 200:
                 data = response.json()
                 return data.get("transaction_id")
             else:
                 raise Exception(f"Failed to charge customer: {response.text}")
         except Exception as e:
-            # Bug introduced here: catching all exceptions and just returning None, failing silently!
-            # (GitLean reviewer should flag this as a critical silent failure bug)
-            return None
+            # Modified logic (silent exception capture remains)
+            return None
"""

def get_pulled_files(cwd="."):
    """Returns list of files changed in the last pull/merge operation (comparing HEAD@{1} to HEAD)."""
    root = get_git_root(cwd)
    if not root:
        return []
    
    files = set()
    try:
        diff_files = subprocess.check_output(
            ["git", "diff", "--name-only", "HEAD@{1}", "HEAD"],
            cwd=root,
            stderr=subprocess.DEVNULL
        ).decode().splitlines()
        files.update(diff_files)
    except Exception:
        # Fallback to the last commit
        try:
            diff_files = subprocess.check_output(
                ["git", "diff", "--name-only", "HEAD~1", "HEAD"],
                cwd=root,
                stderr=subprocess.DEVNULL
            ).decode().splitlines()
            files.update(diff_files)
        except Exception:
            pass
            
    result = []
    for f in sorted(list(files)):
        full_path = root / f
        if full_path.exists() and full_path.is_file():
            result.append(full_path)
    return result

def get_pulled_diff(cwd="."):
    """Returns the git diff representing the changes introduced by the last pull/merge."""
    root = get_git_root(cwd)
    if not root:
        return ""
    try:
        diff_out = subprocess.check_output(
            ["git", "diff", "HEAD@{1}", "HEAD"],
            cwd=root,
            stderr=subprocess.DEVNULL
        ).decode()
        if diff_out:
            return diff_out
    except Exception:
        pass
        
    try:
        diff_out = subprocess.check_output(
            ["git", "diff", "HEAD~1", "HEAD"],
            cwd=root,
            stderr=subprocess.DEVNULL
        ).decode()
        return diff_out
    except Exception:
        return ""

def get_demo_files():
    return MOCK_FILES

def get_demo_diff():
    return MOCK_DIFF
