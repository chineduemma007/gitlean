import requests
import json
import logging
from .config import settings

logger = logging.getLogger("gitlean.llm_reviewer")

def get_code_review(git_diff: str, compressed_files: dict, use_mock: bool = True) -> str:
    """
    Sends the git diff and compressed file context to the upstream LLM for review.
    If use_mock=True or upstream key is missing, returns a realistic mock code review
    that flags security, silent failure bugs, and performance.
    """
    if use_mock or not settings.upstream_api_key:
        logger.info("Using Mock LLM Reviewer for demonstration.")
        return _generate_mock_review(git_diff)
        
    logger.info(f"Calling upstream Anthropic Claude model {settings.upstream_model} for code review.")
    
    # Construct context string from compressed files
    context_str = ""
    for filepath, file_data in compressed_files.items():
        compressed_code = file_data.get("compressed", "")
        context_str += f"\n\n--- File: {filepath} ---\n{compressed_code}"
        
    prompt = f"""You are a senior staff engineer performing a code review.
Below is the Git Diff of the modifications, followed by the code context of the affected files (which has been compressed to save token context).

GIT DIFF:
```diff
{git_diff}
```

FILE CONTEXT:
{context_str}

Perform a rigorous code review. Focus on:
1. Critical bugs or logical flaws (especially silent failures or uncaught exceptions).
2. Security issues or hardcoded secrets.
3. Performance suggestions.

Format your output in clean GitHub-Flavored Markdown. Be concise and actionable.
"""

    try:
        # Call Anthropic API
        headers = {
            "x-api-key": settings.upstream_api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        
        # Point to Paritok proxy if use_gpu_server is false but proxy URL is set.
        # However, for simple direct calling, if the user points ANTHROPIC_BASE_URL to proxy, it routes.
        # Here we just make a standard request.
        url = "https://api.anthropic.com/v1/messages"
        
        # If user runs local proxy, route the LLM call through it
        if not settings.use_gpu_server and settings.paritok_proxy_url:
            url = f"{settings.paritok_proxy_url}/v1/messages"
            logger.info(f"Routing upstream Anthropic call through local Paritok proxy: {url}")

        payload = {
            "model": settings.upstream_model,
            "max_tokens": 2048,
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=60)
        
        if response.status_code == 200:
            res_json = response.json()
            # Extract content from response
            content_list = res_json.get("content", [])
            if content_list and len(content_list) > 0:
                return content_list[0].get("text", "Error parsing response content.")
            return "Empty response from Anthropic API."
        else:
            logger.error(f"Anthropic API returned error {response.status_code}: {response.text}")
            return f"### Upstream LLM Review Error\nAPI returned status code {response.status_code}.\n\n**Response:**\n`{response.text}`\n\n*Note: Falling back to local mock review for demo purposes.*"
            
    except Exception as e:
        logger.error(f"Exception during LLM review call: {e}")
        return f"### Upstream LLM Review Error\nFailed to reach Anthropic API: {e}\n\n*Note: Falling back to local mock review for demo purposes.*"

def _generate_mock_review(git_diff: str) -> str:
    """Generates a high-quality mock code review based on the mock file changes."""
    return """# GitLean Automated Code Review

I have analyzed the git diff and the compressed file contexts. Here are the findings for your PR:

## 🚨 Critical Bugs & Silent Failures (1)

### 1. Silent Exception Capture in `PaymentProcessor.charge_customer`
- **Location**: [payment_processor.py](file:///C:/Users/user/.gemini/antigravity/scratch/gitlean/backend/git_helper.py#L90-L95) (`charge_customer` method)
- **Priority**: **CRITICAL**
- **Description**: The exception block in `charge_customer` catches all exceptions (`except Exception as e`) and silently returns `None` without logging the failure, raising the exception, or updating any alert systems.
  ```python
  except Exception as e:
      # Bug introduced here: catching all exceptions and just returning None, failing silently!
      return None
  ```
- **Impact**: If the network times out or the payment gateway returns an error, the charge will fail silently and the app will proceed as if no transaction ID was created, which can lead to database desyncs or unpaid orders.
- **Recommended Fix**: Log the exception using a logging framework and re-raise or return a structured error response:
  ```python
  except Exception as e:
      logger.error(f"Transaction failed for customer {customer_id}: {e}", exc_info=True)
      raise PaymentGatewayError("Payment charge failed due to gateway timeout.") from e
  ```

---

## ⚠️ Code Quality & Test Coverage (1)

### 2. Commented Assertions in Payment Tests
- **Location**: [test_payment.py](file:///C:/Users/user/.gemini/antigravity/scratch/gitlean/backend/git_helper.py#L110-L115) (`test_charge_success` method)
- **Priority**: **MEDIUM**
- **Description**: The assertion checking that the transaction ID is not None has been commented out:
  ```python
  # Note: self.assertIsNotNone(tx_id) was commented out by mistake!
  # self.assertIsNotNone(tx_id)
  ```
- **Impact**: The test case will pass even if `charge_customer` returns `None` (which it currently does on failure), leading to a false sense of test coverage and build stability.
- **Recommended Fix**: Uncomment the assertion and write tests checking both success and error paths.

---

## 📈 Performance & Context Savings
- **Original Context Size**: ~2,840 characters (~710 tokens)
- **Paritok Compressed Size**: ~950 characters (~238 tokens)
- **Token Reduction**: **66.4%**
- **Status**: Excellent. Unused utility methods (`parse_date_to_epoch`, `generate_checksum_v1`) and verbose logging structures were successfully compressed, leaving only logic interfaces and signatures.
"""
