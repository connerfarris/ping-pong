import time
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify
import threading

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
