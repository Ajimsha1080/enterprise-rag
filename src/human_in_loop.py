"""
Human-in-the-Loop Management Module with LangChain Integration
Provides centralized human review workflow management with LangChain agent integration
"""
import asyncio
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
import uuid
from threading import Lock
import logging
import json
from functools import wraps

logger = logging.getLogger(__name__)

# LangChain imports with LangGraph support
try:
    from langchain_core.messages import AIMessage, HumanMessage
    from langchain_core.tools import Tool
    from langchain_groq import ChatGroq
    from langchain_openai import ChatOpenAI
    
    # LangGraph imports for agent support
    try:
        from langgraph.prebuilt import create_react_agent
        from langgraph.graph import StateGraph
        from langgraph.graph.message import add_messages
        LANGGRAPH_AVAILABLE = True
        logger.info("LangGraph available for agent support")
    except ImportError:
        LANGGRAPH_AVAILABLE = False
        logger.warning("LangGraph not available, agents will be disabled")
    
    # Try Groq first, then fall back to OpenAI
    try:
        ChatGroq
        LLM_TYPE = "groq"
    except ImportError:
        try:
            ChatOpenAI
            LLM_TYPE = "openai"
        except ImportError:
            LLM_TYPE = "none"
    
    LANGCHAIN_AVAILABLE = LLM_TYPE != "none"
    if LANGCHAIN_AVAILABLE:
        logger.info(f"LangChain available with {LLM_TYPE} models")
        if LANGGRAPH_AVAILABLE:
            logger.info("Full agent capabilities available")
        else:
            logger.warning("LangGraph not available, human-in-the-loop will work without agent capabilities")
    else:
        logger.warning("LangChain not available, human-in-the-loop will work without agent capabilities")
except ImportError:
    LANGCHAIN_AVAILABLE = False
    LLM_TYPE = "none"
    LANGGRAPH_AVAILABLE = False
    logger.warning("LangChain not available, human-in-the-loop will work without agent capabilities")

class ReviewStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    ESCALATED = "escalated"

class ReviewPriority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class ReviewRequest:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    priority: ReviewPriority = ReviewPriority.MEDIUM
    status: ReviewStatus = ReviewStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    reviewed_at: Optional[datetime] = None
    reviewed_by: Optional[str] = None
    review_notes: Optional[str] = None
    is_approved: bool = False
    escalation_reason: Optional[str] = None
    
    def approve(self, reviewer: str, notes: Optional[str] = None):
        """Approve this review request"""
        self.status = ReviewStatus.APPROVED
        self.is_approved = True
        self.reviewed_at = datetime.now()
        self.reviewed_by = reviewer
        self.review_notes = notes
        logger.info(f"Review {self.id} approved by {reviewer}")
    
    def reject(self, reviewer: str, notes: str):
        """Reject this review request"""
        self.status = ReviewStatus.REJECTED
        self.is_approved = False
        self.reviewed_at = datetime.now()
        self.reviewed_by = reviewer
        self.review_notes = notes
        logger.info(f"Review {self.id} rejected by {reviewer}: {notes}")
    
    def escalate(self, reason: str):
        """Escalate this review request"""
        self.status = ReviewStatus.ESCALATED
        self.escalation_reason = reason
        logger.warning(f"Review {self.id} escalated: {reason}")

