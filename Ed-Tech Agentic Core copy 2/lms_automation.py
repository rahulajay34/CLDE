import time
from playwright.sync_api import sync_playwright

# Global list to keep references and prevent Garbage Collection closing the browser
_browser_instances = []

def publish_to_lms(email, password, content):
    """
    Automates the process of publishing content to the Masai LMS.
    
    Args:
        email (str): LMS login email.
        password (str): LMS login password.
        content (str): The markdown content to inject.
        
    Returns:
        dict: A dictionary containing 'success' (bool) and 'message' (str).
    """
    try:
        # NOTE: We do NOT use 'with sync_playwright() as p' because that closes the browser on exit.
        # We manually start it and store the reference to keep it open.
        p = sync_playwright().start()
        
        # Launch browser in visible mode
        browser = p.chromium.launch(headless=False)
        
        # Store references to prevent GC from killing the process
        _browser_instances.append({"p": p, "browser": browser})
        
        context = browser.new_context()
        page = context.new_page()

        # Step A: Login
        try:
            page.goto("https://experience-admin.masaischool.com/")
            
            # Wait for email input and fill
            page.wait_for_selector("input#email1", timeout=10000)
            page.fill("input#email1", email)
            
            # Fill password
            page.fill("input#password1", password)
            
            # Click submit
            page.click("button[type='submit']")
            
            # Wait for navigation after login
            page.wait_for_load_state("networkidle")
            
        except Exception as e:
            # On login failure, we might want to close it or leave it open?
            # Usually better to close if we failed early ensuring no zombie processes if failure loop.
            # But for debugging users prefer open. Let's close ONLY on early failure if requested?
            # Current request is "should not close by itself". 
            # If it errors out, maybe better to leave open so they see WHY?
            # Let's return error but NOT close, consistent with user request.
            return {"success": False, "message": f"Login failed: {str(e)}"}

        # Step B: Navigation
        try:
            page.goto("https://experience-admin.masaischool.com/lectures/create/")
            page.wait_for_load_state("networkidle")
        except Exception as e:
            return {"success": False, "message": f"Navigation failed: {str(e)}"}

        # Step C: Content Injection
        try:
            # Wait for the specific textarea
            textarea_selector = "textarea.w-md-editor-text-input"
            page.wait_for_selector(textarea_selector, timeout=10000)
            
            page.fill(textarea_selector, content)
            
        except Exception as e:
            return {"success": False, "message": f"Content injection failed: {str(e)}"}

        # Step D: Handover
        # We do NOT close the browser.
        msg = "Content pasted successfully! The browser has been left open for you to verify and save."
        return {"success": True, "message": msg}

    except Exception as e:
        return {"success": False, "message": f"Automation Error: {str(e)}"}
