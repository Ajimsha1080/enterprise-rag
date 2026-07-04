"""
LangChain Middleware Module
Provides LangChain-integrated middleware for human-in-the-loop workflows and agent processing
"""
import asyncio
import time
import re
from datetime import datetime
from typing import Dict, Any, Optional, List, Callable, Awaitable
from fastapi import Request, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.gzip import GZipMiddleware
from starlette.responses import JSONResponse
import logging
import json

logger = logging.getLogger(__name__)

# LangChain imports
try:
    from langchain.agents import AgentExecutor, create_openai_tools_agent
    from langchain_core.messages import AIMessage, HumanMessage
    from langchain_core.runnables import RunnablePassthrough
    from langchain_core.tools import Tool
    
    # Try Groq first, then fall back to other providers
    try:
        from langchain_groq import ChatGroq
        LLM_TYPE = "groq"
    except ImportError:
        try:
            from langchain_openai import ChatOpenAI
            LLM_TYPE = "openai"
        except ImportError:
            try:
                from langchain_anthropic import ChatAnthropic
                LLM_TYPE = "anthropic"
            except ImportError:
                LLM_TYPE = "none"
    
    LANGCHAIN_AVAILABLE = LLM_TYPE != "none"
    if LANGCHAIN_AVAILABLE:
        logger.info(f"LangChain available with {LLM_TYPE} models")
    else:
        logger.warning("LangChain not available, middleware will work without agent capabilities")
except ImportError:
    LANGCHAIN_AVAILABLE = False
    LLM_TYPE = "none"
    logger.warning("LangChain not available, middleware will work without agent capabilities")

