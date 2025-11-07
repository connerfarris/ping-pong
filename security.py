import time
import logging
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify, session
import threading

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# In-memory storage for failed attempts and blocked IPs
# In production, consider using Redis or a database
failed_attempts = {}
blocked_ips = {}

# Configuration
MAX_FAILED_ATTEMPTS = 5
INITIAL_BLOCK_TIME = 300  # 5 minutes
MAX_BLOCK_TIME = 86400    # 24 hours
EXPONENTIAL_BASE = 2      # Base for exponential backoff

class IPBlockedError(Exception):
    def __init__(self, retry_after):
        self.retry_after = retry_after
        super().__init__(f"IP blocked. Try again after {retry_after} seconds")

def get_client_ip():
    """Get the client's IP address, handling proxies."""
    if request.headers.getlist("X-Forwarded-For"):
        return request.headers.getlist("X-Forwarded-For")[0]
    return request.remote_addr

def is_ip_blocked(ip):
    """Check if an IP is currently blocked."""
    if ip in blocked_ips:
        if datetime.now() < blocked_ips[ip]['blocked_until']:
            return True, blocked_ips[ip]['blocked_until']
        # Block expired, remove it
        del blocked_ips[ip]
    return False, None

def record_failed_attempt(ip):
    """Record a failed login attempt and block if necessary."""
    now = datetime.now()
    
    # Initialize or update failed attempts
    if ip not in failed_attempts:
        failed_attempts[ip] = {
            'count': 0,
            'first_attempt': now,
            'last_attempt': now
        }
    
    attempt = failed_attempts[ip]
    attempt['count'] += 1
    attempt['last_attempt'] = now
    
    # Calculate block time with exponential backoff
    if attempt['count'] > MAX_FAILED_ATTEMPTS:
        block_time = min(
            INITIAL_BLOCK_TIME * (EXPONENTIAL_BASE ** (attempt['count'] - MAX_FAILED_ATTEMPTS - 1)),
            MAX_BLOCK_TIME
        )
        blocked_until = now + timedelta(seconds=block_time)
        blocked_ips[ip] = {
            'blocked_until': blocked_until,
            'block_time': block_time
        }
        # Reset failed attempts after blocking
        del failed_attempts[ip]
        
        return blocked_until
    
    return None

def reset_failed_attempts(ip):
    """Reset failed attempts counter for an IP."""
    if ip in failed_attempts:
        del failed_attempts[ip]

def block_ip(ip, duration):
    """Manually block an IP for a specific duration."""
    blocked_ips[ip] = {
        'blocked_until': datetime.now() + timedelta(seconds=duration),
        'block_time': duration
    }

def get_remaining_block_time(ip):
    """Get remaining block time in seconds for an IP."""
    if ip in blocked_ips:
        remaining = (blocked_ips[ip]['blocked_until'] - datetime.now()).total_seconds()
        return max(0, int(remaining))
    return 0

def check_ip_block():
    """Decorator to check if the client's IP is blocked."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            ip = get_client_ip()
            is_blocked, blocked_until = is_ip_blocked(ip)
            
            if is_blocked:
                retry_after = int((blocked_until - datetime.now()).total_seconds())
                return (
                    jsonify({
                        "error": "Too many failed attempts. Please try again later.",
                        "retry_after": retry_after
                    }),
                    429,
                    {"Retry-After": str(retry_after)}
                )
                
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def requires_auth(f):
    @wraps(f)
    @check_ip_block()  # Check if IP is blocked
    # @auth_limiter  # Apply rate limiting to all auth attempts
    @log_failed_attempt()  # Log failed attempts
    def decorated(*args, **kwargs):
        # Check session first
        if session.get('authenticated'):
            # Check if session is expired
            if 'last_activity' in session:
                last_activity = session['last_activity']
                if (datetime.now() - last_activity).total_seconds() > 3600:  # 1 hour session timeout
                    session.clear()
                    logger.warning(f"Session expired for IP: {get_client_ip()}")
                else:
                    session['last_activity'] = datetime.now()
                    return f(*args, **kwargs)
        
        # Basic auth fallback
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            client_ip = get_client_ip()
            logger.warning(f"Failed login attempt from IP: {client_ip}")
            return Response(
                'Could not verify your access level for that URL.\n'
                'You have to login with proper credentials', 401,
                {'WWW-Authenticate': 'Basic realm="Login Required"'})
        
        # Successful authentication
        client_ip = get_client_ip()
        logger.info(f"Successful login from IP: {client_ip}")
        
        # Reset failed attempts and set up session
        reset_failed_attempts(client_ip)
        session.clear()
        session['authenticated'] = True
        session['user_agent'] = request.headers.get('User-Agent')
        session['ip_address'] = client_ip
        session['last_activity'] = datetime.now()
        
        # Set session to expire after 1 hour of inactivity
        session.permanent = True
        
        return f(*args, **kwargs)
    return decorated

def log_failed_attempt():
    """Decorator to log failed login attempts."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            ip = get_client_ip()
            response = f(*args, **kwargs)
            
            # If the response indicates a failed login (401 Unauthorized)
            if isinstance(response, tuple) and len(response) > 1 and response[1] == 401:
                blocked_until = record_failed_attempt(ip)
                if blocked_until:
                    retry_after = int((blocked_until - datetime.now()).total_seconds())
                    return (
                        jsonify({
                            "error": "Too many failed attempts. Your IP has been temporarily blocked.",
                            "retry_after": retry_after
                        }),
                        429,
                        {"Retry-After": str(retry_after)}
                    )
            
            return response
        return decorated_function
    return decorator

# Background task to clean up old entries
def cleanup_old_entries():
    """Periodically clean up old entries from the failed_attempts and blocked_ips dictionaries."""
    while True:
        now = datetime.now()
        
        # Clean up old failed attempts (older than 1 hour)
        global failed_attempts
        failed_attempts = {
            ip: data for ip, data in failed_attempts.items()
            if (now - data['last_attempt']).total_seconds() < 3600
        }
        
        # Clean up expired blocks
        global blocked_ips
        blocked_ips = {
            ip: data for ip, data in blocked_ips.items()
            if now < data['blocked_until']
        }
        
        # Sleep for 5 minutes
        time.sleep(300)

# Start the cleanup thread
cleanup_thread = threading.Thread(target=cleanup_old_entries, daemon=True)
cleanup_thread.start()
