"""
Cache service for managing anime data and search results.
"""

import json
import os
import time
from pathlib import Path
from typing import List, Dict, Any, Optional

from ..core.exceptions import ConfigurationError
from ..models import SearchResult, Anime
from ..utils.logger import logger


class CacheService:
    """Service for managing cached anime data."""
    
    def __init__(self, cache_dir: Optional[str] = None):
        self.cache_dir = Path(cache_dir) if cache_dir else self._get_default_cache_dir()
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.anime_list_cache = self.cache_dir / "anime_list.json"
        self.search_cache = self.cache_dir / "search_cache.json"
        self.anime_details_cache = self.cache_dir / "anime_details"
        self.anime_details_cache.mkdir(exist_ok=True)
        
        # Cache settings
        self.cache_ttl = 24 * 60 * 60  # 24 hours in seconds
        self.max_search_cache_size = 1000
    
    def _get_default_cache_dir(self) -> Path:
        """Get default cache directory."""
        cache_dir = Path.home() / '.cache' / 'animepahe-dl'
        return cache_dir
    
    def save_anime_list(self, anime_list: List[SearchResult]) -> None:
        """Save anime list to cache."""
        try:
            cache_data = {
                'timestamp': time.time(),
                'data': [
                    {
                        'title': anime.title,
                        'session': anime.session,
                        'year': anime.year,
                        'status': anime.status,
                        'episodes': anime.episodes
                    }
                    for anime in anime_list
                ]
            }
            
            with open(self.anime_list_cache, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
                
            logger.info(f"Cached {len(anime_list)} anime entries")
            
        except Exception as e:
            logger.error(f"Failed to save anime list cache: {e}")
    
    def load_anime_list(self) -> List[SearchResult]:
        """Load anime list from cache."""
        try:
            if not self.anime_list_cache.exists():
                return []
            
            with open(self.anime_list_cache, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            # Check if cache is still valid
            if time.time() - cache_data.get('timestamp', 0) > self.cache_ttl:
                logger.info("Anime list cache expired")
                return []
            
            anime_list = []
            for item in cache_data.get('data', []):
                anime = SearchResult(
                    title=item['title'],
                    session=item['session'],
                    year=item.get('year'),
                    status=item.get('status'),
                    episodes=item.get('episodes')
                )
                anime_list.append(anime)
            
            logger.info(f"Loaded {len(anime_list)} anime from cache")
            return anime_list
            
        except Exception as e:
            logger.error(f"Failed to load anime list cache: {e}")
            return []
    
    def save_anime_details(self, anime: Anime) -> None:
        """Save detailed anime information to cache."""
        try:
            cache_file = self.anime_details_cache / f"{anime.slug}.json"
            cache_data = {
                'timestamp': time.time(),
                'data': anime.to_dict()
            }
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logger.error(f"Failed to save anime details cache: {e}")
    
    def load_anime_details(self, anime_slug: str) -> Optional[Anime]:
        """Load detailed anime information from cache."""
        try:
            cache_file = self.anime_details_cache / f"{anime_slug}.json"
            
            if not cache_file.exists():
                return None
            
            with open(cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            # Check if cache is still valid
            if time.time() - cache_data.get('timestamp', 0) > self.cache_ttl:
                return None
            
            return Anime.from_dict(cache_data['data'])
            
        except Exception as e:
            logger.error(f"Failed to load anime details cache: {e}")
            return None
    
    def save_search_results(self, query: str, results: List[SearchResult]) -> None:
        """Save search results to cache."""
        try:
            cache_data = {}
            if self.search_cache.exists():
                with open(self.search_cache, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
            
            # Clean old entries if cache is too large
            if len(cache_data) >= self.max_search_cache_size:
                # Remove oldest entries
                sorted_entries = sorted(
                    cache_data.items(),
                    key=lambda x: x[1].get('timestamp', 0)
                )
                # Keep only the newest half
                cache_data = dict(sorted_entries[len(sorted_entries)//2:])
            
            cache_data[query] = {
                'timestamp': time.time(),
                'results': [
                    {
                        'title': result.title,
                        'session': result.session,
                        'year': result.year,
                        'status': result.status,
                        'episodes': result.episodes
                    }
                    for result in results
                ]
            }
            
            with open(self.search_cache, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logger.error(f"Failed to save search cache: {e}")
    
    def load_search_results(self, query: str) -> Optional[List[SearchResult]]:
        """Load search results from cache."""
        try:
            if not self.search_cache.exists():
                return None
            
            with open(self.search_cache, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            if query not in cache_data:
                return None
            
            entry = cache_data[query]
            
            # Check if cache is still valid
            if time.time() - entry.get('timestamp', 0) > self.cache_ttl:
                return None
            
            results = []
            for item in entry.get('results', []):
                result = SearchResult(
                    title=item['title'],
                    session=item['session'],
                    year=item.get('year'),
                    status=item.get('status'),
                    episodes=item.get('episodes')
                )
                results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to load search cache: {e}")
            return None
    
    def clear_cache(self) -> None:
        """Clear all cached data."""
        try:
            if self.anime_list_cache.exists():
                self.anime_list_cache.unlink()
            
            if self.search_cache.exists():
                self.search_cache.unlink()
            
            # Clear anime details cache
            for cache_file in self.anime_details_cache.glob("*.json"):
                cache_file.unlink()
            
            logger.info("Cache cleared successfully")
            
        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
    
    def get_cache_size(self) -> Dict[str, int]:
        """Get cache size information."""
        try:
            anime_list_size = self.anime_list_cache.stat().st_size if self.anime_list_cache.exists() else 0
            search_cache_size = self.search_cache.stat().st_size if self.search_cache.exists() else 0
            
            details_cache_size = 0
            details_count = 0
            for cache_file in self.anime_details_cache.glob("*.json"):
                details_cache_size += cache_file.stat().st_size
                details_count += 1
            
            return {
                'anime_list_size': anime_list_size,
                'search_cache_size': search_cache_size,
                'details_cache_size': details_cache_size,
                'details_count': details_count,
                'total_size': anime_list_size + search_cache_size + details_cache_size
            }
            
        except Exception as e:
            logger.error(f"Failed to get cache size: {e}")
            return {}
    
    def is_cache_valid(self, cache_file: Path) -> bool:
        """Check if a cache file is still valid."""
        try:
            if not cache_file.exists():
                return False
            
            with open(cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            return time.time() - cache_data.get('timestamp', 0) <= self.cache_ttl
            
        except Exception:
            return False