class LangChainMiddleware(BaseHTTPMiddleware):
    """LangChain-integrated middleware for human-in-the-loop workflows and agent processing"""
    
    def __init__(self, app, llm_model: str = "llama-3.3-70b-versatile", api_key: Optional[str] = None):
        super().__init__(app)
        self._requests: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()
        
        # LangChain agent setup
        self.llm = None
        self.agent_executor = None
        if LANGCHAIN_AVAILABLE and api_key:
            try:
                # Use appropriate LLM based on availability
                if LLM_TYPE == "groq":
                    self.llm = ChatGroq(groq_api_key=api_key, model=llm_model)
                    logger.info(f"Initialized Groq middleware model: {llm_model}")
                elif LLM_TYPE == "openai":
                    from langchain_openai import ChatOpenAI
                    self.llm = ChatOpenAI(model=llm_model, api_key=api_key)
                    logger.info(f"Initialized OpenAI middleware model: {llm_model}")
                elif LLM_TYPE == "anthropic":
                    from langchain_anthropic import ChatAnthropic
                    self.llm = ChatAnthropic(model=llm_model, api_key=api_key)
                    logger.info(f"Initialized Anthropic middleware model: {llm_model}")
                
                self._setup_agent()
            except Exception as e:
                logger.warning(f"Failed to initialize LangChain agent: {e}")
    
    def _setup_agent(self):
        """Setup LangChain agent for middleware processing"""
        if not LANGCHAIN_AVAILABLE or not self.llm:
            return
            
        try:
            # Define tools for the agent
            middleware_tools = [
                Tool(
                    name="process_request",
                    func=self._process_request_tool,
                    description="Process HTTP requests through LangChain agent"
                ),
                Tool(
                    name="validate_content",
                    func=self._validate_content_tool,
                    description="Validate content for security and compliance"
                ),
                Tool(
                    name="human_review",
                    func=self._human_review_tool,
                    description="Submit content for human review"
                ),
                Tool(
                    name="log_request",
                    func=self._log_request_tool,
                    description="Log request details for monitoring"
                )
            ]
            
            # Create agent
            agent_prompt = """
            You are a LangChain-powered middleware assistant for human-in-the-loop workflows using Groq LLM.
            
            Your capabilities include:
            - Processing and analyzing HTTP requests
            - Validating content for security and compliance
            - Determining when human review is needed
            - Managing review workflows
            - Logging and monitoring requests
            
            For each request, you should:
            1. Analyze the request content and context
            2. Validate for security and compliance
            3. Determine if human review is required
            4. Process or route accordingly
            5. Log all actions for monitoring
            
            Always prioritize security and user privacy.
            
            You are using Groq's llama-3.3-70b-versatile model for fast and efficient processing.
            """
            
            self.agent_executor = AgentExecutor(
                agent=create_openai_tools_agent(
                    llm=self.llm,
                    tools=middleware_tools,
                    prompt=agent_prompt
                ),
                tools=middleware_tools,
                verbose=True,
                handle_parsing_errors=True
            )
            
            logger.info("LangChain agent initialized for middleware processing")
            
        except Exception as e:
            logger.error(f"Failed to setup LangChain agent: {e}")
    
    async def dispatch(self, request: Request, call_next):
        request_id = f"req_{int(time.time() * 1000000)}_{hash(str(request.client))}"
        start_time = time.time()
        
        # Log request details
        request_info = {
            "id": request_id,
            "method": request.method,
            "url": str(request.url),
            "client": str(request.client.host) if request.client else "unknown",
            "user_agent": request.headers.get("user-agent", ""),
            "content_type": request.headers.get("content-type", ""),
            "timestamp": datetime.now().isoformat(),
            "start_time": start_time,
        }
        
        # Process with LangChain agent if available
        if self.agent_executor:
            try:
                await self._process_with_agent(request_id, request, request_info)
            except Exception as e:
                logger.error(f"Agent processing failed: {e}")
                # Continue with normal processing
        
        # Store request info
        async with self._lock:
            self._requests[request_id] = request_info
        
        logger.info(f"Request started: {request_id} - {request.method} {request.url}")
        
        # Process the request
        response = await call_next(request)
        
        # Calculate processing time
        process_time = time.time() - start_time
        
        # Update request info with response details
        response_info = {
            "status_code": response.status_code,
            "process_time": process_time,
            "response_size": len(await response.body) if hasattr(response, 'body') else 0,
            "content_type": response.headers.get("content-type", ""),
        }
        
        async with self._lock:
            if request_id in self._requests:
                self._requests[request_id].update(response_info)
        
        # Check if response requires human review
        if await self._requires_human_review(request, response):
            logger.warning(f"Response {request_id} requires human review")
            
            # Submit for review
            try:
                from human_in_loop import human_in_loop_manager, ReviewPriority
                await human_in_loop_manager.submit_for_review(
                    content=f"Response from {request.method} {request.url}",
                    priority=ReviewPriority.MEDIUM,
                    metadata={
                        "request_id": request_id,
                        "request_info": request_info,
                        "response_info": response_info,
                        "requires_review": True
                    }
                )
            except Exception as e:
                logger.error(f"Failed to submit response for review: {e}")
        
        logger.info(f"Request completed: {request_id} - {response.status_code} ({process_time:.3f}s)")
        
        return response
    
    async def _requires_human_review(self, request: Request, response: Response) -> bool:
        """Check if response requires human review"""
        # Check if path matches review endpoints
        if request.url.path.startswith("/hitl/"):
            return False
        
        # Check if response is JSON and contains review indicators
        if hasattr(response, 'body'):
            try:
                content_type = response.headers.get("content-type", "")
                if content_type.startswith("application/json"):
                    # This would need custom logic based on your response structure
                    pass
            except Exception:
                # Handle any exceptions when accessing response properties
                pass
        
        # For now, return False - customize based on your needs
        return False
    
    # LangChain agent tool methods
    async def _process_with_agent(self, request_id: str, request: Request, request_info: Dict[str, Any]) -> None:
        """Process request through LangChain agent"""
        try:
            result = await self.agent_executor.ainvoke({
                "request_id": request_id,
                "request_info": request_info,
                "url": str(request.url),
                "method": request.method,
                "headers": dict(request.headers),
                "query_params": dict(request.query_params),
            })
            
            agent_response = result.get("output", "No agent response")
            logger.info(f"Agent processed request {request_id}: {agent_response}")
            
        except Exception as e:
            logger.error(f"Agent processing failed for request {request_id}: {e}")
    
    def _process_request_tool(self, request_data: str) -> str:
        """Tool for processing requests"""
        return f"Request processed: {request_data}"
    
    def _validate_content_tool(self, content: str) -> str:
        """Tool for validating content"""
        # Add your validation logic here
        if len(content) > 1000:
            return "Content validation failed: Content too long"
        return "Content validation passed"
    
    def _human_review_tool(self, content: str, priority: str = "MEDIUM") -> str:
        """Tool for submitting human review"""
        try:
            asyncio.create_task(
                self._human_in_loop_submit(content, priority)
            )
            return f"Content submitted for human review with priority {priority}"
        except Exception as e:
            return f"Error submitting for review: {str(e)}"
    
    def _log_request_tool(self, request_id: str, action: str) -> str:
        """Tool for logging request actions"""
        logger.info(f"Request {request_id}: {action}")
        return f"Logged action: {action} for request {request_id}"
    
    async def _human_in_loop_submit(self, content: str, priority: str):
        """Submit content to human-in-the-loop system"""
        try:
            from human_in_loop import human_in_loop_manager, ReviewPriority
            priority_enum = ReviewPriority(priority.upper())
            await human_in_loop_manager.submit_for_review(content, priority_enum)
        except Exception as e:
            logger.error(f"Failed to submit to human-in-loop: {e}")

