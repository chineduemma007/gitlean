import os
import sys
import json
import argparse
import requests

# Add current folder to path to enable package imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.config import settings
from backend.git_helper import get_modified_files, get_git_diff, get_file_content, get_demo_files, get_demo_diff
from backend.paritok_client import compress_code
from backend.llm_reviewer import get_code_review

def run_local_review(demo_mode=False, level="medium"):
    print("====================================================")
    print(" GitLean CLI PR Reviewer (Token-Efficient)")
    print("====================================================")
    
    if demo_mode:
        print("Mode: DEMO MODE (using mock repositories)")
        files_dict = get_demo_files()
        git_diff = get_demo_diff()
    else:
        print("Mode: LOCAL WORKSPACE SCAN")
        modified = get_modified_files(".")
        if not modified:
            print("No modified or unstaged files found. Try running with --demo flag!")
            return
        files_dict = {str(f.relative_to(os.getcwd())): get_file_content(f) for f in modified}
        git_diff = get_git_diff(".")
        
    print(f"Files to analyze: {list(files_dict.keys())}")
    print("Compressing context via Paritok model layer...")
    
    compressed_files = {}
    total_original = 0
    total_compressed = 0
    
    for filepath, content in files_dict.items():
        comp_res = compress_code(content, query=git_diff, level=level)
        compressed_files[filepath] = {
            "original_code": content,
            "compressed_code": comp_res["compressed"],
            "original_tokens": comp_res["original_tokens"],
            "compressed_tokens": comp_res["compressed_tokens"],
            "savings_ratio": comp_res["savings_ratio"]
        }
        total_original += comp_res["original_tokens"]
        total_compressed += comp_res["compressed_tokens"]
        print(f" - {filepath}: Compressed {comp_res['original_tokens']} -> {comp_res['compressed_tokens']} tokens (-{comp_res['savings_ratio']}%)")

    savings_ratio = round((1 - (total_compressed / total_original)) * 100, 1) if total_original > 0 else 0
    print(f"\nOverall Token Savings: {savings_ratio}% ({total_original} raw vs {total_compressed} compressed)")
    
    print("\nRequesting AI code review comment blocks...")
    review = get_code_review(git_diff, compressed_files, use_mock=demo_mode)
    
    print("\n================ REVIEW REPORT ================")
    print(review)
    print("================================================")
    
    # Write report locally
    output_path = "gitlean_review.md"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(review)
    print(f"Review report saved to {output_path}")

def run_github_action():
    print("Running GitLean PR Reviewer in GitHub Action...")
    
    # 1. Read GitHub Action Environment Variables
    event_path = os.getenv("GITHUB_EVENT_PATH")
    github_token = os.getenv("GITHUB_TOKEN")
    repo = os.getenv("GITHUB_REPOSITORY") # format: owner/repo
    
    if not event_path or not github_token or not repo:
        print("Error: Missing GITHUB_EVENT_PATH, GITHUB_TOKEN, or GITHUB_REPOSITORY.")
        print("This command is meant to run inside a GitHub Actions environment.")
        sys.exit(1)
        
    # Read PR event details
    try:
        with open(event_path, "r") as f:
            event_data = json.load(f)
            
        pr_number = event_data.get("pull_request", {}).get("number")
        comments_url = event_data.get("pull_request", {}).get("_links", {}).get("comments", {}).get("href")
    except Exception as e:
        print(f"Failed to parse GITHUB_EVENT_PATH: {e}")
        sys.exit(1)
        
    if not pr_number or not comments_url:
        print("Error: Event details indicate this is not a Pull Request event.")
        sys.exit(0)
        
    print(f"Pull Request Identified: #{pr_number} in repo: {repo}")
    
    # 2. Scan changes inside the runner
    modified = get_modified_files(".")
    if not modified:
        print("No changed files found in the checkout directory.")
        sys.exit(0)
        
    files_dict = {str(f.relative_to(os.getcwd())): get_file_content(f) for f in modified}
    git_diff = get_git_diff(".")
    
    print(f"Analyzing {len(files_dict)} changed files...")
    
    # 3. Compress using Paritok
    compressed_files = {}
    total_original = 0
    total_compressed = 0
    
    for filepath, content in files_dict.items():
        comp_res = compress_code(content, query=git_diff, level="medium")
        compressed_files[filepath] = {
            "original_code": content,
            "compressed_code": comp_res["compressed"],
            "original_tokens": comp_res["original_tokens"],
            "compressed_tokens": comp_res["compressed_tokens"]
        }
        total_original += comp_res["original_tokens"]
        total_compressed += comp_res["compressed_tokens"]

    savings_ratio = round((1 - (total_compressed / total_original)) * 100, 1) if total_original > 0 else 0
    print(f"Paritok compression finished! Saved {savings_ratio}% of input tokens.")
    
    # 4. Request review from LLM (using real upstream keys or mock)
    # The action expects real tokens from settings or env
    review = get_code_review(git_diff, compressed_files, use_mock=False)
    
    # Append the token savings badge and metrics to the top of the PR comment
    badge = f"![Built with Paritok](https://img.shields.io/badge/Context--Compressed--by-Paritok-{savings_ratio}%25-1f2d3d)\n\n"
    header = f"### ⚡ GitLean Code Review Summary\n"
    metrics = f"- **Raw Context Size**: {total_original} tokens\n- **Compressed Context Size**: {total_compressed} tokens\n- **Token Reduction**: **{savings_ratio}% saved** via Paritok compression!\n\n---\n"
    
    full_comment = badge + header + metrics + review
    
    # 5. Post comment to GitHub PR
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json"
    }
    payload = {"body": full_comment}
    
    try:
        print(f"Posting review to GitHub comments URL: {comments_url}")
        res = requests.post(comments_url, json=payload, headers=headers)
        if res.status_code == 201:
            print("Successfully posted GitLean code review comment to GitHub PR!")
        else:
            print(f"Failed to post comment. Status: {res.status_code}, Body: {res.text}")
    except Exception as e:
        print(f"Network error trying to post PR comment: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GitLean CLI tool for token-efficient code reviews.")
    parser.add_argument("--review", action="store_true", help="Run a code review on local workspace modifications.")
    parser.add_argument("--demo", action="store_true", help="Run in mock demo mode.")
    parser.add_argument("--github-action", action="store_true", help="Run inside a GitHub Action workflow.")
    parser.add_argument("--level", default="medium", choices=["low", "medium", "high"], help="Compression level.")
    
    args = parser.parse_args()
    
    if args.github_action:
        run_github_action()
    elif args.review:
        run_local_review(demo_mode=args.demo, level=args.level)
    else:
        parser.print_help()
