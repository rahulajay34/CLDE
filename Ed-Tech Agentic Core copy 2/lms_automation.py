import time
from playwright.sync_api import sync_playwright

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
        with sync_playwright() as p:
            # Launch browser in visible mode
            browser = p.chromium.launch(headless=False)
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
                
                # Wait for navigation after login (wait for URL change or dashboard element)
                # Ideally, wait for the dashboard URL or a specific element on the dashboard
                # For robustness, we'll wait for the URL to NOT be the login URL or just wait for load state
                page.wait_for_load_state("networkidle")
                
            except Exception as e:
                browser.close()
                return {"success": False, "message": f"Login failed: {str(e)}"}

            # Step B: Navigation
            try:
                page.goto("https://experience-admin.masaischool.com/lectures/create/")
                page.wait_for_load_state("networkidle")
            except Exception as e:
                browser.close()
                return {"success": False, "message": f"Navigation failed: {str(e)}"}

            # Step C: Content Injection
            try:
                # Wait for the specific textarea
                textarea_selector = "textarea.w-md-editor-text-input"
                page.wait_for_selector(textarea_selector, timeout=10000)
                
                # Fill the textarea
                # Using focus and type or fill based on how the editor reacts. 
                # .fill() is usually safer for standard inputs, but sometimes editors need keyboard events.
                # Let's try fill first.
                page.fill(textarea_selector, content)
                
            except Exception as e:
                browser.close()
                return {"success": False, "message": f"Content injection failed: {str(e)}"}

            # Step D: Handover
            # Keep browser open for 5 minutes
            # Step D: Handover
            # Keep browser open for a short while to allow verification
            # We wait for a "Saved" indicator or just give 5 seconds for the user to see it.
            # Long sleeps block the Streamlit server thread.
            print("Completed. Waiting 5s before closing...")
            time.sleep(5)
            
            browser.close()
            return {"success": True, "message": "Content pasted successfully! Browser closed."}

    except Exception as e:
        return {"success": False, "message": f"Automation Error: {str(e)}"}
