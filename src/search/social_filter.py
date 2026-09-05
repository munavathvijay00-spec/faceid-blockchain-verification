"""Social media domain identification and result filtering."""

from dataclasses import dataclass
from typing import Dict, List, Optional
from urllib.parse import urlparse
import re

@dataclass
class SocialMediaMatch:
    """Represents a matched social media post from reverse image search."""
    platform: str
    post_url: str
    title: str
    snippet: str
    source_domain: str
    author: Optional[str] = None
    thumbnail_url: Optional[str] = None
    match_score: float = 0.85

    def to_dict(self) -> Dict:
        """Converts match to serializable dictionary."""
        return {
            "platform": self.platform,
            "post_url": self.post_url,
            "title": self.title,
            "snippet": self.snippet,
            "source_domain": self.source_domain,
            "author": self.author,
            "thumbnail_url": self.thumbnail_url,
            "match_score": round(self.match_score, 4),
        }

class SocialMediaFilter:
    """Filters and ranks genuine social media post matches."""

    # Domain to platform name mapping
    PLATFORM_DOMAINS = {
        "x.com": "X (formerly Twitter)",
        "twitter.com": "X (Twitter)",
        "linkedin.com": "LinkedIn",
        "reddit.com": "Reddit",
        "instagram.com": "Instagram",
        "threads.net": "Threads",
        "facebook.com": "Facebook",
        "youtube.com": "YouTube",
        "tiktok.com": "TikTok",
        "medium.com": "Medium",
        "github.com": "GitHub",
        "pinterest.com": "Pinterest",
    }

    @classmethod
    def identify_platform(cls, url: str) -> Optional[str]:
        """Identifies if a URL belongs to a recognized social media platform."""
        try:
            domain = urlparse(url).netloc.lower()
            # Strip www. or subdomains if necessary
            for known_domain, platform_name in cls.PLATFORM_DOMAINS.items():
                if domain == known_domain or domain.endswith("." + known_domain):
                    return platform_name
        except Exception:
            pass
        return None

    @classmethod
    def extract_author(cls, platform: str, url: str, title: str) -> Optional[str]:
        """Heuristically extracts username or handle from social post URL or title."""
        parsed = urlparse(url)
        path_parts = [p for p in parsed.path.split("/") if p]

        if "X (formerly Twitter)" in platform or "X (Twitter)" in platform:
            if len(path_parts) >= 1 and path_parts[0] not in ["home", "explore", "search"]:
                return f"@{path_parts[0]}"
        elif "Reddit" in platform:
            match = re.search(r"r/([A-Za-z0-9_]+)", parsed.path)
            if match:
                return f"r/{match.group(1)}"
        elif "LinkedIn" in platform:
            match = re.search(r"/in/([A-Za-z0-9_-]+)", parsed.path)
            if match:
                return match.group(1)
        elif "Instagram" in platform:
            if len(path_parts) >= 1:
                return f"@{path_parts[0]}"

        # Fallback to title segment before dash/colon
        if title and ("-" in title or ":" in title):
            parts = re.split(r"[-:]", title)
            if len(parts) > 1:
                return parts[0].strip()

        return None

    @classmethod
    def filter_matches(cls, raw_results: List[Dict]) -> List[SocialMediaMatch]:
        """
        Takes raw reverse image search results and filters for genuine social media posts.
        Returns sorted list of SocialMediaMatch objects.
        """
        social_matches = []

        for item in raw_results:
            link = item.get("link") or item.get("url") or ""
            title = item.get("title") or ""
            snippet = item.get("snippet") or item.get("description") or ""
            thumbnail = item.get("thumbnail") or item.get("image") or ""
            source = item.get("source") or ""

            if not link:
                continue

            platform = cls.identify_platform(link)
            if platform:
                domain = urlparse(link).netloc.lower()
                author = cls.extract_author(platform, link, title)
                score = float(item.get("similarity", 0.88))

                match = SocialMediaMatch(
                    platform=platform,
                    post_url=link,
                    title=title,
                    snippet=snippet,
                    source_domain=domain,
                    author=author,
                    thumbnail_url=thumbnail,
                    match_score=score
                )
                social_matches.append(match)

        # Sort by match score descending
        social_matches.sort(key=lambda m: m.match_score, reverse=True)
        return social_matches