class HumanInLoopManager:
    """Centralized human review workflow management with LangChain integration"""
    
    def __init__(self, llm_model: str = "llama-3.3-70b-versatile", api_key: Optional[str] = None):
        self._reviews: Dict[str, ReviewRequest] = {}
        self._lock = Lock()
        self._auto_approve_threshold = timedelta(minutes=30)  # Auto-approve after 30 minutes
        
        # LangChain agent setup
        self.llm = None
        self.agent = None
        if LANGCHAIN_AVAILABLE and api_key:
            try:
                # Use appropriate LLM based on availability
                if LLM_TYPE == "groq":
                    self.llm = ChatGroq(groq_api_key=api_key, model=llm_model)
                    logger.info(f"Initialized Groq model: {llm_model}")
                elif LLM_TYPE == "openai":
                    from langchain_openai import ChatOpenAI
                    self.llm = ChatOpenAI(model=llm_model, api_key=api_key)
                    logger.info(f"Initialized OpenAI model: {llm_model}")
                
                self._setup_agent()
            except Exception as e:
                logger.warning(f"Failed to initialize LangChain agent: {e}")
    
    def _setup_agent(self):
        """Setup LangChain agent for human-in-the-loop workflows"""
        if not LANGCHAIN_AVAILABLE or not self.llm:
            return
            
        try:
            # Define tools for the agent
            review_tools = [
                Tool(
                    name="submit_review",
                    func=self._submit_review_tool,
                    description="Submit content for human review"
                ),
                Tool(
                    name="approve_review",
                    func=self._approve_review_tool,
                    description="Approve a review request"
                ),
                Tool(
                    name="reject_review",
                    func=self._reject_review_tool,
                    description="Reject a review request"
                ),
                Tool(
                    name="get_pending_reviews",
                    func=self._get_pending_reviews_tool,
                    description="Get all pending reviews"
                )
            ]
            
            # Create agent
            agent_prompt = """
            You are a human-in-the-loop management assistant using Groq LLM. You can help with:
            - Submitting content for review
            - Reviewing and approving/rejecting content
            - Managing review workflows
            
            When users submit content, you should:
            1. Assess if human review is needed
            2. Submit for review if required
            3. Provide recommendations for approval/rejection
            4. Escalate if necessary
            
            Always maintain security and follow review guidelines.
            
            You are using Groq's llama-3.3-70b-versatile model for fast and efficient processing.
            """
            
            if LANGGRAPH_AVAILABLE:
                # Use LangGraph for agent execution
                self.graph = StateGraph(add_messages)
                
                # Add the agent with tools
                self.agent = create_react_agent(
                    llm=self.llm,
                    tools=review_tools,
                    prompt=agent_prompt
                )
                
                logger.info("LangGraph agent initialized for human-in-the-loop management")
            else:
                logger.warning("LangGraph not available, using basic LangChain agent")
                # Fallback to simple LangChain without agents
                self.agent = None
            
        except Exception as e:
            logger.error(f"Failed to setup LangChain agent: {e}")
    
    async def submit_for_review(self, content: str, priority: ReviewPriority = ReviewPriority.MEDIUM, 
                               metadata: Optional[Dict[str, Any]] = None) -> ReviewRequest:
        """Submit content for human review"""
        review = ReviewRequest(
            content=content,
            priority=priority,
            metadata=metadata or {}
        )
        
        with self._lock:
            self._reviews[review.id] = review
        
        logger.info(f"Submitted review request {review.id} with priority {priority}")
        
        # Start auto-approval timer
        asyncio.create_task(self._monitor_for_auto_approval(review.id))
        
        return review
    
    async def get_review(self, review_id: str) -> Optional[ReviewRequest]:
        """Get a review request by ID"""
        with self._lock:
            return self._reviews.get(review_id)
    
    # LangChain agent tool methods
    def _submit_review_tool(self, content: str, priority: str = "MEDIUM") -> str:
        """Tool for submitting content for review"""
        try:
            priority_enum = ReviewPriority(priority.upper())
            review = asyncio.create_task(self.submit_for_review(content, priority_enum))
            return f"Review submitted successfully with priority {priority}"
        except Exception as e:
            return f"Error submitting review: {str(e)}"
    
    def _approve_review_tool(self, review_id: str, notes: str = "") -> str:
        """Tool for approving a review"""
        try:
            review = self._reviews.get(review_id)
            if not review:
                return f"Review {review_id} not found"
            
            review.approve("agent", notes)
            return f"Review {review_id} approved successfully"
        except Exception as e:
            return f"Error approving review: {str(e)}"
    
    def _reject_review_tool(self, review_id: str, notes: str) -> str:
        """Tool for rejecting a review"""
        try:
            review = self._reviews.get(review_id)
            if not review:
                return f"Review {review_id} not found"
            
            review.reject("agent", notes)
            return f"Review {review_id} rejected successfully"
        except Exception as e:
            return f"Error rejecting review: {str(e)}"
    
    def _get_pending_reviews_tool(self, priority: Optional[str] = None) -> str:
        """Tool for getting pending reviews"""
        try:
            if priority:
                priority_enum = ReviewPriority(priority.upper())
                reviews = [r for r in self._reviews.values() if r.status == ReviewStatus.PENDING and r.priority == priority_enum]
            else:
                reviews = [r for r in self._reviews.values() if r.status == ReviewStatus.PENDING]
            
            return json.dumps([{
                "id": r.id,
                "content": r.content[:100] + "..." if len(r.content) > 100 else r.content,
                "priority": r.priority.value,
                "created_at": r.created_at.isoformat()
            } for r in reviews], indent=2)
        except Exception as e:
            return f"Error getting reviews: {str(e)}"
    
    async def process_with_agent(self, content: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Process content using LangChain agent for human-in-the-loop decisions"""
        if not self.agent:
            # Fallback to basic review if agent not available
            return await self.submit_for_review(content)
        
        try:
            result = await self.agent.ainvoke({
                "messages": [HumanMessage(content=content)],
                "context": context or {}
            })
            return {
                "agent_response": result.get("output", "No response"),
                "review_required": True,
                "review_id": None
            }
        except Exception as e:
            logger.error(f"Agent processing failed: {e}")
            return await self.submit_for_review(content)
    
    async def get_pending_reviews(self, priority: Optional[ReviewPriority] = None) -> List[ReviewRequest]:
        """Get all pending reviews, optionally filtered by priority"""
        with self._lock:
            reviews = [review for review in self._reviews.values() 
                      if review.status == ReviewStatus.PENDING]
            
            if priority:
                reviews = [review for review in reviews if review.priority == priority]
            
            # Sort by priority (higher priority first) and then by creation time
        priority_order = {"critical": 4, "high": 3, "medium": 2, "low": 1}
        return sorted(reviews, key=lambda x: (priority_order.get(x.priority.value if hasattr(x.priority, 'value') else x.priority, 0), x.created_at), reverse=True)
    
    async def approve_review(self, review_id: str, reviewer: str, notes: Optional[str] = None) -> bool:
        """Approve a review request"""
        review = await self.get_review(review_id)
        if not review or review.status != ReviewStatus.PENDING:
            return False
        
        review.approve(reviewer, notes)
        return True
    
    async def reject_review(self, review_id: str, reviewer: str, notes: str) -> bool:
        """Reject a review request"""
        review = await self.get_review(review_id)
        if not review or review.status != ReviewStatus.PENDING:
            return False
        
        review.reject(reviewer, notes)
        return True
    
    async def escalate_review(self, review_id: str, reason: str) -> bool:
        """Escalate a review request"""
        review = await self.get_review(review_id)
        if not review or review.status != ReviewStatus.PENDING:
            return False
        
        review.escalate(reason)
        return True
    
    async def get_review_history(self, days: int = 7) -> List[ReviewRequest]:
        """Get review history for the specified number of days"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        with self._lock:
            return [review for review in self._reviews.values() 
                   if review.created_at >= cutoff_date]
    
    async def get_review_statistics(self) -> Dict[str, Any]:
        """Get review statistics"""
        with self._lock:
            total_reviews = len(self._reviews)
            if total_reviews == 0:
                return {
                    "total_reviews": 0,
                    "pending_reviews": 0,
                    "approved_reviews": 0,
                    "rejected_reviews": 0,
                    "escalated_reviews": 0,
                    "approval_rate": 0.0
                }
            
            pending_reviews = len([r for r in self._reviews.values() if r.status == ReviewStatus.PENDING])
            approved_reviews = len([r for r in self._reviews.values() if r.status == ReviewStatus.APPROVED])
            rejected_reviews = len([r for r in self._reviews.values() if r.status == ReviewStatus.REJECTED])
            escalated_reviews = len([r for r in self._reviews.values() if r.status == ReviewStatus.ESCALATED])
            
            approval_rate = approved_reviews / total_reviews if total_reviews > 0 else 0.0
            
            return {
                "total_reviews": total_reviews,
                "pending_reviews": pending_reviews,
                "approved_reviews": approved_reviews,
                "rejected_reviews": rejected_reviews,
                "escalated_reviews": escalated_reviews,
                "approval_rate": approval_rate
            }
    
    async def _monitor_for_auto_approval(self, review_id: str):
        """Monitor review for auto-approval after timeout"""
        await asyncio.sleep(self._auto_approve_threshold.total_seconds())
        
        with self._lock:
            if review_id in self._reviews:
                review = self._reviews[review_id]
                if review.status == ReviewStatus.PENDING:
                    review.approve("system", "Auto-approved after timeout")
                    logger.info(f"Review {review_id} auto-approved after timeout")
    
    def clear_old_reviews(self, days: int = 30):
        """Clear reviews older than specified days"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        with self._lock:
            old_reviews = [review_id for review_id, review in self._reviews.items() 
                          if review.created_at < cutoff_date]
            
            for review_id in old_reviews:
                del self._reviews[review_id]
            
            if old_reviews:
                logger.info(f"Cleared {len(old_reviews)} old reviews older than {days} days")

# Global instance
human_in_loop_manager = HumanInLoopManager()