class RequestMonitoringMiddleware(BaseHTTPMiddleware):
    """Middleware for request monitoring and analytics"""
    
    def __init__(self, app):
        super().__init__(app)
        self._metrics = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "avg_response_time": 0.0,
            "requests_by_endpoint": {},
            "requests_by_hour": {},
        }
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        endpoint = request.url.path
        
        # Update metrics
        self._metrics["total_requests"] += 1
        
        if endpoint not in self._metrics["requests_by_endpoint"]:
            self._metrics["requests_by_endpoint"][endpoint] = 0
        self._metrics["requests_by_endpoint"][endpoint] += 1
        
        hour_key = datetime.now().strftime("%Y-%m-%d %H:00")
        if hour_key not in self._metrics["requests_by_hour"]:
            self._metrics["requests_by_hour"][hour_key] = 0
        self._metrics["requests_by_hour"][hour_key] += 1
        
        response = await call_next(request)
        
        # Update response time metrics
        process_time = time.time() - start_time
        
        if response.status_code < 400:
            self._metrics["successful_requests"] += 1
        else:
            self._metrics["failed_requests"] += 1
        
        # Update average response time
        total_time = self._metrics["avg_response_time"] * (self._metrics["total_requests"] - 1) + process_time
        self._metrics["avg_response_time"] = total_time / self._metrics["total_requests"]
        
        return response
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current monitoring metrics"""
        return {
            **self._metrics,
            "timestamp": datetime.now().isoformat(),
        }

class SecurityMonitoringMiddleware(BaseHTTPMiddleware):
    """Middleware for security monitoring and threat detection"""
    
    def __init__(self, app):
        super().__init__(app)
        self._suspicious_patterns = [
            r"<script[^>]*>",  # Potential XSS
            r"union\s+select",  # Potential SQL injection
            r"exec\s*\(",      # Potential command injection
            r"base64\s*\(",     # Potential encoding obfuscation
        ]
        self._rate_limit = {}
        self._block_list = set()
    
    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"
        
        # Check if client is blocked
        if client_ip in self._block_list:
            logger.warning(f"Blocked request from {client_ip}")
            from fastapi import HTTPException, status
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Rate limiting
        current_time = time.time()
        if client_ip not in self._rate_limit:
            self._rate_limit[client_ip] = []
        
        # Remove old requests (older than 1 minute)
        self._rate_limit[client_ip] = [
            req_time for req_time in self._rate_limit[client_ip]
            if current_time - req_time < 60
        ]
        
        # Check if rate limit exceeded (100 requests per minute)
        if len(self._rate_limit[client_ip]) >= 100:
            self._block_list.add(client_ip)
            logger.warning(f"Rate limit exceeded for {client_ip}, blocking access")
            from fastapi import HTTPException, status
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded"
            )
        
        # Add current request
        self._rate_limit[client_ip].append(current_time)
        
        # Check for suspicious patterns
        await self._check_suspicious_patterns(request, client_ip)
        
        response = await call_next(request)
        
        # Check response for security issues
        await self._check_response_security(response, client_ip)
        
        return response
    
    async def _check_suspicious_patterns(self, request: Request, client_ip: str):
        """Check request for suspicious patterns"""
        # Check query parameters
        for key, value in request.query_params.items():
            for pattern in self._suspicious_patterns:
                if re.search(pattern, value, re.IGNORECASE):
                    logger.warning(f"Suspicious pattern detected in {key} from {client_ip}: {pattern}")
        
        # Check headers
        for key, value in request.headers.items():
            for pattern in self._suspicious_patterns:
                if re.search(pattern, value, re.IGNORECASE):
                    logger.warning(f"Suspicious pattern detected in header {key} from {client_ip}: {pattern}")
        
        # Check body for POST/PUT requests
        if request.method in ["POST", "PUT"]:
            try:
                body = await request.body()
                body_str = body.decode('utf-8', errors='ignore')
                for pattern in self._suspicious_patterns:
                    if re.search(pattern, body_str, re.IGNORECASE):
                        logger.warning(f"Suspicious pattern detected in body from {client_ip}: {pattern}")
            except Exception:
                pass
    
    async def _check_response_security(self, response: Response, client_ip: str):
        """Check response for security issues"""
        if hasattr(response, 'body'):
            try:
                content_type = response.headers.get("content-type", "")
                if content_type.startswith("text/html"):
                    body = await response.body()
                    body_str = body.decode('utf-8', errors='ignore')
                    
                    # Check for potential XSS in response
                    if "<script" in body_str.lower():
                        logger.warning(f"Potential XSS in response to {client_ip}")
                
            except Exception:
                pass

# Helper function to apply middleware
def create_enhanced_app(app):
    """Create enhanced FastAPI app with middleware"""
    # Add GZip compression
    app.add_middleware(GZipMiddleware)
    
    return app