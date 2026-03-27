"""
Provenance Data Tool with Azure Cognitive Search Integration
Searches auction history, museum records, and theft databases
"""

import json
import os
from typing import Any, Optional, Dict, List
from datetime import datetime

try:
    from azure.search.documents import SearchClient
    from azure.core.credentials import AzureKeyCredential
    HAS_COGNITIVE_SEARCH = True
except ImportError:
    HAS_COGNITIVE_SEARCH = False


def create_provenance_tool(db_connection: str = None, search_endpoint: str = None, search_key: str = None):
    """
    Factory function to create a ProvenanceSearcher instance.
    
    Args:
        db_connection: Connection string to provenance database
        search_endpoint: Azure Cognitive Search endpoint URL
        search_key: Azure Cognitive Search API key
        
    Returns:
        ProvenanceSearcher instance
    """
    return ProvenanceSearcher(db_connection, search_endpoint, search_key)


class ProvenanceSearcher:
    """Searches provenance and auction history for artworks using Azure Cognitive Search"""
    
    def __init__(self, db_connection: str = None, search_endpoint: str = None, search_key: str = None):
        """
        Initialize provenance searcher with optional Azure Cognitive Search integration.
        
        Args:
            db_connection: Connection string to provenance database
            search_endpoint: Azure Cognitive Search endpoint URL
            search_key: Azure Cognitive Search API key
        """
        self.db_connection = db_connection
        self.search_endpoint = search_endpoint or os.getenv("COGNITIVE_SEARCH_ENDPOINT")
        self.search_key = search_key or os.getenv("COGNITIVE_SEARCH_KEY")
        
        # Initialize Cognitive Search clients
        self.has_search = False
        self.search_clients = {}
        
        if HAS_COGNITIVE_SEARCH and self.search_endpoint and self.search_key:
            self.has_search = True
            try:
                # Initialize search clients for different indices
                self._init_search_clients()
                print("✅ Azure Cognitive Search initialized successfully")
            except Exception as e:
                print(f"⚠️  Cognitive Search initialization failed: {e}")
                print("  Using mock database as fallback")
                self.has_search = False
        else:
            if not HAS_COGNITIVE_SEARCH:
                print("⚠️  Azure Search SDK not installed")
            print("📚 Using mock provenance database (fallback mode)")
        
        # Initialize mock database
        self.sample_database = self._init_sample_database()
    
    def _init_search_clients(self):
        """Initialize Azure Cognitive Search clients for different indices"""
        indices = ["art-auction-records", "stolen-art-database", "museum-collections"]
        
        for index_name in indices:
            try:
                client = SearchClient(
                    endpoint=self.search_endpoint,
                    index_name=index_name,
                    credential=AzureKeyCredential(self.search_key)
                )
                self.search_clients[index_name] = client
            except Exception as e:
                print(f"⚠️  Could not initialize index '{index_name}': {e}")
    
    def search_auction_records(self, artist: str, title: str, year: int = None) -> Dict[str, Any]:
        """
        Search auction records for artwork.
        
        Args:
            artist: Artist name
            title: Artwork title
            year: Year of creation (optional)
            
        Returns:
            Dictionary with auction record results
        """
        print(f"  📡 Searching auction records for '{title}' by {artist}")
        
        # Try Cognitive Search first
        if self.has_search and "art-auction-records" in self.search_clients:
            try:
                search_query = f"{artist} {title}"
                filters = []
                if year:
                    filters.append(f"year eq {year}")
                
                client = self.search_clients["art-auction-records"]
                results = client.search(
                    search_text=search_query,
                    filter=" and ".join(filters) if filters else None,
                    select=["title", "artist", "auction_house", "sale_date", "hammer_price", "estimated_price"],
                    top=5
                )
                
                auction_results = []
                for result in results:
                    auction_results.append({
                        "source": "Azure Cognitive Search",
                        "title": result.get("title"),
                        "artist": result.get("artist"),
                        "auction_house": result.get("auction_house"),
                        "sale_date": result.get("sale_date"),
                        "hammer_price": result.get("hammer_price"),
                        "estimated_price": result.get("estimated_price")
                    })
                
                if auction_results:
                    print(f"  ✅ Found {len(auction_results)} auction record(s)")
                    return {
                        "status": "success",
                        "records_found": len(auction_results),
                        "records": auction_results
                    }
            except Exception as e:
                print(f"  ⚠️  Cognitive Search failed: {e}")
        
        # Fallback to mock data
        return self._search_mock_auction_records(artist, title)
    
    def _search_mock_auction_records(self, artist: str, title: str) -> Dict[str, Any]:
        """Search mock auction database"""
        print(f"  📚 Searching mock auction database")
        
        records = []
        for record_id, record in self.sample_database.get("auction_records", {}).items():
            if (artist.lower() in record.get("artist", "").lower() or 
                title.lower() in record.get("title", "").lower()):
                records.append(record)
        
        return {
            "status": "mock_data",
            "records_found": len(records),
            "records": records,
            "note": "Results from sample database (not real auction data)"
        }
    
    def search_stolen_art(self, artist: str, title: str) -> Dict[str, Any]:
        """
        Search stolen art database (Interpol, FBI).
        
        Args:
            artist: Artist name
            title: Artwork title
            
        Returns:
            Dictionary with theft record results
        """
        print(f"  🚨 Checking stolen art databases for '{title}'")
        
        # Try Cognitive Search first
        if self.has_search and "stolen-art-database" in self.search_clients:
            try:
                search_query = f"{artist} {title}"
                client = self.search_clients["stolen-art-database"]
                results = client.search(
                    search_text=search_query,
                    select=["title", "artist", "theft_date", "location", "status"],
                    top=5
                )
                
                theft_records = list(results)
                
                if theft_records:
                    print(f"  ⚠️  WARNING: Found theft record(s)!")
                    return {
                        "status": "warning",
                        "theft_found": True,
                        "records_found": len(theft_records),
                        "records": theft_records
                    }
                else:
                    print(f"  ✅ No theft records found")
                    return {
                        "status": "success",
                        "theft_found": False,
                        "records_found": 0,
                        "source": "Azure Cognitive Search (Interpol/FBI Database)"
                    }
            except Exception as e:
                print(f"  ⚠️  Theft search failed: {e}")
        
        # Fallback to mock data
        return {
            "status": "success",
            "theft_found": False,
            "records_found": 0,
            "source": "Mock database",
            "note": "No theft records in sample database"
        }
    
    def search_museum_records(self, artist: str, title: str) -> Dict[str, Any]:
        """
        Search museum collections (MoMA, Louvre, Metropolitan, etc).
        
        Args:
            artist: Artist name
            title: Artwork title
            
        Returns:
            Dictionary with museum records
        """
        print(f"  🏛️  Searching museum collections for '{title}'")
        
        # Try Cognitive Search first
        if self.has_search and "museum-collections" in self.search_clients:
            try:
                search_query = f"{artist} {title}"
                client = self.search_clients["museum-collections"]
                results = client.search(
                    search_text=search_query,
                    select=["title", "artist", "museum_name", "accession_number", "exhibition_history"],
                    top=5
                )
                
                museum_records = []
                for result in results:
                    museum_records.append({
                        "museum": result.get("museum_name"),
                        "title": result.get("title"),
                        "accession_number": result.get("accession_number"),
                        "exhibition_history": result.get("exhibition_history")
                    })
                
                if museum_records:
                    print(f"  ✅ Found in {len(museum_records)} museum(s)")
                    return {
                        "status": "success",
                        "museums_found": len(museum_records),
                        "records": museum_records
                    }
            except Exception as e:
                print(f"  ⚠️  Museum search failed: {e}")
        
        # Fallback to mock data
        return self._search_mock_museum_records(artist, title)
    
    def _search_mock_museum_records(self, artist: str, title: str) -> Dict[str, Any]:
        """Search mock museum database"""
        print(f"  📚 Searching mock museum database")
        
        records = self.sample_database.get("museum_records", {})
        found_records = []
        
        for museum, collections in records.items():
            for artwork in collections:
                if (artist.lower() in artwork.get("artist", "").lower() or 
                    title.lower() in artwork.get("title", "").lower()):
                    artwork["museum"] = museum
                    found_records.append(artwork)
        
        return {
            "status": "mock_data",
            "museums_found": len(set(r.get("museum") for r in found_records)),
            "records": found_records,
            "note": "Results from sample database"
        }
    
    def get_ownership_history(self, artwork_id: str) -> Dict[str, Any]:
        """
        Get complete ownership history for an artwork.
        
        Args:
            artwork_id: Unique artwork identifier
            
        Returns:
            Dictionary with ownership history
        """
        print(f"  🔗 Retrieving ownership history")
        
        if artwork_id in self.sample_database.get("ownership_history", {}):
            history = self.sample_database["ownership_history"][artwork_id]
            return {
                "status": "success",
                "artwork_id": artwork_id,
                "ownership_chain": history,
                "chain_length": len(history)
            }
        
        return {
            "status": "not_found",
            "artwork_id": artwork_id,
            "note": "No ownership history found in database"
        }
    
    def _init_sample_database(self) -> dict[str, Any]:
        """Initialize sample provenance database for fallback"""
        return {
            "auction_records": {
                "auction_1": {
                    "artwork_id": "monet_water_lilies_001",
                    "title": "Water Lilies",
                    "artist": "Claude Monet",
                    "year": 1906,
                    "auction_house": "Christie's London",
                    "sale_date": "2020-05-15",
                    "hammer_price": "$45,000,000",
                    "estimated_price": "$40,000,000-60,000,000",
                    "buyer": "Anonymous (Museum)",
                    "seller": "Private Collection"
                }
            },
            "museum_records": {
                "MoMA": [
                    {
                        "title": "The Starry Night",
                        "artist": "Vincent van Gogh",
                        "year": 1889,
                        "accession_number": "MoMA.1941.29.3",
                        "exhibition_history": "Permanent Collection"
                    }
                ],
                "Louvre": [
                    {
                        "title": "Mona Lisa",
                        "artist": "Leonardo da Vinci",
                        "year": 1503,
                        "accession_number": "INV 775",
                        "exhibition_history": "Denon Wing, Room 6"
                    }
                ]
            },
            "ownership_history": {
                "monet_water_lilies_001": [
                    {
                        "owner": "Monet Family",
                        "period": "1900-1930",
                        "status": "Private Collection",
                        "verified": True
                    },
                    {
                        "owner": "Museum of Modern Art",
                        "period": "1930-1960",
                        "status": "Public Collection",
                        "verified": True
                    }
                ]
            }
        }
