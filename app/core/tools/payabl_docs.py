import httpx
import re
from typing import Dict, List, Any
from app.core.tools.base import BaseTool, ToolResult

class PayablDocsSearch(BaseTool):
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://docs.payabl.com"
        
    async def execute(self, query: str, category: str = None) -> ToolResult:
        try:
            # Search the documentation
            results = await self._search_docs(query, category)
            
            if not results:
                return ToolResult(
                    success=True,
                    data={
                        "message": f"No documentation found for '{query}'",
                        "query": query,
                        "category": category,
                        "results": [],
                        "total_results": 0,
                        "suggestions": [
                            "Try different keywords",
                            "Check spelling", 
                            "Use broader terms",
                            "Try category-specific searches"
                        ]
                    },
                    metadata={"query": query, "category": category}
                )
            
            formatted_results = []
            for result in results:
                formatted_results.append({
                    "title": result["title"],
                    "url": result["url"],
                    "description": result["description"],
                    "relevance_score": result["relevance_score"],
                    "category": result["category"],
                    "formatted_result": f"{result['title']} - {result['url']}"
                })
            
            response_data = {
                "query": query,
                "category": category,
                "total_results": len(results),
                "base_url": self.base_url,
                "message": f"Found {len(results)} result(s) for '{query}':",
                "results_with_urls": formatted_results,
                "urls_only": [f"{r['title']}: {r['url']}" for r in formatted_results],
                "formatted_response": "\n".join([f"• {r['formatted_result']}" for r in formatted_results])
            }
            
            return ToolResult(
                success=True,
                data=response_data,
                metadata={"query": query, "category": category}
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Error searching documentation: {str(e)}",
                metadata={"query": query, "category": category}
            )
    
    async def _search_docs(self, query: str, category: str = None) -> List[Dict[str, Any]]:
        try:
            # For demonstration purposes, we'll simulate searching multiple documentation pages
            # In a real implementation, you would crawl the actual docs site
            
            # Simulate documentation pages with content
            doc_pages = [
                {
                    "url": f"{self.base_url}/docs/getting-started",
                    "title": "Getting Started",
                    "content": "Welcome to Payabl API documentation. Learn how to integrate payment processing, handle 3DSecure, and manage transactions.",
                    "category": "API Integration"
                },
                {
                    "url": f"{self.base_url}/docs/payment-methods",
                    "title": "Payment Methods",
                    "content": "Payabl supports various payment methods including credit cards, SEPA Direct Debit, iDEAL, Sofort, and digital wallets like Apple Pay and Google Pay.",
                    "category": "Payment Methods"
                },
                {
                    "url": f"{self.base_url}/docs/3dsecure",
                    "title": "3D Secure Integration",
                    "content": "Learn how to implement 3D Secure (3DS) authentication for card payments. Includes API endpoints, redirect flows, and security best practices.",
                    "category": "3DSecure"
                },
                {
                    "url": f"{self.base_url}/docs/api-reference",
                    "title": "API Reference",
                    "content": "Complete API reference including authentication, endpoints, request/response formats, and error codes for payment processing.",
                    "category": "API Integration"
                },
                {
                    "url": f"{self.base_url}/docs/tokenization",
                    "title": "Tokenization",
                    "content": "Secure payment tokenization for storing payment methods. Learn about token_id, security benefits, and PCI compliance.",
                    "category": "Security"
                },
                {
                    "url": f"{self.base_url}/docs/webhooks",
                    "title": "Webhooks",
                    "content": "Configure webhooks to receive real-time notifications about payment status changes, refunds, and other events.",
                    "category": "API Integration"
                },
                {
                    "url": f"{self.base_url}/docs/testing",
                    "title": "Testing & Sandbox",
                    "content": "Test your integration using our sandbox environment. Includes test card numbers, test scenarios, and debugging tools.",
                    "category": "Testing"
                },
                {
                    "url": f"{self.base_url}/docs/error-codes",
                    "title": "Error Codes",
                    "content": "Comprehensive list of error codes, their meanings, and recommended actions for troubleshooting payment issues.",
                    "category": "Error Codes"
                }
            ]
            
            # Filter by category if specified
            if category:
                doc_pages = [page for page in doc_pages if self._matches_category(page, category)]
            
            # Search within pages
            results = []
            query_lower = query.lower()
            
            for page in doc_pages:
                relevance_score = self._calculate_relevance(page, query_lower)
                if relevance_score > 0:
                    results.append({
                        "title": page["title"],
                        "url": page["url"],
                        "description": page["content"][:200] + "..." if len(page["content"]) > 200 else page["content"],
                        "relevance_score": relevance_score,
                        "category": page["category"]
                    })
            
            # Sort by relevance score
            results.sort(key=lambda x: x["relevance_score"], reverse=True)
            
            # Return all relevant results (no limit for now)
            return results
                
        except Exception as e:
            raise Exception(f"Failed to search documentation: {str(e)}")
    
    def _matches_category(self, page: Dict[str, Any], category: str) -> bool:
        return page["category"] == category
    
    def _calculate_relevance(self, page: Dict[str, Any], query: str) -> float:
        score = 0.0
        
        # Title relevance (highest weight)
        if query in page["title"].lower():
            score += 5.0
        
        # Content relevance
        if query in page["content"].lower():
            score += 3.0
        
        # Category relevance
        if query in page["category"].lower():
            score += 2.0
        
        # URL relevance
        if query in page["url"].lower():
            score += 1.5
        
        # Partial matches and word matching
        words = query.split()
        for word in words:
            if word in page["title"].lower():
                score += 1.0
            if word in page["content"].lower():
                score += 0.5
            if word in page["category"].lower():
                score += 0.3
        
        return score
