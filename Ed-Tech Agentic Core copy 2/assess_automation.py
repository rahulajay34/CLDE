from playwright.sync_api import sync_playwright
import time
import pandas as pd
import re

# Global list to keep browser open if needed
_playwright_instances = []

def publish_quiz_loop(email, password, quiz_df, status_callback=None):
    """
    Publishes a quiz to the Assess Platform using Playwright.
    Supports MCSC, MCMC, and Subjective types.
    """
    def log(msg, p=0.0):
        if status_callback:
            status_callback(msg, p)
        print(msg)

    log("🚀 Initializing Browser...", 0.0)

    try:
        # Start Playwright manually to allow detaching/keeping open
        p = sync_playwright().start()
        browser = p.chromium.launch(headless=False)
        _playwright_instances.append({"p": p, "browser": browser})
        
        context = browser.new_context()
        page = context.new_page()

        # --- Step A: Login ---
        log("🔑 Logging in...", 0.05)
        
        page.goto("https://assess-admin.masaischool.com/auth/sign-in")
        
        # Robust Login
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
            select_el = page.locator("select").first
            if select_el.is_visible():
                log("⏳ Waiting 15s for MANUAL Client Selection...", 0.1)
                time.sleep(15) 
                log("Resuming automation...")
        except Exception as e:
            pass

        # --- Step C: Creation Loop ---
        total_questions = len(quiz_df)
        
        for index, row in quiz_df.iterrows():
            q_num = index + 1
            progress = 0.1 + (0.9 * (index / total_questions))
            q_type = row.get('questionType', 'mcsc')
            
            log(f"📝 Publishing Q{q_num} ({q_type})...", progress)
            
            # 1. Navigate
            page.goto("https://assess-admin.masaischool.com/questions/create")
            # Wait for the main container or specific elements to minimize flakiness
            page.wait_for_selector("button:has-text('Multiple choice single choice')", timeout=10000)
            
            # --- 2. Select Question Type ---
            try:
                type_map = {
                    "mcsc": "Multiple choice single choice",
                    "mcmc": "Multiple choice multiple choice",
                    "subjective": "Subjective"
                }
                target_text = type_map.get(q_type, "Multiple choice single choice")
                
                # The dropdown trigger usually shows the CURRENT selection.
                # Default seems to be "Multiple choice single choice".
                # We find the button that acts as the menu trigger for Question Type.
                # Use a specific locator: The one that probably contains the current type text.
                
                # Check if current text is already correct
                # We look for a button that contains the text.
                current_type_btn = page.locator("button[aria-haspopup='menu']").filter(has_text=re.compile(r"Multiple choice|Subjective")).first
                
                if current_type_btn.is_visible():
                    curr_text = current_type_btn.inner_text()
                    if target_text not in curr_text:
                        current_type_btn.click()
                        # Click the target option from the menu
                        page.get_by_role("menuitem", name=target_text).click()
                        time.sleep(0.5) # Allow UI to update
            except Exception as e:
                log(f"⚠️ Type selection warning: {e}")

            # --- 3. Select Content Type -> Markdown ---
            try:
                # The "Text" vs "Markdown" dropdown.
                # It's also a menu button. Often starts as "Text".
                # We need to find the one related to Question Content (the first one).
                
                content_type_btn = page.locator("button[aria-haspopup='menu']").filter(has_text=re.compile(r"Text|Markdown")).first
                if content_type_btn.is_visible():
                    if "Markdown" not in content_type_btn.inner_text():
                        content_type_btn.click()
                        page.get_by_role("menuitem", name="Markdown").click()
            except Exception as e:
                log(f"⚠️ Markdown toggle warning: {e}")

            time.sleep(0.5)

            # --- 4. Fill Question Body ---
            try:
                # Based on user snippet:
                # For MCQ/MSQ it was <textarea placeholder="Content Here..." ...>
                # For Subjective it was <textarea ... class="w-md-editor-text-input ">
                # BUT if we select Markdown, it likely becomes w-md-editor-text-input for ALL.
                # Let's try the markdown editor class first as we forced Markdown.
                
                md_editor = page.locator(".w-md-editor-text-input").first
                if md_editor.is_visible():
                    md_editor.fill(row['contentBody'])
                else:
                    # Fallback to the placeholder provided in snippet
                    page.get_by_placeholder("Content Here...").fill(row['contentBody'])
            except Exception as e:
                log(f"⚠️ Body fill warning: {e}")

            # --- 5. Handlie Options (MCSC / MCMC) ---
            if q_type in ["mcsc", "mcmc"]:
                # Scroll down
                page.keyboard.press("PageDown")
                
                # Wait for interaction
                time.sleep(0.5)

                try:
                     # Wait for inputs
                     page.wait_for_selector("input[placeholder*='option here']", timeout=3000)
                except:
                     pass

                # Find Option Inputs
                inputs = page.locator("input[placeholder*='option here']")
                
                # Add Options if needed
                if inputs.count() < 4:
                    add_btn = page.get_by_role("button", name="Add Option")
                    if add_btn.is_visible():
                        while inputs.count() < 4:
                            add_btn.click()
                            time.sleep(0.3)
                
                # Fill Options
                count = inputs.count()
                for i in range(4):
                    if i < count:
                        opt_val = row.get(f"option.{i+1}", "")
                        if pd.notna(opt_val):
                            inputs.nth(i).fill(str(opt_val))

                # Identify Options Container
                # The container that holds the "Options" header
                options_container = page.locator("p", has_text="Options").locator("xpath=..")
                
                # Select Answer
                if q_type == "mcsc":
                    try:
                        correct_idx = int(float(row['mcscAnswer'])) - 1
                        
                        # Radius inside Options container
                        # "Show tag with Id" uses checkboxes, so radios should be safe here
                        radios = options_container.locator(".chakra-radio__control")
                        
                        if radios.count() > correct_idx:
                            radios.nth(correct_idx).click(force=True)
                        else:
                            log(f"⚠️ Radio index {correct_idx} out of range (found {radios.count()})")
                            
                    except Exception as e:
                        log(f"⚠️ Radio select warning: {e}")

                elif q_type == "mcmc":
                    try:
                        ans_str = str(row['mcmcAnswer'])
                        indices = [int(x.strip())-1 for x in ans_str.split(",") if x.strip().isdigit()]
                        
                        # Checkboxes inside Options container
                        # Filter OUT "Show tag with Id" labels
                        # We target the LABEL, filter by text, then find control
                        # The Answer checkbox label is usually empty text-wise or doesn't have "Show tag with Id"
                        
                        target_checkboxes = options_container.locator("label.chakra-checkbox").filter(has_not_text="Show tag with Id").locator(".chakra-checkbox__control")
                        
                        for idx in indices:
                            if target_checkboxes.count() > idx:
                                target_checkboxes.nth(idx).click(force=True)
                            else:
                                log(f"⚠️ Checkbox index {idx} out of range (found {target_checkboxes.count()})")
                                
                    except Exception as e:
                        log(f"⚠️ Checkbox select warning: {e}")

            # --- 6. Advanced Tab & Explanation ---
            try:
                # Snippet: <button ...>Advanced</button>
                adv_btn = page.get_by_role("button", name="Advanced")
                if adv_btn.is_visible():
                    adv_btn.click()
                
                time.sleep(0.5)
                
                # Explanation Type -> Markdown
                # It's logically the SECOND "Text"/"Markdown" dropdown on the page now.
                # We can find it by searching again or scoping.
                
                # Find all buttons with text Text/Markdown
                type_btns = page.locator("button[aria-haspopup='menu']").filter(has_text=re.compile(r"Text|Markdown"))
                
                # The last one is likely the explanation one (since it appears after Advanced).
                exp_type_btn = type_btns.last
                if exp_type_btn.is_visible() and "Markdown" not in exp_type_btn.inner_text():
                    exp_type_btn.click()
                    # Click Markdown in the specific menu that opened?
                    # Playwright handles the menu opening.
                    page.get_by_role("menuitem", name="Markdown").last.click() # Use last to be safe? Or just name. 
                    # Usually "Markdown" menu item is unique visible when menu is open.
                    
                time.sleep(0.5)

                # Explanation Body
                # Snippet: <textarea ... placeholder="Please enter Markdown text" ...>
                # Also likely .w-md-editor-text-input since it's markdown
                
                # Scope to the advanced panel if possible, or just take the LAST editor.
                editors = page.locator("textarea.w-md-editor-text-input")
                if editors.count() > 1:
                    editors.last.fill(str(row['answerExplanation']))
                else:
                    # Fallback check placeholder
                    page.get_by_placeholder("Please enter Markdown text").fill(str(row['answerExplanation']))

            except Exception as e:
                log(f"⚠️ Advanced/Explanation warning: {e}")

            # --- 7. Create ---
            try:
                 page.get_by_role("button", name="Create").click()
                 # Wait for success toast or navigation?
                 # Since we loop, we need to ensure we are done.
                 # User didn't give success indicator. We'll wait a bit.
                 time.sleep(3) 
            except Exception as e:
                 log(f"❌ Create click failed: {e}")

        log("✅ Quiz Published! Browser left open.", 1.0)
        return {"success": True, "message": f"Published {total_questions} questions. Browser Open."}
            
    except Exception as e:
        return {"success": False, "message": f"Automation Error: {str(e)}"}
