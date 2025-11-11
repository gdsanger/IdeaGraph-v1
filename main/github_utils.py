"""
GitHub utility functions for IdeaGraph

This module provides common utility functions for working with GitHub repositories.
"""

from typing import Optional, Tuple


def parse_github_repo(github_repo: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Parse github_repo field to extract owner and repo name
    
    This function handles various formats:
    - owner/repo
    - https://github.com/owner/repo
    - http://github.com/owner/repo
    - github.com/owner/repo
    - https://github.com/owner/repo/ (with trailing slash)
    - https://github.com/owner/repo/tree/main (with path)
    
    Args:
        github_repo: Repository string in various formats
    
    Returns:
        Tuple of (owner, repo) or (None, None) if parsing fails
    
    Examples:
        >>> parse_github_repo('gdsanger/IdeaGraph-v1')
        ('gdsanger', 'IdeaGraph-v1')
        
        >>> parse_github_repo('https://github.com/gdsanger/IdeaGraph-v1')
        ('gdsanger', 'IdeaGraph-v1')
        
        >>> parse_github_repo('IdeaGraph-v1')
        (None, None)
    """
    if not github_repo:
        return None, None
    
    # Remove common GitHub URL prefixes
    repo_str = github_repo.strip()
    repo_str = repo_str.replace('https://github.com/', '')
    repo_str = repo_str.replace('http://github.com/', '')
    repo_str = repo_str.replace('github.com/', '')
    repo_str = repo_str.strip('/')
    
    # Split by '/' to get owner and repo
    parts = repo_str.split('/')
    if len(parts) >= 2:
        return parts[0], parts[1]
    
    return None, None
