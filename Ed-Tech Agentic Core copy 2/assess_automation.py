from playwright.sync_api import sync_playwright
import time
import pandas as pd

def publish_quiz_loop(email, password, quiz_df, status_callback=None):
    """
    Publishes a quiz to the Assess Platform using Playwright.
    Robust version using text/role based selectors.
    """
    def log(msg, p=0.0):
        if status_callback:
            status_callback(msg, p)
        print(msg)

    log("🚀 Initializing Browser...", 0.0)

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            context = browser.new_context()
            page = context.new_page()

            # --- Step A: Login ---
            log("🔑 Logging in...", 0.05)
            
            page.goto("https://assess-admin.masaischool.com/auth/sign-in")
            
            # Robust Login Selectors
            page.get_by_placeholder("Email").fill(email)
            page.get_by_placeholder("Password").fill(password)
            page.get_by_role("button", name="Sign In").click()
            
            # Wait for navigation
            try:
                page.wait_for_url("**/client-selection", timeout=8000) 
            except:
                pass 

            # --- Step B: Client Selection ---
            log("🏢 Selecting Client...", 0.1)
            
            try:
                # Try to detect if we need to select a client
                select_el = page.locator("select").first
                if select_el.is_visible():
                    log("⏳ Waiting 15s for MANUAL Client Selection (User Action Required)...", 0.1)
                    time.sleep(15) 
                    log("Resuming automation...")
            except Exception as e:
                log(f"Client selection check passed/skipped: {e}")

            # --- Step C: Creation Loop ---
            total_questions = len(quiz_df)
            
            for index, row in quiz_df.iterrows():
                q_num = index + 1
                progress = 0.1 + (0.9 * (index / total_questions))
                
                log(f"📝 Publishing Question {q_num}/{total_questions}...", progress)
                
                # 1. Navigate to Create Page
                page.goto("https://assess-admin.masaischool.com/questions/create")
                page.wait_for_load_state("networkidle")
                
                # 2. Select Question Type
                # Using text matching which is safer than complex xpath
                try:
                    # If "Multiple choice single choice" text is not visible as a selected item, click to select
                    if not page.get_by_role("button", name="Multiple choice single choice").is_visible():
                        # Click the dropdown trigger. It's usually a button near "Select Question Type"
                        # We try to click the trigger button
                        page.locator("button").filter(has_text="Select Question Type").click()
                        # Then click the option
                        page.get_by_role("menuitem", name="Multiple choice single choice").click()
                except:
                    # Fallback pattern
                     pass

                # 3. Select Markdown Format
                # Click "Markdown" button if "Text" is currently selected
                try:
                    # Find the button group for content type
                    # Look for button "Markdown"
                    md_btn = page.get_by_role("button", name="Markdown")
                    if md_btn.count() > 0:
                        md_btn.click()
                    else:
                        # Maybe inside a menu?
                        pass
                except Exception as e:
                    log(f"Markdown toggle warning: {e}")

                # 4. Fill Question Body
                try:
                    # Try filling the Markdown editor input
                    # .w-md-editor-text-input is standard for the markdown editor lib used
                    editor = page.locator(".w-md-editor-text-input")
                    if editor.is_visible():
                        editor.fill(row['contentBody'])
                    else:
                        # Fallback to standard textarea
                        page.get_by_placeholder("Content Here...").fill(row['contentBody'])
                except Exception as e:
                    log(f"Body fill failed: {e}")

                # 5. Fill Options
                # Find all option inputs
                inputs = page.get_by_placeholder("type mcsc option here...")
                inputs.first.wait_for()
                
                if inputs.count() >= 4:
                    inputs.nth(0).fill(str(row['option.1']))
                    inputs.nth(1).fill(str(row['option.2']))
                    inputs.nth(2).fill(str(row['option.3']))
                    inputs.nth(3).fill(str(row['option.4']))
                
                # 6. Select Correct Answer
                correct_idx = int(row['mcscAnswer']) - 1
                try:
                    # Click the radio button corresponding to the correct index
                    # We find all radio controls in the options area
                    radios = page.locator(".chakra-radio__control")
                    # There might be others on page, so we filter/scope if possible
                    # But typically option radios appear in order.
                    # Warning: 'chakra-radio__control' is a class name, acceptable for specific chakra UI apps.
                    if radios.count() >= 4:
                        radios.nth(correct_idx).click()
                except Exception as e:
                    log(f"Radio click failed: {e}")

                # 7. Submit
                page.get_by_role("button", name="Create").click()
                
                # Wait for completion (short sleep as we don't have a reliable success element to await in this generic script)
                time.sleep(2)

            log("✅ All Questions Published!", 1.0)
            browser.close()
            return {"success": True, "message": f"Successfully published {total_questions} questions."}
            
    except Exception as e:
        return {"success": False, "message": f"Automation Error: {str(e)}"}
